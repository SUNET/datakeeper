import os
import logging
import configparser
from dataclasses import dataclass, field


class StreamOnlyFilter(logging.Filter):
    """Allow all levels except ERROR for StreamHandler."""
    def filter(self, record):
        return record.levelno == logging.INFO

# Create handlers
stream_handler = logging.StreamHandler()
stream_handler.addFilter(StreamOnlyFilter())


parent_dir = os.path.dirname(os.path.dirname(__file__))
log_directory = os.getenv("AIS_LOG_DIRECTORY", parent_dir)

# Make sure that directory does exist
os.makedirs(log_directory, exist_ok=True)
log_path = os.path.join(log_directory, "ais_processor.log")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[stream_handler, logging.FileHandler(log_path)],
)
logger = logging.getLogger("ais_processor")


@dataclass
class AppConfigEnv:
    """Configuration class for AIS data processor"""
    
    # AIS-Server
    ais_host: str = field(default_factory=lambda: os.environ.get("AIS_SERVER_HOST", "localhost"))
    ais_port: int = field(default_factory=lambda: int(os.environ.get("AIS_SERVER_PORT", "8040")))
    ais_user: str = field(default_factory=lambda: os.environ.get("AIS_USER", "user"))
    ais_password: str = field(default_factory=lambda: os.environ.get("AIS_USER_PASSWORD", "pass"))
    ais_log_file: str = field(default_factory=lambda: os.environ.get("LOG_PATH", "ais_processor.log"))
    retry_interval: int = field(default_factory=lambda: int(os.environ.get("RETRY_INTERVAL", "5")))
    max_retries: int = field(default_factory=lambda: int(os.environ.get("MAX_RETRIES", "3")))
    connection_timeout: int = field(default_factory=lambda: int(os.environ.get("CONNECTION_TIMEOUT", "30")))

    # Kafka
    bootstrap_servers: str = field(default_factory=lambda: os.environ.get("BOOTSTRAP_SERVERS", "localhost:9092"))
    kafka_topic: str = field(default_factory=lambda: os.environ.get("KAFKA_TOPIC", "ais-data"))
    kafka_batch_size: int = field(default_factory=lambda: int(os.environ.get("KAFKA_BATCH_SIZE", "100")))
    kafka_flush_timeout: float = field(default_factory=lambda: float(os.environ.get("KAFKA_FLUSH_TIMEOUT", "1.0")))
    enable_kafka_output: bool = field(default_factory=lambda: os.environ.get("ENABLE_KAFKA_OUTPUT", False))

    # MongoDB
    mongo_url: str = field(default_factory=lambda: os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    mongo_db: str = field(default_factory=lambda: os.environ.get("MONGO_DB", "aisdb"))
    mongo_collection: str = field(default_factory=lambda: os.environ.get("MONGO_COLLECTION", "vessels"))
    log_file: str = field(default_factory=lambda: os.environ.get("LOG_FILE", "data.log"))
    enable_mongo_output:  bool = field(default_factory=lambda: os.environ.get("ENABLE_MONGO_OUTPUT", False))
    
    def __post_init__(self):
        # Internal method call during initialization
        self._normalize_flags()

    def _normalize_flags(self):
        # Internal/private method (by convention)
        self.enable_mongo_output = self._str_to_bool(self.enable_mongo_output)
        self.enable_kafka_output = self._str_to_bool(self.enable_kafka_output)

    def _str_to_bool(self, value: str) -> bool:
        return str(value).strip().lower() in ('1', 'true', 'yes', 'on', True)


class AppConfigFile:


    def __init__(self, config_path: str):
        """Initialize settings from an INI file."""
        if not config_path:
            raise Exception("Config file path is required for AppConfigFile class.")
        self.config_path = config_path
        self.config = self.load_config(self.config_path)
        
        # AIS-Server
        self.ais_host: str = self.get("AIS", "AIS_SERVER_HOST", default="localhost")
        self.ais_port: int = int(self.get("AIS", "AIS_SERVER_PORT", default="8040"))
        self.ais_user: str = self.get("AIS", "AIS_USER", default="user")
        self.ais_password: str = self.get("AIS", "AIS_USER_PASSWORD", default="pass")
        self.ais_log_file: str = self.get("AIS", "LOG_PATH", default="ais_processor.log")
        self.retry_interval: int = int(self.get("AIS", "RETRY_INTERVAL", default="5"))
        self.max_retries: int = int(self.get("AIS", "MAX_RETRIES", default="3"))
        self.connection_timeout: int = int(self.get("AIS", "CONNECTION_TIMEOUT", default="30"))

        # Kafka
        self.bootstrap_servers: str = self.get("KAFKA", "BOOTSTRAP_SERVERS", default="localhost:9092")
        self.kafka_topic: str = self.get("KAFKA", "KAFKA_TOPIC", default="ais-data")
        self.kafka_batch_size: int = int(self.get("KAFKA", "BATCH_SIZE", default="100"))
        self.kafka_flush_timeout: float = float(self.get("KAFKA", "FLUSH_TIMEOUT", default="1.0"))
        self.enable_kafka_output: bool = self._str_to_bool(self.get("KAFKA", "ENABLE_KAFKA_OUTPUT", default="False"))

        # MongoDB
        self.mongo_url: str = self.get("MONGO", "MONGO_URL", default="mongodb://localhost:27017")
        self.mongo_db: str = self.get("MONGO", "MONGO_DB", default="aisdb")
        self.mongo_collection: str = self.get("MONGO", "MONGO_COLLECTION", default="vessels")
        self.log_file: str = self.get("LOGGING", "FILE", default="data.log")
        self.enable_mongo_output: bool = self._str_to_bool(self.get("MONGO", "ENABLE_MONGO_OUTPUT", default="False"))
  
        
    def _str_to_bool(self, value: str) -> bool:
        return str(value).strip().lower() in ('1', 'true', 'yes', 'on', True)

    def get(self, section: str, key: str, required: bool = False, default=None):
        """Retrieve a configuration value with optional defaults."""
        if not self.config.has_section(section):
            if required:
                raise KeyError(f"Missing section [{section}] in config file.")
            return default
        value = self.config.get(section, key, fallback=default)
        if not value:
            return None
        return value.strip()
        

    def load_config(self, config_path, strict=True):
        """Load the configuration file if it exists."""
        config = configparser.ConfigParser()
        if not os.path.exists(config_path):
            if strict:
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            else:
                return config

        config.read(config_path)
        return config
    
    

    def __repr__(self):
        str_repr = []
        for attr in vars(self):
            if 'config' not in attr:
                str_repr.append(f"{attr}: {getattr(self, attr)}")        
        return f"{self.__class__.__name__}({', '.join(str_repr)})"
        
