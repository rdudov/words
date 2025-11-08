"""
Structured logging configuration for the Words application.

This module provides centralized logging setup using structlog for structured
logging with support for both development (console) and production (JSON) output.
"""

import logging
from pathlib import Path

import structlog

from src.words.config.settings import settings


def setup_logging():
    """
    Configure structured logging for the application.

    This function sets up both standard Python logging and structlog with:
    - File and console output handlers
    - Log level filtering based on settings
    - JSON format for production (debug=False)
    - Console renderer for development (debug=True)
    - ISO timestamp format
    - Context variables support
    - Stack info and exception info

    The function creates the logs directory if it doesn't exist and configures
    all necessary processors for structured logging.

    Returns:
        structlog.BoundLogger: A configured structlog logger instance
    """
    # Create logs directory if not exists
    log_dir = Path(settings.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure standard logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(message)s",
        handlers=[
            logging.FileHandler(settings.log_file),
            logging.StreamHandler(),
        ],
        force=True,  # Force reconfiguration of logging
    )

    # Configure structlog processors
    processors = [
        # Merge in context from contextvars
        structlog.contextvars.merge_contextvars,
        # Add log level to event dict
        structlog.processors.add_log_level,
        # Add stack info if requested
        structlog.processors.StackInfoRenderer(),
        # Format exceptions if present
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
        # Add ISO timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Choose renderer based on debug mode
        structlog.dev.ConsoleRenderer()
        if settings.debug
        else structlog.processors.JSONRenderer(),
    ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    return structlog.get_logger()


# Module-level logger instance
logger = setup_logging()
