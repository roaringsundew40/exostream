"""Logging configuration with rich console output and file logging"""

import logging
import sys
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler

console = Console()

# Default log directory
DEFAULT_LOG_DIR = Path.home() / ".exostream" / "logs"
DEFAULT_LOG_FILE = "daemon.log"


def setup_logger(name: str, level: str = "INFO", log_file: bool = True) -> logging.Logger:
    """
    Set up a logger with rich formatting and optional file logging
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Whether to write logs to a file (default: True)
    
    Returns:
        Configured logger instance
    """
    # Console handler with level based on verbosity
    console_handler = RichHandler(console=console, rich_tracebacks=True)
    console_handler.setLevel(level)  # Console respects verbosity setting
    handlers = [console_handler]
    
    # Add file handler if requested
    if log_file:
        # Ensure log directory exists
        DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = DEFAULT_LOG_DIR / DEFAULT_LOG_FILE
        
        # File handler with detailed format
        # Always capture DEBUG level in file, regardless of console verbosity
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)  # Always capture DEBUG and above in file
        handlers.append(file_handler)
    
    # Set root logger to DEBUG so all messages reach handlers
    # Each handler will filter based on its own level
    logging.basicConfig(
        level=logging.DEBUG,  # Root logger accepts all levels
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    logger = logging.getLogger(name)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)

