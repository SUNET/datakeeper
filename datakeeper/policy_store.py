import os
import yaml
import json
import uuid
from typing import List
from datakeeper.policy_system.plugin_registry import PluginRegistry
from datakeeper.mixins.logger import LoggerMixin
from datakeeper.policy_system.plugin_registry import Policy
from datakeeper.database.db import Database
        

class PolicyStore(LoggerMixin):
    """Store for managing and applying policies."""
    
    def __init__(self, db: Database, policy_path: str=None, plugin_dir=None, log_file="policy_store.log"):
        
        super().__init__(log_file)
        self.policy_path=policy_path or os.path.join(os.path.dirname(__file__), "config", "policy.yaml")
        self.plugin_dir=plugin_dir or os.path.join(os.path.dirname(__file__), "policy_system", "plugins")
        self.policy_config = None
        self.policies: List[Policy] = []
        self.settings = None
        self.policy_templates = []
        self.database: Database = db

        try:
            self.log_info(f"Loading plugins from {self.plugin_dir}")
            PluginRegistry.load_plugins(self.plugin_dir)
            
            print("PluginRegistry")
            print("_operations=>", PluginRegistry._operations)
            print("_strategies=>", PluginRegistry._strategies)
            print("_policy_types=>", PluginRegistry._policy_types)
    
            # Load policy configuration
            self.load()
            
            print("-----")
            print(self.policies)

            
        except Exception as e:
            self.logger.error(f"Error during initialization: {e}", exc_info=True)
            raise
        
    
    def load(self):
        """Load policies from the configuration file."""
        try:
            if os.path.exists(self.policy_path):
                self.log_info(f"Loading policies from {self.policy_path}")
                with open(self.policy_path, 'r') as f:
                    self.policy_config = yaml.safe_load(f) or {}
                    self.settings = self.policy_config.get("settings", {})
                    self.policy_templates = self.policy_config.get("policy_templates", [])
                    policy_data = self.policy_config.get("policies", [])
                    
                    self.log_info(f"Found {len(policy_data)} policies in configuration")
                    
                    self.policies = []
                    for policy_config in policy_data:
                        if not policy_config.get('enabled', True):
                            continue
                        
                        policy = self._create_policy(policy_config)
                        if policy:
                            self.policies.append(policy)
            else:
                self.logger.warning(f"Policy file {self.policy_path} not found")
        except Exception as e:
            self.logger.error(f"Error loading policies: {e}", exc_info=True)
            raise
        
    def _create_policy(self, policy_config):
        """Create a policy instance from the configuration."""
        policy_name = policy_config.get("name")
        enabled = policy_config.get("enabled", True)
        triggers = policy_config.get("triggers", [])
        selector = policy_config.get("selector", {})
        actions = policy_config.get("actions", [])
        
        if not actions:
            self.log_warning(f"Policy '{policy_name}' has no actions, skipping")
            return None
        
        policy_type = actions[0].get("type")
        spec = actions[0].get("spec", {})

        # Get the appropriate policy class
        policy_class = PluginRegistry.get_policy_type(policy_type)

        if not policy_class:
            self.log_warning(f"Policy type '{policy_type}' not found, skipping policy '{policy_name}'")
            return None

        # Create and return the policy instance
        try:
            self.log_info(f"Creating policy: {policy_class}")
            uniq_id = f"{policy_name}-{uuid.uuid4()}"
            policy_data = {
                "id": uniq_id,
                "name": policy_name,
                "policy_file": self.policy_path,
                "is_enabled": int(enabled),
                "strategy": spec.get('strategy', 'none'), 
                "data_type": selector.get('data_type', ['hdf5']),
                "tags": selector.get('tags', None),
                "paths": selector.get('paths', None),
                "operations": spec.get('operations', []),
                "triggers": triggers,
            }
            self._save_scheduled_policies(policy_data)

            return policy_class(uniq_id, policy_name, enabled, triggers, selector, spec, self.database)
        except Exception as e:
            self.logger.error(f"Error creating policy '{policy_name}': {e}", exc_info=True)
            return None

    
    def _save_scheduled_policies(self, policy_data, trigger_type="schedule"):
        """Save the current policies to the configuration file."""
        
        def json_dump_keys(policy_data):
            policy_data["data_type"] = json.dumps(policy_data["data_type"])
            policy_data["tags"] = json.dumps(policy_data["tags"] )
            policy_data["paths"] = json.dumps(policy_data["paths"])
            policy_data["operations"] = json.dumps(policy_data["operations"])
            policy_data["triggers"] = json.dumps(policy_data["triggers"])
            return policy_data
        
        
        for trigger in policy_data["triggers"]:
            if trigger.get("type") == trigger_type:
                policy_data = json_dump_keys(policy_data)
                sql_values = tuple(policy_data.values())
                self.database.add_policy(sql_values)


    def apply_policies(self, context={}):
        """Apply all applicable policies to the given data."""
        result = None
        for policy in self.policies:
            if policy.enabled and policy.evaluate(context):
                self.log_info(f"Applying policy '{policy.name}'")
                try:
                    result = policy.apply(context)
                except Exception as e:
                    self.logger.error(f"Error applying policy '{policy.name}': {e}", exc_info=True)
        
        return result
    
    def get_policy_by_name(self, name):
        """Get a policy by name."""
        for policy in self.policies:
            if policy.name == name:
                return policy
        return None
    
    def get_policies_by_trigger_type(self, trigger_type):
        """Get all policies that have a specific trigger type."""
        matching_policies = []
        
        for policy in self.policies:
            if not policy.enabled:
                continue
                
            for trigger in policy.triggers:
                if trigger.get("type") == trigger_type:
                    matching_policies.append((policy, trigger))
                    break
        
        return matching_policies
    
    def get_scheduled_policies(self):
        """Get all policies that have schedule triggers."""
        return self.get_policies_by_trigger_type("schedule")
        

   
if __name__ == "__main__":
    policy_store = PolicyStore("config/policy.yaml")
    context = {
        "metadata": {
            "priority": "normal",
            "tagged": "standard"
        },
        "storage": {
            "utilization": 85
        }
    }
    result = policy_store.apply_policies(context={})
    
    # Example of accessing a specific policy
    retention_policy = policy_store.get_policy_by_name("automatic-deletion")
    if retention_policy:
        print(f"Retention period: {retention_policy.retention_time} days")
        
    scheduled_policies = policy_store.get_scheduled_policies()
    for policy, trigger in scheduled_policies:
        trigger_spec = trigger.get("spec", {})
        print("Policy=", policy)
        print("Trigger=", trigger)
        print("Trigger_spec=", trigger_spec)

