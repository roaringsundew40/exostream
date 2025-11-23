"""Logging configuration with rich console output"""

import logging
import sys
from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Set up a logger with rich formatting
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )
    
    logger = logging.getLogger(name)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)

