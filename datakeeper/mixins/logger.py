import os
import logging

class LoggerMixin:
    def __init__(self, log_file="app.log"):
        self.logger = logging.getLogger(self.__class__.__name__)
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        self.log_directory = os.getenv("LOG_DIRECTORY", parent_dir)
        log_path = os.path.join(self.log_directory, "logs")
        # Make sure that directory does exist
        os.makedirs(log_path, exist_ok=True)
        
        
        self.log_path = os.path.join(log_path, log_file)
        

        # Configure logger if it hasn't been configured yet
        if not self.logger.handlers:
            
            self.logger.setLevel(logging.DEBUG)

            # Create file handler
            file_handler = logging.FileHandler(self.log_path)
            file_handler.setLevel(logging.DEBUG)

            # Create formatter and add it to the handler
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)

            # Add handler to logger
            self.logger.addHandler(file_handler)
            # Prevent duplicate logs
            self.logger.propagate = False

    def log_info(self, message):
        self.logger.info(message)

    def log_error(self, message):
        self.logger.error(message)
        
    def log_warning(self, message):
        self.logger.warning(message)
