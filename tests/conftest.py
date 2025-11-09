"""
Pytest configuration and shared fixtures for the Words test suite.

This file contains pytest fixtures that are available to all test modules.
"""

import pytest
import sys
import os
from pathlib import Path

# Set up test environment variables before any imports
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_token_12345")
os.environ.setdefault("LLM_API_KEY", "test_api_key_12345")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("LOG_FILE", "/tmp/test_bot.log")
os.environ.setdefault("DEBUG", "true")

# Add src directory to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def temp_data_dir(tmp_path):
    """
    Provide a temporary directory for test data.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Returns:
        Path: Path to temporary data directory
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_word_data():
    """
    Provide sample word data for testing.

    Returns:
        dict: Sample word data structure
    """
    return {
        "word": "hello",
        "translation": "привет",
        "frequency_rank": 100,
        "examples": [
            "Hello, how are you?",
            "Say hello to your friends."
        ]
    }
