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


# ================================================================
# Lazy Loading Detection Documentation
# ================================================================
#
# NOTE: In async SQLAlchemy, lazy loading already raises MissingGreenlet errors
# naturally. This is actually the built-in "detection system"!
#
# The integration_test_session fixture is sufficient for most tests because:
# 1. Lazy loading attempts will raise MissingGreenlet errors automatically
# 2. Tests that access relationships without eager loading will fail naturally
# 3. No additional configuration is needed
#
# Best practices for avoiding lazy loading issues:
# -------------------------------------------------
# 1. Always use selectinload() or joinedload() when querying relationships
# 2. Test relationship access in integration tests
# 3. If a test fails with MissingGreenlet, add selectinload() to the query
#
# Example:
# --------
# # BAD - Will raise MissingGreenlet in async:
# user = await session.get(User, 123)
# profiles = user.profiles  # Error!
#
# # GOOD - Eager load relationships:
# from sqlalchemy import select
# from sqlalchemy.orm import selectinload
#
# result = await session.execute(
#     select(User)
#     .where(User.user_id == 123)
#     .options(selectinload(User.profiles))
# )
# user = result.scalar_one()
# profiles = user.profiles  # Works!
#
# See /home/user/words/tests/LAZY_LOADING_DETECTION.md for detailed documentation.
# ================================================================


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


@pytest.fixture
async def strict_integration_session(integration_test_session):
    """
    Session with explicit lazy loading detection.

    Uses the same underlying session but provides clearer error context.
    See /home/user/words/tests/LAZY_LOADING_DETECTION.md for usage patterns.

    This fixture exists for explicit naming and documentation - it
    provides the same behavior as integration_test_session but makes
    the intent of catching lazy loading issues more explicit in test names.

    Args:
        integration_test_session: AsyncSession from integration_test_session fixture

    Yields:
        AsyncSession: SQLAlchemy async session for testing (automatically
                      raises MissingGreenlet on lazy loading attempts)
    """
    yield integration_test_session
    # Session already raises MissingGreenlet automatically
    # This fixture exists for explicit naming and documentation


# ================================================================
# Pytest Hooks for Enhanced Error Messages
# ================================================================


def pytest_exception_interact(node, call, report):
    """
    Provide helpful guidance when MissingGreenlet errors occur (interactive mode).

    This hook is automatically called by pytest when an exception occurs
    during interactive debugging (e.g., with --pdb flag).

    Args:
        node: The pytest test item that raised the exception
        call: The call object containing exception info
        report: The test report object
    """
    if call.excinfo and "MissingGreenlet" in str(call.excinfo.typename):
        print("\n" + "=" * 70)
        print("❌ LAZY LOADING DETECTED IN ASYNC CONTEXT")
        print("=" * 70)
        print("This error occurs when accessing a relationship that wasn't eagerly loaded.")
        print("\nQuick fix: Add selectinload() to your query:")
        print("  .options(selectinload(YourModel.relationship_name))")
        print("\n📖 Detailed documentation: /home/user/words/tests/LAZY_LOADING_DETECTION.md")
        print("=" * 70 + "\n")


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """
    Provide helpful guidance when MissingGreenlet errors occur in test reports.

    This hook is called for every test phase (setup, call, teardown) and
    enhances error reports when lazy loading issues are detected.

    Args:
        item: The pytest test item
        call: The call object containing execution info
    """
    import sys

    outcome = yield
    report = outcome.get_result()

    # Only process failed tests in the 'call' phase
    if report.when == "call" and report.failed:
        if hasattr(call, 'excinfo') and call.excinfo is not None:
            # Check if this is a MissingGreenlet error
            exc_typename = str(call.excinfo.typename) if hasattr(call.excinfo, 'typename') else ""
            exc_value = str(call.excinfo.value) if hasattr(call.excinfo, 'value') else ""

            if "MissingGreenlet" in exc_typename or "greenlet_spawn" in exc_value:
                # Add helpful message to the test output (write to stderr for immediate display)
                message = "\n" + "=" * 70 + "\n"
                message += "❌ LAZY LOADING DETECTED IN ASYNC CONTEXT\n"
                message += "=" * 70 + "\n"
                message += "This error occurs when accessing a relationship that wasn't eagerly loaded.\n"
                message += "\nQuick fix: Add selectinload() to your query:\n"
                message += "  .options(selectinload(YourModel.relationship_name))\n"
                message += "\n📖 Detailed documentation: /home/user/words/tests/LAZY_LOADING_DETECTION.md\n"
                message += "=" * 70 + "\n\n"

                sys.stderr.write(message)
                sys.stderr.flush()
