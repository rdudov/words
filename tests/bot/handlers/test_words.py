"""
Comprehensive tests for word handlers.

Tests cover:
- ➕ Add Word button handler
- Word input processing
- Language detection (target→native and native→target fallback)
- Translation fetching and display
- Word addition to vocabulary
- State transitions
- Input validation (empty word)
- Error handling
- User profile validation
- Service integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, User as TgUser, Chat
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.words.bot.handlers.words import (
    cmd_add_word,
    process_word_input,
    router
)
from src.words.bot.states.registration import AddWordStates
from src.words.models import Base, User, LanguageProfile, CEFRLevel, Word, UserWord
from src.words.repositories.user import UserRepository, ProfileRepository


@pytest.fixture
async def test_engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
async def test_user_with_profile(test_session):
    """Create test user with active profile."""
    user = User(
        user_id=123456789,
        native_language="ru",
        interface_language="ru"
    )
    test_session.add(user)
    await test_session.commit()

    profile = LanguageProfile(
        user_id=123456789,
        target_language="en",
        level=CEFRLevel.B1,
        is_active=True
    )
    test_session.add(profile)
    await test_session.commit()

    return user, profile


@pytest.fixture
def mock_message():
    """Create mock Message object."""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TgUser)
    message.from_user.id = 123456789
    message.from_user.first_name = "Test"
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 123456789
    message.answer = AsyncMock()
    message.text = ""
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


class TestCmdAddWord:
    """Tests for cmd_add_word handler."""

    @pytest.mark.asyncio
    async def test_cmd_add_word_shows_instruction_message(
        self,
        mock_message,
        mock_state
    ):
        """Test ➕ Add Word button shows instruction message."""
        await cmd_add_word(mock_message, mock_state)

        # Verify instruction message is shown
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Send me the word" in call_args[0][0]
        assert "native language or in the language you're learning" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_add_word_sets_waiting_for_word_state(
        self,
        mock_message,
        mock_state
    ):
        """Test state transitions to waiting_for_word."""
        await cmd_add_word(mock_message, mock_state)

        # Verify state transition
        mock_state.set_state.assert_called_once_with(
            AddWordStates.waiting_for_word
        )

    @pytest.mark.asyncio
    async def test_cmd_add_word_emoji_in_message(
        self,
        mock_message,
        mock_state
    ):
        """Test instruction message contains emoji."""
        await cmd_add_word(mock_message, mock_state)

        call_args = mock_message.answer.call_args
        assert "📝" in call_args[0][0]


class TestProcessWordInput:
    """Tests for process_word_input handler."""

    @pytest.mark.asyncio
    async def test_process_word_input_validates_empty_word(
        self,
        mock_message,
        mock_state
    ):
        """Test empty word input is rejected."""
        mock_message.text = ""

        await process_word_input(mock_message, mock_state)

        # Verify error message is shown
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Please send a valid word" in call_args[0][0]

        # Verify state is not cleared
        mock_state.clear.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_word_input_validates_whitespace_only(
        self,
        mock_message,
        mock_state
    ):
        """Test whitespace-only input is rejected."""
        mock_message.text = "   "

        await process_word_input(mock_message, mock_state)

        # Verify error message is shown
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Please send a valid word" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_process_word_input_shows_processing_message(
        self,
        mock_message,
        mock_state,
        test_session,
        test_user_with_profile
    ):
        """Test processing message is shown."""
        mock_message.text = "hello"
        processing_msg = MagicMock(spec=Message)
        processing_msg.delete = AsyncMock()
        mock_message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])

        # Mock services
        with patch('src.words.bot.handlers.words.get_session') as mock_get_session:
            with patch('src.words.bot.handlers.words.LLMClient') as mock_llm:
                with patch('src.words.bot.handlers.words.WordService') as mock_word_service:
                    mock_get_session.return_value.__aenter__.return_value = test_session

                    # Mock translation and word addition
                    mock_service_instance = mock_word_service.return_value
                    mock_service_instance.get_word_with_translations = AsyncMock(return_value={
                        "translations": ["привет"],
                        "examples": [{"source": "Hello", "target": "Привет"}]
                    })
                    mock_service_instance.add_word_for_user = AsyncMock(return_value=MagicMock())

                    await process_word_input(mock_message, mock_state)

        # Verify processing message was shown
        assert mock_message.answer.call_count == 2
        first_call = mock_message.answer.call_args_list[0]
        assert "🔍 Looking up translations" in first_call[0][0]

    @pytest.mark.asyncio
    async def test_process_word_input_checks_user_profile(
        self,
        mock_message,
        mock_state,
        test_session
    ):
        """Test handler checks for user profile."""
        mock_message.text = "hello"
        processing_msg = MagicMock(spec=Message)
        processing_msg.delete = AsyncMock()
        mock_message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])

        with patch('src.words.bot.handlers.words.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            await process_word_input(mock_message, mock_state)

        # Verify user is asked to register
        assert mock_message.answer.call_count == 2
        second_call = mock_message.answer.call_args_list[1]
        assert "Please complete registration first" in second_call[0][0]

        # Verify state is cleared
        mock_state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_word_input_detects_target_to_native_language(
        self,
        mock_message,
        mock_state,
        test_session,
        test_user_with_profile
    ):
        """Test language detection for target→native (word in target language)."""
        mock_message.text = "hello"
        processing_msg = MagicMock(spec=Message)
        processing_msg.delete = AsyncMock()
        mock_message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])

        translation_data = {
            "translations": ["привет", "здравствуй"],
            "examples": [
                {"source": "Hello, world!", "target": "Привет, мир!"},
                {"source": "Hello there", "target": "Привет"}
            ]
        }

        with patch('src.words.bot.handlers.words.get_session') as mock_get_session:
            with patch('src.words.bot.handlers.words.LLMClient') as mock_llm:
                with patch('src.words.bot.handlers.words.WordService') as mock_word_service:
                    mock_get_session.return_value.__aenter__.return_value = test_session

                    # Mock translation and word addition
                    mock_service_instance = mock_word_service.return_value
                    mock_service_instance.get_word_with_translations = AsyncMock(
                        return_value=translation_data
                    )
                    mock_service_instance.add_word_for_user = AsyncMock(return_value=MagicMock())

                    await process_word_input(mock_message, mock_state)

        # Verify get_word_with_translations was called with correct languages
        mock_service_instance.get_word_with_translations.assert_called_once_with(
            "hello", "en", "ru"  # target→native
        )

        # Verify add_word_for_user was called with correct languages
        mock_service_instance.add_word_for_user.assert_called_once()
        call_kwargs = mock_service_instance.add_word_for_user.call_args[1]
        assert call_kwargs["source_language"] == "en"
        assert call_kwargs["target_language"] == "ru"

    @pytest.mark.asyncio
    async def test_process_word_input_detects_native_to_target_language(
        self,
        mock_message,
        mock_state,
        test_session,
        test_user_with_profile
    ):
        """Test language detection fallback for native→target (word in native language)."""
        mock_message.text = "привет"
        processing_msg = MagicMock(spec=Message)
        processing_msg.delete = AsyncMock()
        mock_message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])

        translation_data = {
            "translations": ["hello", "hi"],
            "examples": [
                {"source": "Привет, мир!", "target": "Hello, world!"},
                {"source": "Привет", "target": "Hello there"}
            ]
        }

        with patch('src.words.bot.handlers.words.get_session') as mock_get_session:
            with patch('src.words.bot.handlers.words.LLMClient') as mock_llm:
                with patch('src.words.bot.handlers.words.WordService') as mock_word_service:
                    mock_get_session.return_value.__aenter__.return_value = test_session

                    # Mock translation: first attempt fails, second succeeds
                    mock_service_instance = mock_word_service.return_value
                    mock_service_instance.get_word_with_translations = AsyncMock(
                        side_effect=[
                            Exception("Translation failed"),  # First attempt (target→native)
                            translation_data  # Second attempt (native→target)
                        ]
                    )
                    mock_service_instance.add_word_for_user = AsyncMock(return_value=MagicMock())

                    await process_word_input(mock_message, mock_state)

        # Verify get_word_with_translations was called twice (fallback)
        assert mock_service_instance.get_word_with_translations.call_count == 2

        # First call: target→native
        first_call = mock_service_instance.get_word_with_translations.call_args_list[0]
        assert first_call[0] == ("привет", "en", "ru")

        # Second call: native→target
        second_call = mock_service_instance.get_word_with_translations.call_args_list[1]
        assert second_call[0] == ("привет", "ru", "en")

        # Verify add_word_for_user was called with correct languages
        call_kwargs = mock_service_instance.add_word_for_user.call_args[1]
        assert call_kwargs["source_language"] == "ru"
        assert call_kwargs["target_language"] == "en"

    @pytest.mark.asyncio
    async def test_process_word_input_displays_translation_result(
        self,
        mock_message,
        mock_state,
        test_session,
        test_user_with_profile
    ):
        """Test translation result is displayed correctly."""
        mock_message.text = "hello"
        processing_msg = MagicMock(spec=Message)
        processing_msg.delete = AsyncMock()
        mock_message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])

        translation_data = {
            "translations": ["привет", "здравствуй", "алло"],
            "examples": [
                {"source": "Hello, world!", "target": "Привет, мир!"},
                {"source": "Hello there", "target": "Привет"}
            ]
        }

        with patch('src.words.bot.handlers.words.get_session') as mock_get_session:
            with patch('src.words.bot.handlers.words.LLMClient') as mock_llm:
                with patch('src.words.bot.handlers.words.WordService') as mock_word_service:
                    mock_get_session.return_value.__aenter__.return_value = test_session

                    mock_service_instance = mock_word_service.return_value
                    mock_service_instance.get_word_with_translations = AsyncMock(
                        return_value=translation_data
                    )
                    mock_service_instance.add_word_for_user = AsyncMock(return_value=MagicMock())

                    await process_word_input(mock_message, mock_state)

        # Verify processing message was deleted
        processing_msg.delete.assert_called_once()

        # Verify result message
        assert mock_message.answer.call_count == 2
        result_call = mock_message.answer.call_args_list[1]
        result_text = result_call[0][0]

        assert "✅ Word added to your vocabulary" in result_text
        assert "<b>hello</b>" in result_text
        assert "привет, здравствуй, алло" in result_text
        assert "Hello, world!" in result_text
        assert "Привет, мир!" in result_text
        assert "parse_mode" in result_call[1]
        assert result_call[1]["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    async def test_process_word_input_limits_examples_to_two(
        self,
        mock_message,
        mock_state,
        test_session,
        test_user_with_profile
    ):
        """Test only first 2 examples are displayed."""
        mock_message.text = "hello"
        processing_msg = MagicMock(spec=Message)
        processing_msg.delete = AsyncMock()
        mock_message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])

        translation_data = {
            "translations": ["привет"],
            "examples": [
                {"source": "Example 1", "target": "Пример 1"},
                {"source": "Example 2", "target": "Пример 2"},
                {"source": "Example 3", "target": "Пример 3"},
                {"source": "Example 4", "target": "Пример 4"}
            ]
        }

        with patch('src.words.bot.handlers.words.get_session') as mock_get_session:
            with patch('src.words.bot.handlers.words.LLMClient') as mock_llm:
                with patch('src.words.bot.handlers.words.WordService') as mock_word_service:
                    mock_get_session.return_value.__aenter__.return_value = test_session

                    mock_service_instance = mock_word_service.return_value
                    mock_service_instance.get_word_with_translations = AsyncMock(
                        return_value=translation_data
                    )
                    mock_service_instance.add_word_for_user = AsyncMock(return_value=MagicMock())

                    await process_word_input(mock_message, mock_state)

        # Verify result contains only first 2 examples
        result_call = mock_message.answer.call_args_list[1]
        result_text = result_call[0][0]

        assert "Example 1" in result_text
        assert "Example 2" in result_text
        assert "Example 3" not in result_text
        assert "Example 4" not in result_text

    @pytest.mark.asyncio
    async def test_process_word_input_clears_state_on_success(
        self,
        mock_message,
        mock_state,
        test_session,
        test_user_with_profile
    ):
        """Test FSM state is cleared after successful word addition."""
        mock_message.text = "hello"
        processing_msg = MagicMock(spec=Message)
        processing_msg.delete = AsyncMock()
        mock_message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])

        with patch('src.words.bot.handlers.words.get_session') as mock_get_session:
            with patch('src.words.bot.handlers.words.LLMClient') as mock_llm:
                with patch('src.words.bot.handlers.words.WordService') as mock_word_service:
                    mock_get_session.return_value.__aenter__.return_value = test_session

                    mock_service_instance = mock_word_service.return_value
                    mock_service_instance.get_word_with_translations = AsyncMock(
                        return_value={"translations": ["привет"], "examples": []}
                    )
                    mock_service_instance.add_word_for_user = AsyncMock(return_value=MagicMock())

                    await process_word_input(mock_message, mock_state)

        # Verify state is cleared
        mock_state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_word_input_handles_error_gracefully(
        self,
        mock_message,
        mock_state,
        test_session,
        test_user_with_profile
    ):
        """Test error handling shows user-friendly message."""
        mock_message.text = "hello"
        processing_msg = MagicMock(spec=Message)
        processing_msg.delete = AsyncMock()
        mock_message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])

        with patch('src.words.bot.handlers.words.get_session') as mock_get_session:
            with patch('src.words.bot.handlers.words.LLMClient') as mock_llm:
                with patch('src.words.bot.handlers.words.WordService') as mock_word_service:
                    mock_get_session.return_value.__aenter__.return_value = test_session

                    # Mock service to raise error
                    mock_service_instance = mock_word_service.return_value
                    mock_service_instance.get_word_with_translations = AsyncMock(
                        side_effect=[Exception("Service error"), Exception("Service error")]
                    )

                    await process_word_input(mock_message, mock_state)

        # Verify processing message was deleted
        processing_msg.delete.assert_called_once()

        # Verify error message is shown
        assert mock_message.answer.call_count == 2
        error_call = mock_message.answer.call_args_list[1]
        assert "❌ Failed to add word" in error_call[0][0]
        assert "try again later" in error_call[0][0]

        # Verify state is still cleared
        mock_state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_word_input_trims_whitespace(
        self,
        mock_message,
        mock_state,
        test_session,
        test_user_with_profile
    ):
        """Test word text is trimmed before processing."""
        mock_message.text = "  hello  "
        processing_msg = MagicMock(spec=Message)
        processing_msg.delete = AsyncMock()
        mock_message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])

        with patch('src.words.bot.handlers.words.get_session') as mock_get_session:
            with patch('src.words.bot.handlers.words.LLMClient') as mock_llm:
                with patch('src.words.bot.handlers.words.WordService') as mock_word_service:
                    mock_get_session.return_value.__aenter__.return_value = test_session

                    mock_service_instance = mock_word_service.return_value
                    mock_service_instance.get_word_with_translations = AsyncMock(
                        return_value={"translations": ["привет"], "examples": []}
                    )
                    mock_service_instance.add_word_for_user = AsyncMock(return_value=MagicMock())

                    await process_word_input(mock_message, mock_state)

        # Verify trimmed word was used
        mock_service_instance.get_word_with_translations.assert_called_once()
        call_args = mock_service_instance.get_word_with_translations.call_args
        assert call_args[0][0] == "hello"  # Trimmed

    @pytest.mark.asyncio
    async def test_process_word_input_uses_correct_user_id(
        self,
        mock_message,
        mock_state,
        test_session,
        test_user_with_profile
    ):
        """Test correct user ID is used for profile lookup."""
        mock_message.text = "hello"
        mock_message.from_user.id = 987654321
        processing_msg = MagicMock(spec=Message)
        processing_msg.delete = AsyncMock()
        mock_message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])

        with patch('src.words.bot.handlers.words.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            await process_word_input(mock_message, mock_state)

        # Verify no profile found for different user
        assert mock_message.answer.call_count == 2
        second_call = mock_message.answer.call_args_list[1]
        assert "Please complete registration first" in second_call[0][0]

    @pytest.mark.asyncio
    async def test_process_word_input_handles_empty_translations(
        self,
        mock_message,
        mock_state,
        test_session,
        test_user_with_profile
    ):
        """Test handling of empty translations list."""
        mock_message.text = "hello"
        processing_msg = MagicMock(spec=Message)
        processing_msg.delete = AsyncMock()
        mock_message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])

        translation_data = {
            "translations": [],
            "examples": []
        }

        with patch('src.words.bot.handlers.words.get_session') as mock_get_session:
            with patch('src.words.bot.handlers.words.LLMClient') as mock_llm:
                with patch('src.words.bot.handlers.words.WordService') as mock_word_service:
                    mock_get_session.return_value.__aenter__.return_value = test_session

                    mock_service_instance = mock_word_service.return_value
                    mock_service_instance.get_word_with_translations = AsyncMock(
                        return_value=translation_data
                    )
                    mock_service_instance.add_word_for_user = AsyncMock(return_value=MagicMock())

                    await process_word_input(mock_message, mock_state)

        # Verify success message is still shown (even with empty translations)
        result_call = mock_message.answer.call_args_list[1]
        result_text = result_call[0][0]
        assert "✅ Word added to your vocabulary" in result_text


class TestRouterConfiguration:
    """Tests for router configuration."""

    def test_router_has_correct_name(self):
        """Test router has correct name."""
        assert router.name == "words"

    def test_router_can_be_imported(self):
        """Test router can be imported from handlers package."""
        from src.words.bot.handlers import words_router
        assert words_router is router


class TestIntegration:
    """Integration tests for word addition flow."""

    @pytest.mark.asyncio
    async def test_complete_word_addition_flow(
        self,
        mock_message,
        mock_state,
        test_session,
        test_user_with_profile
    ):
        """Test complete flow from button click to word added."""
        # Step 1: Click ➕ Add Word button
        await cmd_add_word(mock_message, mock_state)
        mock_state.set_state.assert_called_with(AddWordStates.waiting_for_word)

        # Step 2: Enter word
        mock_message.text = "hello"
        processing_msg = MagicMock(spec=Message)
        processing_msg.delete = AsyncMock()
        mock_message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])

        with patch('src.words.bot.handlers.words.get_session') as mock_get_session:
            with patch('src.words.bot.handlers.words.LLMClient') as mock_llm:
                with patch('src.words.bot.handlers.words.WordService') as mock_word_service:
                    mock_get_session.return_value.__aenter__.return_value = test_session

                    mock_service_instance = mock_word_service.return_value
                    mock_service_instance.get_word_with_translations = AsyncMock(
                        return_value={
                            "translations": ["привет"],
                            "examples": [{"source": "Hello", "target": "Привет"}]
                        }
                    )
                    mock_service_instance.add_word_for_user = AsyncMock(return_value=MagicMock())

                    await process_word_input(mock_message, mock_state)

        # Verify state is cleared
        mock_state.clear.assert_called_once()

        # Verify success message shown
        result_call = mock_message.answer.call_args_list[1]
        assert "✅ Word added to your vocabulary" in result_call[0][0]
