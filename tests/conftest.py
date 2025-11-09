"""
Pytest configuration and shared fixtures for the Words test suite.

This file contains pytest fixtures that are available to all test modules.
"""

import pytest
import sys
import os
from pathlib import Path

# Set up test environment variables before any imports
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
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


# ================================================================
# Integration Test Fixtures (for detecting lazy loading issues)
# ================================================================


@pytest.fixture
async def integration_test_engine():
    """
    Create in-memory async database engine for integration tests.

    This fixture creates a real SQLite database with all tables
    to test actual database operations without mocking.

    Yields:
        AsyncEngine: SQLAlchemy async engine for testing
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    from src.words.models import Base

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture
async def integration_test_session(integration_test_engine):
    """
    Create async session for integration tests.

    Args:
        integration_test_engine: AsyncEngine from integration_test_engine fixture

    Yields:
        AsyncSession: SQLAlchemy async session for testing
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    async_session = async_sessionmaker(
        integration_test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
async def test_user_with_profile(integration_test_session):
    """
    Create a real user and profile in the test database.

    This fixture creates actual database records (both User AND LanguageProfile)
    to test relationship loading and lazy loading issues.

    Args:
        integration_test_session: AsyncSession from integration_test_session fixture

    Returns:
        tuple[User, LanguageProfile]: User and profile instances
    """
    from src.words.models import User, LanguageProfile, CEFRLevel

    # Create user
    user = User(
        user_id=123456789,
        native_language="ru",
        interface_language="ru"
    )
    integration_test_session.add(user)
    await integration_test_session.commit()

    # Create active profile
    profile = LanguageProfile(
        user_id=123456789,
        target_language="en",
        level=CEFRLevel.B1,
        is_active=True
    )
    integration_test_session.add(profile)
    await integration_test_session.commit()

    return user, profile
