"""
Logging configuration for the Words application.

This module provides centralized logging setup using Python's standard
logging module with rotating file handlers for production use.
"""

import os
import logging
from logging.handlers import RotatingFileHandler

from src.words.config.settings import settings


class EventLogger:
    """Lightweight logger wrapper that accepts structured kwargs."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def debug(self, event: str, **kwargs) -> None:
        self._logger.debug(event, extra=kwargs)

    def info(self, event: str, **kwargs) -> None:
        self._logger.info(event, extra=kwargs)

    def warning(self, event: str, **kwargs) -> None:
        self._logger.warning(event, extra=kwargs)

    def error(self, event: str, **kwargs) -> None:
        self._logger.error(event, extra=kwargs)


def get_event_logger(name: str) -> EventLogger:
    """Return an EventLogger wrapper for a named logger."""
    return EventLogger(logging.getLogger(name))


logger = get_event_logger(__name__)


def setup_log_directories():
    """
    Create necessary directories for logs if they don't exist.

    Creates the logs directory structure needed for application logging.
    Uses exist_ok=True to avoid errors if directories already exist.
    """
    directories = ['logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def setup_logging():
    """
    Configure logging for the application.

    Sets up both console and file logging with rotation:
    - Console output via StreamHandler
    - File output via RotatingFileHandler with configurable rotation
    - Log format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    - Log level from settings
    - File rotation controlled by MAX_LOG_SIZE and MAX_LOG_BACKUP_COUNT env vars

    This function configures the root logger, so all module loggers will
    inherit these settings. Each module should create its own logger using:
        logger = logging.getLogger(__name__)

    Environment Variables:
        MAX_LOG_SIZE: Maximum log file size in bytes (default: 10MB)
        MAX_LOG_BACKUP_COUNT: Number of backup files to keep (default: 5)
    """
    # Create log directories
    setup_log_directories()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Create rotating file handler
    # Default: 10MB per file, keep 5 backup files
    file_handler = RotatingFileHandler(
        settings.log_file,
        maxBytes=int(os.getenv('MAX_LOG_SIZE', 10*1024*1024)),  # 10MB default
        backupCount=int(os.getenv('MAX_LOG_BACKUP_COUNT', 5)),
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
