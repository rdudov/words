"""Tests for logging configuration."""

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

import pytest

from src.words.utils.logger import setup_logging, setup_log_directories


def test_setup_log_directories_creates_logs_dir(tmp_path, monkeypatch):
    """Test that setup_log_directories creates the logs directory."""
    # Change to tmp directory
    monkeypatch.chdir(tmp_path)

    # Call function
    setup_log_directories()

    # Verify logs directory was created
    assert (tmp_path / "logs").exists()
    assert (tmp_path / "logs").is_dir()


def test_setup_log_directories_idempotent(tmp_path, monkeypatch):
    """Test that setup_log_directories can be called multiple times safely."""
    monkeypatch.chdir(tmp_path)

    # Call multiple times
    setup_log_directories()
    setup_log_directories()
    setup_log_directories()

    # Should still work and directory should exist
    assert (tmp_path / "logs").exists()


def test_setup_logging_creates_log_directory(tmp_path, monkeypatch):
    """Test that setup_logging creates the log directory."""
    log_file = tmp_path / "logs" / "test.log"
    log_file_str = str(log_file)

    # Mock settings
    class MockSettings:
        log_file = log_file_str
        log_level = "INFO"

    monkeypatch.setattr("src.words.utils.logger.settings", MockSettings())
    monkeypatch.chdir(tmp_path)

    # Call setup_logging
    setup_logging()

    # Verify directory was created
    assert log_file.parent.exists()


def test_setup_logging_configures_handlers():
    """Test that setup_logging configures both file and console handlers."""
    # Clear existing handlers
    root = logging.getLogger()
    root.handlers.clear()

    setup_logging()

    # Should have exactly 2 handlers: console and file
    assert len(root.handlers) == 2

    handler_types = [type(h).__name__ for h in root.handlers]
    assert "StreamHandler" in handler_types
    assert "RotatingFileHandler" in handler_types


def test_setup_logging_uses_rotating_file_handler():
    """Test that setup_logging uses RotatingFileHandler with rotation config."""
    root = logging.getLogger()
    root.handlers.clear()

    setup_logging()

    # Find the RotatingFileHandler
    rotating_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
    assert len(rotating_handlers) == 1

    handler = rotating_handlers[0]

    # Check default values (10MB, 5 backups)
    assert handler.maxBytes == 10 * 1024 * 1024
    assert handler.backupCount == 5


def test_setup_logging_respects_env_vars(monkeypatch):
    """Test that setup_logging respects MAX_LOG_SIZE and MAX_LOG_BACKUP_COUNT."""
    root = logging.getLogger()
    root.handlers.clear()

    # Set environment variables
    monkeypatch.setenv("MAX_LOG_SIZE", "5242880")  # 5MB
    monkeypatch.setenv("MAX_LOG_BACKUP_COUNT", "3")

    setup_logging()

    # Find the RotatingFileHandler
    rotating_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
    handler = rotating_handlers[0]

    # Check configured values
    assert handler.maxBytes == 5242880
    assert handler.backupCount == 3


def test_setup_logging_respects_log_level(monkeypatch):
    """Test that setup_logging respects the configured log level."""
    root = logging.getLogger()
    root.handlers.clear()

    class MockSettings:
        log_file = "test.log"
        log_level = "DEBUG"

    monkeypatch.setattr("src.words.utils.logger.settings", MockSettings())

    setup_logging()

    # Should be set to DEBUG
    assert root.level == logging.DEBUG


def test_setup_logging_uses_correct_format():
    """Test that setup_logging uses the correct log format."""
    root = logging.getLogger()
    root.handlers.clear()

    setup_logging()

    # Check formatter on handlers
    for handler in root.handlers:
        formatter = handler.formatter
        assert formatter is not None
        # Check format string matches calypso pattern
        assert formatter._fmt == '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def test_module_logger_gets_correct_name():
    """Test that module loggers get the correct __name__."""
    # Simulate a module creating its own logger
    module_logger = logging.getLogger("test.module.name")

    assert module_logger.name == "test.module.name"

    # Should inherit root logger configuration
    root = logging.getLogger()
    if root.handlers:
        # Module logger should use root logger's handlers
        assert module_logger.level == logging.NOTSET or module_logger.level == root.level


def test_logging_to_file_and_console(tmp_path, monkeypatch, caplog):
    """Test that logs are written to both file and console."""
    log_file = tmp_path / "logs" / "test.log"
    log_file_str = str(log_file)

    class MockSettings:
        log_file = log_file_str
        log_level = "INFO"

    monkeypatch.setattr("src.words.utils.logger.settings", MockSettings())
    monkeypatch.chdir(tmp_path)

    # Clear and setup
    root = logging.getLogger()
    root.handlers.clear()
    setup_logging()

    # Create a test logger
    test_logger = logging.getLogger("test_module")

    # Write a test message
    test_message = "Test log message for dual output"
    test_logger.info(test_message)

    # Check file
    assert log_file.exists()
    log_content = log_file.read_text()
    assert test_message in log_content
    assert "test_module" in log_content
    assert "INFO" in log_content
