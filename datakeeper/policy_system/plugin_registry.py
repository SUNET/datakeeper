import os
import glob
import importlib.util
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type
from mixins.logger import LoggerMixin


class Operation(ABC, LoggerMixin):
    """Base class for all operations that can be performed by policies."""

    def __init__(self, log_file):
        super().__init__(log_file)
        super().__init__()

    @abstractmethod
    def execute(self, data: Any, context: Dict[str, Any]) -> Any:
        """Execute the operation on the given data."""
        pass

    @classmethod
    def get_name(cls) -> str:
        """Return the operation name for registration."""
        return cls.__name__.lower().replace("operation", "")


class Strategy(ABC):
    """Base class for all strategies that determine how operations are applied."""

    @abstractmethod
    def apply(self, data: Any, operation: Operation, context: Dict[str, Any]) -> Any:
        """Apply the strategy using the given operation."""
        pass

    @classmethod
    def get_name(cls) -> str:
        """Return the strategy name for registration."""
        return cls.__name__.lower().replace("strategy", "")


class Policy(ABC):
    """Base class for all policies."""

    def __init__(
        self,
        uniq_id: str,
        name: str,
        enabled: bool,
        triggers: List[Dict[str, Any]],
        selector: Dict[str, Any],
        operations: List[str] = None,
        strategy: str = None,
    ):
        self.uniq_id = uniq_id
        self.name = name
        self.enabled = enabled
        self.triggers = triggers
        self.selector = selector
        self.operations = operations or []
        self.strategy = strategy or "none"
        self.schedule = {}
        self.scheduled_operations = []

    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate if the policy should be applied in the given context."""
        pass

    @abstractmethod
    def apply(self, context: Dict[str, Any]) -> Any:
        """Apply the policy to the given data."""
        pass

    @classmethod
    def get_policy_type(cls) -> str:
        """Return the policy type for registration."""
        return cls.__name__.lower().replace("policy", "")


# Registry for plugins
class PluginRegistry:
    """Registry for operations, strategies, and policy types."""

    _operations: Dict[str, Type[Operation]] = {}
    _strategies: Dict[str, Type[Strategy]] = {}
    _policy_types: Dict[str, Type[Policy]] = {}

    @classmethod
    def register_operation(cls, operation_class: Type[Operation]):
        """Register an operation class."""
        name = operation_class.get_name()
        cls._operations[name] = operation_class
        return operation_class

    @classmethod
    def register_strategy(cls, strategy_class: Type[Strategy]):
        """Register a strategy class."""
        name = strategy_class.get_name()
        cls._strategies[name] = strategy_class
        return strategy_class

    @classmethod
    def register_policy_type(cls, policy_class: Type[Policy]):
        """Register a policy type class."""
        name = policy_class.get_policy_type()
        cls._policy_types[name] = policy_class
        return policy_class

    @classmethod
    def get_operation(cls, name: str) -> Optional[Type[Operation]]:
        """Get an operation class by name."""
        name = name.replace("-", "").lower()
        return cls._operations.get(name)

    @classmethod
    def get_strategy(cls, name: str) -> Optional[Type[Strategy]]:
        """Get a strategy class by name."""
        return cls._strategies.get(name)

    @classmethod
    def get_policy_type(cls, name: str) -> Optional[Type[Policy]]:
        """Get a policy type class by name."""
        return cls._policy_types.get(name)

    @classmethod
    def load_plugins(cls, plugin_dir: str):
        """Load all plugins from the given directory."""
        if not os.path.exists(plugin_dir):
            return

        # Load Python modules from the plugin directory
        for plugin_file in glob.glob(os.path.join(plugin_dir, "*.py")):
            module_name = os.path.basename(plugin_file)[:-3]  # Remove .py extension
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
