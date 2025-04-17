import json
import uuid
from typing import List, Dict, Any
from datakeeper.policy_system.plugin_registry import PluginRegistry, Policy
from datakeeper.database.db import Database

@PluginRegistry.register_policy_type
class RetentionPolicy(Policy):
    """Policy for data retention and deletion."""
    
    def __init__(self, uniq_id:str, name: str, enabled: bool, triggers: List[Dict[str, Any]], 
                 selector: Dict[str, Any], spec: Dict[str, Any], db: Database = None):
        super().__init__(uniq_id, name, enabled, triggers, selector, spec.get('operations', []), spec.get('strategy', 'none'))
        
        self.retention_time = spec.get('retention_time', 30)  # Default 30 days
        self.warning_time = spec.get('warning_time', 7)
        self.strategy_name = spec.get('strategy', 'default')
        self.time_unit = spec.get('time_unit', 'day')
        self.operations = spec.get('operations', [])
        self.exceptions = spec.get('exceptions', [])
        self.tags = self.selector.get('tags', None)
        self.paths = self.selector.get('paths', None)
        self.data_type = self.selector.get('data_type', ['hdf5'])
        self.schedule =  list(filter(lambda x: x['type']=='schedule', self.triggers))[0]
        self.scheduled_operations = []
        self.context = {
            "name": self.name,
            "data_type": self.data_type,
            "file_paths": self.paths,
            "tags": self.tags,
            "time_unit": self.time_unit, 
            "retention_time": self.retention_time, 
            "warning_time": self.warning_time,
            "triggers": self.triggers,
            "exceptions": self.exceptions
        }
        self.database = db
        # print("=== SPEC ===")
        # print(spec)
        self._set_scheduled_operations_sql()

    
    def _set_scheduled_operations_sql(self):

        for op in self.operations:
            data_in = {
                "id": f"{op}-{uuid.uuid4()}",
                "id_policy": self.uniq_id,
                "name": op,
                "operation": str(PluginRegistry.get_operation(op)),
                "filetypes": json.dumps(self.context["file_paths"]),
                "trigger_type": self.schedule['type'],
                "trigger_spec": json.dumps(self.schedule['spec']),
                "status": 'registered',
            }
            sql_values = list(data_in.values())
            self.scheduled_operations.append(data_in)
            if self.database:
                self.database.add_schedule(sql_values)
    
    def evaluate(self, context: Dict[str, Any]={}) -> bool:
        # Update the default context
        self.context.update(context)
        # Check if the file matches the selector criteria
        datatypes = self.context.get('data_type', '')
        
        # Check data type
        for dtp in datatypes:
            if dtp not in self.selector.get('data_type', []):
                return False
        
        # Check tags if applicable
        file_tags = self.context.get('tags', [])
        selector_tags = self.selector.get('tags', [])
        if selector_tags and not any(tag in file_tags for tag in selector_tags):
            return False
        
        # Check exceptions
        metadata = self.context.get('metadata', {})
        for exception in self.exceptions:
            condition = exception.get('condition', '')
            # In production, you'd need a proper expression evaluator
            if 'metadata.priority == \'high\'' in condition and metadata.get('priority') == 'high':
                self.context['retention_time'] = exception.get('retention_time', self.retention_time)
                return True
            if 'metadata.tagged == \'preserve\'' in condition and metadata.get('tagged') == 'preserve':
                self.context['retention_time'] = exception.get('retention_time', self.retention_time)
                return True
        
        # No exceptions matched, use the default retention period
        self.context['retention_time'] = self.retention_time
        return True
    
    def apply(self, context: Dict[str, Any]={}) -> Any:
        # Update the default context
        self.context.update(context)
        # Get the strategy
        strategy_class = PluginRegistry.get_strategy(self.strategy_name)
        if not strategy_class:
            print(f"Strategy '{self.strategy_name}' not found, using default 'none' strategy")
            strategy_class = PluginRegistry.get_strategy('none')
        
        strategy = strategy_class()
        
        # Apply each operation with the strategy
        for op_name in self.operations:
            operation_class = PluginRegistry.get_operation(op_name)
            if operation_class:
                operation = operation_class()
                data = strategy.apply(operation, self.context)
            else:
                print(f"Operation '{op_name}' not found, skipping")
        
        return data

    def __repr__(self):
        return (
            f"RetentionPolicy(uniq_id={self.uniq_id!r}, name={self.name!r}, enabled={self.enabled!r}, "
            f"triggers={self.triggers!r}, selector={self.selector!r}, "
            f"retention_time={self.retention_time!r}, warning_time={self.warning_time!r}, "
            f"strategy_name={self.strategy_name!r}, operations={self.operations!r}, "
            f"exceptions={self.exceptions!r})"
        )
