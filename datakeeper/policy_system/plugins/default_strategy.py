
from typing import Dict, Any
from datakeeper.policy_system.plugin_registry import Operation, PluginRegistry, Strategy

@PluginRegistry.register_strategy
class DefaultStrategy(Strategy):
    """Strategy that applies no processing before the operation."""
    
    def apply(self, operation: Operation, context: Dict[str, Any]) -> Any:
        # Default: execute the operation without any pre-processing
        return operation.execute(context)
