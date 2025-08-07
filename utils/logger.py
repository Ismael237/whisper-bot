from typing import Dict, Any
from loguru import logger
import os
import sys

# Configure log directory and files
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'worker_{time:YYYY-MM-DD}.log')
ERROR_LOG_FILE = os.path.join(LOG_DIR, 'error_{time:YYYY-MM-DD}.log')

# Custom log format
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

def setup_logger(level: str = "INFO") -> None:
    """Configure the logger with specified log level.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Remove default logger
    logger.remove()
    
    # Add file handler with rotation and compression
    logger.add(
        LOG_FILE,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        level=level,
        format=LOG_FORMAT,
        enqueue=True,
        backtrace=True,
        diagnose=True
    )
    
    # Add error log file
    logger.add(
        ERROR_LOG_FILE,
        rotation="10 MB",
        retention="60 days",
        compression="zip",
        level="ERROR",
        format=LOG_FORMAT,
        enqueue=True,
        backtrace=True,
        diagnose=True
    )
    
    # Add console handler
    logger.add(
        sys.stderr,
        level=level,
        format=LOG_FORMAT,
        colorize=True,
        enqueue=True
    )

# Initialize logger with default level
setup_logger()

def log_with_context(
    message: str,
    level: str = "info",
    **context: Dict[str, Any]
) -> None:
    """Log a message with additional context.
    
    Args:
        message: The message to log
        level: Log level (debug, info, warning, error, critical)
        **context: Additional context to include in the log
    """
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(message, **context)

# Configure SQLAlchemy logging
class SQLAlchemyLogFilter:
    def __call__(self, record):
        record["name"] = "sqlalchemy.engine"
        return record

# Configure logger for SQLAlchemy
sqlalchemy_logger = logger.bind(name="sqlalchemy.engine")
logger = logger.patch(lambda record: record.update(name=record["name"].split(".")[-1]) if "." in record["name"] else record)