"""
Log class implementation for use outside of Calibre
This implements the minimal API needed for our application
"""
import logging
from enum import IntEnum

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class LogLevel(IntEnum):
    """Log levels that mimic Calibre's Log class levels"""
    ERROR = 40
    WARN = WARNING = 30
    INFO = 20
    DEBUG = 10


class Log:
    """A simplified version of Calibre's Log class for use in the API"""
    
    # Constants to match Calibre's Log class
    ERROR = LogLevel.ERROR
    WARN = WARNING = LogLevel.WARNING
    INFO = LogLevel.INFO
    DEBUG = LogLevel.DEBUG
    
    def __init__(self):
        self.logger = logging.getLogger('worddumb')
    
    def prints(self, level, *args, **kwargs):
        """Print a message at the specified log level"""
        message = " ".join(str(arg) for arg in args)
        
        if level >= LogLevel.ERROR:
            self.logger.error(message)
        elif level >= LogLevel.WARNING:
            self.logger.warning(message)
        elif level >= LogLevel.INFO:
            self.logger.info(message)
        elif level >= LogLevel.DEBUG:
            self.logger.debug(message)
    
    def debug(self, *args, **kwargs):
        """Log a debug message"""
        self.prints(LogLevel.DEBUG, *args, **kwargs)
    
    def info(self, *args, **kwargs):
        """Log an info message"""
        self.prints(LogLevel.INFO, *args, **kwargs)
    
    def warn(self, *args, **kwargs):
        """Log a warning message"""
        self.prints(LogLevel.WARNING, *args, **kwargs)
    
    def error(self, *args, **kwargs):
        """Log an error message"""
        self.prints(LogLevel.ERROR, *args, **kwargs) 