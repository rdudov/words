"""
Tests for structured logging configuration.

This module tests the logging setup including file/console output,
log levels, JSON vs console rendering, context variables, and exception handling.
"""

import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest
import structlog

from src.words.config.settings import settings
from src.words.utils.logger import setup_logging


class TestLoggingSetup:
    """Tests for the setup_logging function."""

    def test_setup_logging_creates_logs_directory(self, tmp_path):
        """Test that setup_logging creates the logs directory if it doesn't exist."""
        # Arrange
        log_file = tmp_path / "test_logs" / "test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'INFO'), \
             patch.object(settings, 'debug', False):

            # Ensure directory doesn't exist
            assert not log_file.parent.exists()

            # Act
            setup_logging()

            # Assert
            assert log_file.parent.exists()
            assert log_file.parent.is_dir()

    def test_setup_logging_with_existing_directory(self, tmp_path):
        """Test that setup_logging works when the logs directory already exists."""
        # Arrange
        log_dir = tmp_path / "existing_logs"
        log_dir.mkdir()
        log_file = log_dir / "test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'INFO'), \
             patch.object(settings, 'debug', False):

            # Act
            logger = setup_logging()

            # Assert
            assert log_file.parent.exists()
            assert logger is not None

    def test_setup_logging_returns_structlog_logger(self, tmp_path):
        """Test that setup_logging returns a structlog logger instance."""
        # Arrange
        log_file = tmp_path / "test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'INFO'), \
             patch.object(settings, 'debug', False):

            # Act
            logger = setup_logging()

            # Assert
            assert logger is not None
            assert hasattr(logger, "info")
            assert hasattr(logger, "error")
            assert hasattr(logger, "warning")
            assert hasattr(logger, "debug")

    def test_logging_to_file(self, tmp_path):
        """Test that logs are written to the configured file."""
        # Arrange
        log_file = tmp_path / "test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'INFO'), \
             patch.object(settings, 'debug', False):

            # Act
            logger = setup_logging()
            test_message = "Test log message"
            logger.info(test_message)

            # Assert
            assert log_file.exists()
            log_content = log_file.read_text()
            assert test_message in log_content

    def test_logging_to_console(self, tmp_path, capsys):
        """Test that logs are written to console."""
        # Arrange
        log_file = tmp_path / "test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'INFO'), \
             patch.object(settings, 'debug', True):

            # Act
            logger = setup_logging()
            test_message = "Console test message"
            logger.info(test_message)

            # Assert
            captured = capsys.readouterr()
            # The message should appear in stdout or stderr
            output = captured.out + captured.err
            assert test_message in output

    def test_log_level_debug(self, tmp_path):
        """Test that DEBUG level logs are captured when log_level is DEBUG."""
        # Arrange
        log_file = tmp_path / "test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'DEBUG'), \
             patch.object(settings, 'debug', False):

            # Act
            logger = setup_logging()
            debug_message = "Debug level message"
            logger.debug(debug_message)

            # Assert
            log_content = log_file.read_text()
            assert debug_message in log_content

    def test_log_level_filtering(self, tmp_path):
        """Test that log levels below the configured level are filtered out."""
        # Arrange
        log_file = tmp_path / "test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'WARNING'), \
             patch.object(settings, 'debug', False):

            # Act
            logger = setup_logging()
            logger.debug("Debug message - should not appear")
            logger.info("Info message - should not appear")
            warning_message = "Warning message - should appear"
            logger.warning(warning_message)

            # Assert
            log_content = log_file.read_text()
            assert "Debug message" not in log_content
            assert "Info message" not in log_content
            assert warning_message in log_content

    def test_json_renderer_in_production(self, tmp_path):
        """Test that JSON renderer is used when debug=False."""
        # Arrange
        log_file = tmp_path / "test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'INFO'), \
             patch.object(settings, 'debug', False):

            # Act
            logger = setup_logging()
            test_message = "JSON test message"
            logger.info(test_message)

            # Assert
            log_content = log_file.read_text()
            # Try to parse as JSON
            log_lines = log_content.strip().split("\n")
            parsed = json.loads(log_lines[0])
            assert "event" in parsed
            assert parsed["event"] == test_message

    def test_console_renderer_in_development(self, tmp_path, capsys):
        """Test that console renderer is used when debug=True."""
        # Arrange
        log_file = tmp_path / "test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'INFO'), \
             patch.object(settings, 'debug', True):

            # Act
            logger = setup_logging()
            test_message = "Console renderer test"
            logger.info(test_message)

            # Assert
            captured = capsys.readouterr()
            output = captured.out + captured.err
            assert test_message in output
            # Console renderer typically adds color codes or formatting
            # Just verify the message is present

    def test_context_variables(self, tmp_path):
        """Test that context variables are included in logs."""
        # Arrange
        log_file = tmp_path / "test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'INFO'), \
             patch.object(settings, 'debug', False):

            # Act
            logger = setup_logging()
            test_message = "Message with context"
            user_id = 12345
            logger.info(test_message, user_id=user_id, action="test")

            # Assert
            log_content = log_file.read_text()
            assert test_message in log_content
            assert str(user_id) in log_content
            assert "test" in log_content

    def test_exception_logging(self, tmp_path):
        """Test that exceptions are properly logged with stack traces."""
        # Arrange
        log_file = tmp_path / "test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'INFO'), \
             patch.object(settings, 'debug', False):

            # Act
            logger = setup_logging()
            try:
                raise ValueError("Test exception")
            except ValueError:
                logger.exception("An error occurred")

            # Assert
            log_content = log_file.read_text()
            assert "An error occurred" in log_content
            assert "ValueError" in log_content
            assert "Test exception" in log_content

    def test_timestamp_format(self, tmp_path):
        """Test that logs include ISO format timestamps."""
        # Arrange
        log_file = tmp_path / "test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'INFO'), \
             patch.object(settings, 'debug', False):

            # Act
            logger = setup_logging()
            logger.info("Timestamp test")

            # Assert
            log_content = log_file.read_text()
            parsed = json.loads(log_content.strip())
            assert "timestamp" in parsed
            # ISO format should contain a 'T' separator
            assert "T" in parsed["timestamp"]

    def test_log_level_in_output(self, tmp_path):
        """Test that log level is included in the output."""
        # Arrange
        log_file = tmp_path / "test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'INFO'), \
             patch.object(settings, 'debug', False):

            # Act
            logger = setup_logging()
            logger.info("Info level test")
            logger.warning("Warning level test")
            logger.error("Error level test")

            # Assert
            log_content = log_file.read_text()
            log_lines = log_content.strip().split("\n")

            parsed_info = json.loads(log_lines[0])
            assert parsed_info["level"] == "info"

            parsed_warning = json.loads(log_lines[1])
            assert parsed_warning["level"] == "warning"

            parsed_error = json.loads(log_lines[2])
            assert parsed_error["level"] == "error"

    def test_multiple_log_calls(self, tmp_path):
        """Test that multiple log calls all work correctly."""
        # Arrange
        log_file = tmp_path / "test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'INFO'), \
             patch.object(settings, 'debug', False):

            # Act
            logger = setup_logging()
            messages = ["First message", "Second message", "Third message"]
            for msg in messages:
                logger.info(msg)

            # Assert
            log_content = log_file.read_text()
            log_lines = log_content.strip().split("\n")
            assert len(log_lines) == 3
            for i, msg in enumerate(messages):
                parsed = json.loads(log_lines[i])
                assert parsed["event"] == msg


class TestModuleLevelLogger:
    """Tests for the module-level logger instance."""

    def test_module_level_logger_exists(self):
        """Test that the module-level logger is available."""
        from src.words.utils.logger import logger

        assert logger is not None

    def test_module_level_logger_is_functional(self, tmp_path):
        """Test that the module-level logger can log messages."""
        # Arrange
        log_file = tmp_path / "module_test.log"

        with patch.object(settings, 'log_file', str(log_file)), \
             patch.object(settings, 'log_level', 'INFO'), \
             patch.object(settings, 'debug', False):

            # Need to reload the module to pick up the new settings
            import importlib
            import sys

            # Remove the module from cache
            if 'src.words.utils.logger' in sys.modules:
                del sys.modules['src.words.utils.logger']
            if 'src.words.utils' in sys.modules:
                del sys.modules['src.words.utils']

            # Re-import with new settings
            from src.words.utils.logger import logger

            # Act
            test_message = "Module logger test"
            logger.info(test_message)

            # Assert
            assert log_file.exists()
            log_content = log_file.read_text()
            assert test_message in log_content

    def test_module_level_logger_can_be_imported(self):
        """Test that the logger can be imported from the utils package."""
        from src.words.utils import logger

        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
