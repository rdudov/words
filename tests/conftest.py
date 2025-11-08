"""
Pytest configuration and shared fixtures for the Words test suite.

This file contains pytest fixtures that are available to all test modules.
"""

import pytest
import sys
from pathlib import Path

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
