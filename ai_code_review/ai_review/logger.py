"""
Logging utility for the AI code review system.
"""

import os
import sys
import logging
from typing import Optional
from datetime import datetime


def setup_logger(
    name: str = "ai_review",
    log_level: int = logging.INFO,
    log_file: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    """
    Set up a logger with file and/or console handlers.
    
    Args:
        name: Logger name
        log_level: Logging level (e.g., logging.DEBUG, logging.INFO)
        log_file: Path to log file (optional)
        console: Whether to log to console
        
    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Add file handler if log_file is specified
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Add console handler if console is True
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


def get_default_log_file() -> str:
    """
    Get the default log file path.
    
    Returns:
        Path to the default log file
    """
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Get the parent directory (project root)
    project_root = os.path.dirname(script_dir)
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create a log file with the current date
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(logs_dir, f"system_{date_str}.log")
    
    return log_file


# Create a default logger
logger = setup_logger(
    log_file=get_default_log_file(),
    console=False  # Don't log to console by default
)


def enable_console_logging(log_level: int = logging.INFO) -> None:
    """
    Enable console logging for the default logger.
    
    Args:
        log_level: Logging level for the console handler
    """
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # Add to logger
    logger.addHandler(console_handler)


def set_log_level(log_level: int) -> None:
    """
    Set the log level for the default logger.
    
    Args:
        log_level: New logging level
    """
    logger.setLevel(log_level)
    
    # Update handlers
    for handler in logger.handlers:
        handler.setLevel(log_level)


def get_logger() -> logging.Logger:
    """
    Get the default logger.
    
    Returns:
        Default logger
    """
    return logger 