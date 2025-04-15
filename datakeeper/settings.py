import os
import configparser


class DataKeeperSettings:
    """Settings class for DataKeeper, reading from an INI file."""

    DEFAULT_CONFIG_PATH = os.getenv("CONFIG_PATH", "config.ini")

    def __init__(self, config_path: str = None):
        """Initialize settings from an INI file."""
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config = self.load_config(self.config_path)

        # Load settings
        self.log_directory = self.get("DATAKEEPER", "LOG_DIRECTORY", required=True)
        self.plugin_dir = self.get("DATAKEEPER", "PLUGIN_DIR", required=True)
        self.policy_path = self.get("DATAKEEPER", "POLICY_PATH", required=True)
        self.db_path = self.get("DATAKEEPER", "DB_PATH", required=True)
        self.init_file_path = self.get("DATAKEEPER", "INIT_FILE_PATH", default=None)
        self.api_host = self.get("API", "HOST", default='0.0.0.0')
        self.api_port = int(self.get("API", "PORT", default='5000'))
        
        # Set env
        os.environ["LOG_DIRECTORY"] = self.log_directory
        os.environ["DB_PATH"] = self.db_path

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
        return (
            f"DataKeeperSettings(\n"
            f"  log_directory={self.log_directory},\n"
            f"  plugin_dir={self.plugin_dir},\n"
            f"  policy_path={self.policy_path},\n"
            f"  db_path={self.db_path},\n"
            f"  init_file_path={self.init_file_path},\n"
            f")"
        )
