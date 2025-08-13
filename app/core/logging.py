import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.config.config import settings

def setup_logging():
    """Configure application logging with both file and console handlers."""
    # Create log directory if it doesn't exist
    log_path = Path(settings.LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Configure formatter
    log_formatter = logging.Formatter(settings.LOG_FORMAT)
    
    # Configure file handler with rotation
    file_handler = RotatingFileHandler(
        settings.LOG_PATH,
        maxBytes=10485760,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Create application logger
    logger = logging.getLogger("service")
    
    return logger

# Initialize logger
logger = setup_logging() 