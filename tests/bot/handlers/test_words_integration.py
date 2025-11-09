"""
Integration tests for word handlers to detect lazy loading issues.

These tests use real database queries (not mocks) to verify that:
1. The profile.user relationship can be accessed without greenlet errors
2. Eager loading is working correctly in get_active_profile()
3. Future lazy loading issues will be caught by tests

IMPORTANT: These tests use real in-memory database with minimal mocking
to detect SQLAlchemy relationship loading issues that mocks would hide.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, User as TgUser, Chat

from src.words.bot.handlers.words import process_word_input
from src.words.bot.states.registration import AddWordStates
from src.words.models import User, LanguageProfile, CEFRLevel, Word, UserWord
from src.words.repositories.user import ProfileRepository


@pytest.fixture
def mock_message():
    """Create mock Telegram Message object."""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TgUser)
    message.from_user.id = 123456789
    message.from_user.first_name = "Test"
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 123456789
    message.answer = AsyncMock()
    message.text = "hello"
    return message


@pytest.fixture
def mock_state():
    """Create mock FSM context."""
    state = MagicMock(spec=FSMContext)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.clear = AsyncMock()
    return state


@pytest.fixture
def mock_processing_message():
    """Create mock processing message."""
    msg = MagicMock(spec=Message)
    msg.delete = AsyncMock()
    return msg


class TestProcessWordInputIntegration:
    """
    Integration tests for process_word_input handler.

    These tests detect lazy loading issues by accessing profile.user
    relationship with real database queries.
    """

    @pytest.mark.asyncio
    async def test_word_addition_real_db_no_mocking_repositories(
        self,
        integration_test_session,
        test_user_with_profile,
        mock_message,
        mock_state
    ):
        """
        End-to-end integration test with real database and real repositories.

        This test uses real database, real repositories, and only mocks
        the LLM service to verify the complete word addition flow works
        without lazy loading errors.

        Test Strategy:
        - Real database with actual tables and relationships
        - Real repositories (UserRepository, ProfileRepository, WordRepository)
        - Mock only LLM/translation service
        - Execute full word addition flow
        - Verify no greenlet errors occur

        This test will FAIL if:
        - Lazy loading is attempted on profile.user relationship
        - Any repository tries to access relationships without eager loading
        """
        user, profile = test_user_with_profile
        mock_message.text = "hello"

        # Mock processing message
        processing_msg = MagicMock(spec=Message)
        processing_msg.delete = AsyncMock()
        mock_message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])

        # Mock translation data
        translation_data = {
            "translations": ["привет"],
            "examples": [{"source": "Hello", "target": "Привет"}],
            "word_forms": {}
        }

        # Patch get_session to return our test session
        # Patch TranslationService.translate_word to avoid real LLM calls
        with patch('src.words.bot.handlers.words.get_session') as mock_get_session:
            with patch('src.words.services.translation.TranslationService.translate_word') as mock_translate:
                # Setup session mock
                mock_get_session.return_value.__aenter__.return_value = integration_test_session

                # Mock translation service
                mock_translate.return_value = translation_data

                # Execute the handler (uses REAL repositories)
                await process_word_input(mock_message, mock_state)

        # Verify the handler completed successfully
        # This proves that profile.user.native_language access worked

        # Verify word was added to database
        from src.words.repositories.word import WordRepository
        word_repo = WordRepository(integration_test_session)
        word = await word_repo.find_by_text_and_language("hello", "en")
        assert word is not None
        assert word.word == "hello"
        assert word.language == "en"

        # Verify success message
        assert mock_message.answer.call_count == 2
        result_call = mock_message.answer.call_args_list[1]
        result_text = result_call[0][0]
        assert "✅ Word added to your vocabulary" in result_text

        # Verify state was cleared
        mock_state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_profile_user_relationship_loaded_without_error(
        self,
        integration_test_session,
        test_user_with_profile
    ):
        """
        Direct test: Verify get_active_profile() loads user relationship.

        This test directly accesses profile.user to verify eager loading
        works and doesn't raise MissingGreenlet error.

        Test Strategy:
        - Get active profile using ProfileRepository
        - Access profile.user relationship directly
        - Verify no exceptions are raised
        - Verify user data is accessible

        This test will FAIL if:
        - selectinload(LanguageProfile.user) is removed
        - Lazy loading is attempted in async context
        """
        user, profile = test_user_with_profile

        # Get active profile using repository
        profile_repo = ProfileRepository(integration_test_session)
        loaded_profile = await profile_repo.get_active_profile(123456789)

        assert loaded_profile is not None

        # This is the critical access that would fail with lazy loading
        # If eager loading is removed, this will raise:
        # sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called
        native_language = loaded_profile.user.native_language

        # Verify the relationship was loaded correctly
        assert native_language == "ru"
        assert loaded_profile.user.user_id == 123456789
        assert loaded_profile.user.interface_language == "ru"

    @pytest.mark.asyncio
    async def test_lazy_loading_fails_without_selectinload(
        self,
        integration_test_session,
        test_user_with_profile
    ):
        """
        Negative test: Verify that relationship is NOT loaded without eager loading.

        This test proves that the integration tests are effective by demonstrating
        that the user relationship is not loaded when selectinload is not used.
        Using SQLAlchemy inspection, we verify the relationship is lazy-loaded.

        Test Strategy:
        - Query LanguageProfile WITHOUT selectinload(LanguageProfile.user)
        - Use SQLAlchemy inspect() to verify user relationship is NOT loaded
        - This proves that without eager loading, we rely on lazy loading
        - In a real handler context outside the session, lazy loading would fail

        This test validates that:
        - Our integration tests actually catch lazy loading issues
        - The eager loading in get_active_profile() is necessary
        - Without selectinload, the relationship would be lazy-loaded
        """
        from sqlalchemy import select, inspect as sa_inspect
        from sqlalchemy.orm.base import NO_VALUE

        user, profile = test_user_with_profile

        # Query profile WITHOUT eager loading (this is the problematic pattern)
        stmt = select(LanguageProfile).where(
            LanguageProfile.user_id == 123456789,
            LanguageProfile.is_active == True
        )
        # Explicitly NOT using: .options(selectinload(LanguageProfile.user))

        result = await integration_test_session.execute(stmt)
        lazy_profile = result.scalar_one_or_none()

        assert lazy_profile is not None

        # Use SQLAlchemy inspection to verify the relationship is NOT loaded
        inspection = sa_inspect(lazy_profile)
        user_attr = inspection.attrs.user

        # Check if user relationship is loaded
        # Without selectinload, loaded_value should be NO_VALUE (not loaded)
        is_loaded = user_attr.loaded_value is not NO_VALUE

        # This assertion proves that without selectinload, the relationship
        # is NOT eagerly loaded and would require lazy loading to access
        assert not is_loaded, (
            "User relationship should NOT be loaded without selectinload! "
            "This test proves that eager loading is necessary to avoid lazy loading."
        )
