"""
Comprehensive tests for start and registration handlers.

Tests cover:
- /start command for existing users
- /start command for new users
- Native language selection
- Target language selection
- Level selection and registration completion
- State transitions
- Validation logic (e.g., target != native language)
- Database operations
- Error cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, User as TgUser, Chat
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.words.bot.handlers.start import (
    cmd_start,
    process_native_language,
    process_target_language,
    process_level,
    router
)
from src.words.bot.states.registration import RegistrationStates
from src.words.services.user import UserService
from src.words.repositories.user import UserRepository, ProfileRepository
from src.words.models import Base, User, LanguageProfile, CEFRLevel
from src.words.config.constants import SUPPORTED_LANGUAGES


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
def mock_message():
    """Create mock Message object."""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TgUser)
    message.from_user.id = 123456789
    message.from_user.first_name = "Test"
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 123456789
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_callback():
    """Create mock CallbackQuery object."""
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TgUser)
    callback.from_user.id = 123456789
    callback.message = MagicMock(spec=Message)
    callback.message.edit_text = AsyncMock()
    callback.message.delete = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    callback.data = ""
    return callback


@pytest.fixture
def mock_state():
    """Create mock FSM context."""
    state = MagicMock(spec=FSMContext)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.clear = AsyncMock()
    return state


class TestCmdStart:
    """Tests for cmd_start handler."""

    @pytest.mark.asyncio
    async def test_cmd_start_existing_user_shows_main_menu(
        self,
        mock_message,
        mock_state,
        test_session
    ):
        """Test /start for existing user shows main menu."""
        # Create existing user in database
        user = User(
            user_id=123456789,
            native_language="ru",
            interface_language="ru"
        )
        test_session.add(user)
        await test_session.commit()

        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            await cmd_start(mock_message, mock_state)

        # Verify main menu is shown
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Welcome back" in call_args[0][0]
        assert call_args[1]['reply_markup'] is not None

        # Verify state is not changed
        mock_state.set_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_cmd_start_new_user_starts_registration(
        self,
        mock_message,
        mock_state,
        test_session
    ):
        """Test /start for new user starts registration flow."""
        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            await cmd_start(mock_message, mock_state)

        # Verify registration message is shown
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "Welcome to the Language Learning Bot" in call_args[0][0]
        assert "native language" in call_args[0][0]
        assert call_args[1]['reply_markup'] is not None

        # Verify state is set to native_language
        mock_state.set_state.assert_called_once_with(
            RegistrationStates.native_language
        )

    @pytest.mark.asyncio
    async def test_cmd_start_uses_correct_user_id(
        self,
        mock_message,
        mock_state,
        test_session
    ):
        """Test /start uses correct user ID from message."""
        mock_message.from_user.id = 987654321

        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            await cmd_start(mock_message, mock_state)

        # Verify that user lookup was attempted
        mock_state.set_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_start_creates_correct_keyboard(
        self,
        mock_message,
        mock_state,
        test_session
    ):
        """Test /start creates language keyboard for new users."""
        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            with patch('src.words.bot.handlers.start.build_language_keyboard') as mock_kb:
                mock_kb.return_value = MagicMock()
                mock_get_session.return_value.__aenter__.return_value = test_session

                await cmd_start(mock_message, mock_state)

        mock_kb.assert_called_once()


class TestProcessNativeLanguage:
    """Tests for process_native_language handler."""

    @pytest.mark.asyncio
    async def test_process_native_language_saves_selection(
        self,
        mock_callback,
        mock_state
    ):
        """Test native language selection is saved to state."""
        mock_callback.data = "select_language:ru"

        await process_native_language(mock_callback, mock_state)

        # Verify state is updated
        mock_state.update_data.assert_called_once_with(native_language="ru")

    @pytest.mark.asyncio
    async def test_process_native_language_transitions_to_target_language(
        self,
        mock_callback,
        mock_state
    ):
        """Test state transitions to target_language."""
        mock_callback.data = "select_language:en"

        await process_native_language(mock_callback, mock_state)

        # Verify state transition
        mock_state.set_state.assert_called_once_with(
            RegistrationStates.target_language
        )

    @pytest.mark.asyncio
    async def test_process_native_language_edits_message(
        self,
        mock_callback,
        mock_state
    ):
        """Test message is edited with next step."""
        mock_callback.data = "select_language:ru"

        await process_native_language(mock_callback, mock_state)

        # Verify message is edited
        mock_callback.message.edit_text.assert_called_once()
        call_args = mock_callback.message.edit_text.call_args
        assert "Русский" in call_args[0][0]
        assert "Which language do you want to learn" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_process_native_language_shows_language_keyboard(
        self,
        mock_callback,
        mock_state
    ):
        """Test language keyboard is shown for target selection."""
        mock_callback.data = "select_language:en"

        with patch('src.words.bot.handlers.start.build_language_keyboard') as mock_kb:
            mock_kb.return_value = MagicMock()

            await process_native_language(mock_callback, mock_state)

        mock_kb.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_native_language_answers_callback(
        self,
        mock_callback,
        mock_state
    ):
        """Test callback is answered."""
        mock_callback.data = "select_language:ru"

        await process_native_language(mock_callback, mock_state)

        mock_callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_native_language_parses_callback_data(
        self,
        mock_callback,
        mock_state
    ):
        """Test callback data is correctly parsed."""
        test_cases = [
            ("select_language:en", "en"),
            ("select_language:ru", "ru"),
            ("select_language:es", "es"),
        ]

        for callback_data, expected_lang in test_cases:
            mock_callback.data = callback_data
            mock_state.update_data.reset_mock()

            await process_native_language(mock_callback, mock_state)

            mock_state.update_data.assert_called_once_with(
                native_language=expected_lang
            )


class TestProcessTargetLanguage:
    """Tests for process_target_language handler."""

    @pytest.mark.asyncio
    async def test_process_target_language_saves_selection(
        self,
        mock_callback,
        mock_state
    ):
        """Test target language selection is saved to state."""
        mock_callback.data = "select_language:en"
        mock_state.get_data.return_value = {"native_language": "ru"}

        await process_target_language(mock_callback, mock_state)

        # Verify state is updated
        mock_state.update_data.assert_called_once_with(target_language="en")

    @pytest.mark.asyncio
    async def test_process_target_language_validates_different_from_native(
        self,
        mock_callback,
        mock_state
    ):
        """Test target language must be different from native."""
        mock_callback.data = "select_language:ru"
        mock_state.get_data.return_value = {"native_language": "ru"}

        await process_target_language(mock_callback, mock_state)

        # Verify alert is shown
        mock_callback.answer.assert_called_once()
        call_args = mock_callback.answer.call_args
        assert call_args[1]['show_alert'] is True
        assert "different language" in call_args[0][0]

        # Verify state is not updated or transitioned
        mock_state.update_data.assert_not_called()
        mock_state.set_state.assert_not_called()
        mock_callback.message.edit_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_target_language_transitions_to_level(
        self,
        mock_callback,
        mock_state
    ):
        """Test state transitions to level selection."""
        mock_callback.data = "select_language:en"
        mock_state.get_data.return_value = {"native_language": "ru"}

        await process_target_language(mock_callback, mock_state)

        # Verify state transition
        mock_state.set_state.assert_called_once_with(RegistrationStates.level)

    @pytest.mark.asyncio
    async def test_process_target_language_edits_message(
        self,
        mock_callback,
        mock_state
    ):
        """Test message is edited with next step."""
        mock_callback.data = "select_language:en"
        mock_state.get_data.return_value = {"native_language": "ru"}

        await process_target_language(mock_callback, mock_state)

        # Verify message is edited
        mock_callback.message.edit_text.assert_called_once()
        call_args = mock_callback.message.edit_text.call_args
        assert "English" in call_args[0][0]
        assert "current level" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_process_target_language_shows_level_keyboard(
        self,
        mock_callback,
        mock_state
    ):
        """Test level keyboard is shown."""
        mock_callback.data = "select_language:es"
        mock_state.get_data.return_value = {"native_language": "ru"}

        with patch('src.words.bot.handlers.start.build_level_keyboard') as mock_kb:
            mock_kb.return_value = MagicMock()

            await process_target_language(mock_callback, mock_state)

        mock_kb.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_target_language_handles_all_combinations(
        self,
        mock_callback,
        mock_state
    ):
        """Test all valid language combinations work."""
        languages = list(SUPPORTED_LANGUAGES.keys())

        for native in languages:
            for target in languages:
                if native == target:
                    continue

                mock_callback.data = f"select_language:{target}"
                mock_state.get_data.return_value = {"native_language": native}
                mock_state.update_data.reset_mock()
                mock_state.set_state.reset_mock()

                await process_target_language(mock_callback, mock_state)

                # Should successfully update and transition
                mock_state.update_data.assert_called_once()
                mock_state.set_state.assert_called_once()


class TestProcessLevel:
    """Tests for process_level handler."""

    @pytest.mark.asyncio
    async def test_process_level_creates_user(
        self,
        mock_callback,
        mock_state,
        test_session
    ):
        """Test user is created in database."""
        mock_callback.data = "select_level:A1"
        mock_callback.from_user.id = 123456789
        mock_state.get_data.return_value = {
            "native_language": "ru",
            "target_language": "en"
        }

        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            await process_level(mock_callback, mock_state)

        # Verify user was created
        user_repo = UserRepository(test_session)
        user = await user_repo.get_by_telegram_id(123456789)
        assert user is not None
        assert user.user_id == 123456789
        assert user.native_language == "ru"
        assert user.interface_language == "ru"

    @pytest.mark.asyncio
    async def test_process_level_creates_language_profile(
        self,
        mock_callback,
        mock_state,
        test_session
    ):
        """Test language profile is created in database."""
        mock_callback.data = "select_level:B2"
        mock_callback.from_user.id = 123456789
        mock_state.get_data.return_value = {
            "native_language": "ru",
            "target_language": "en"
        }

        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            await process_level(mock_callback, mock_state)

        # Verify profile was created
        profile_repo = ProfileRepository(test_session)
        profile = await profile_repo.get_active_profile(123456789)
        assert profile is not None
        assert profile.user_id == 123456789
        assert profile.target_language == "en"
        assert profile.level == CEFRLevel.B2
        assert profile.is_active is True

    @pytest.mark.asyncio
    async def test_process_level_shows_completion_message(
        self,
        mock_callback,
        mock_state,
        test_session
    ):
        """Test completion message is shown."""
        mock_callback.data = "select_level:A2"
        mock_callback.from_user.id = 123456789
        mock_state.get_data.return_value = {
            "native_language": "ru",
            "target_language": "es"
        }

        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            await process_level(mock_callback, mock_state)

        # Verify completion message
        mock_callback.message.delete.assert_called_once()
        mock_callback.message.answer.assert_called_once()
        call_args = mock_callback.message.answer.call_args
        assert "Registration complete" in call_args[0][0]
        assert "Español" in call_args[0][0]
        assert "A2" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_process_level_shows_main_menu(
        self,
        mock_callback,
        mock_state,
        test_session
    ):
        """Test main menu is shown after registration."""
        mock_callback.data = "select_level:C1"
        mock_callback.from_user.id = 123456789
        mock_state.get_data.return_value = {
            "native_language": "ru",
            "target_language": "en"
        }

        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            with patch('src.words.bot.handlers.start.build_main_menu') as mock_menu:
                mock_menu.return_value = MagicMock()
                mock_get_session.return_value.__aenter__.return_value = test_session

                await process_level(mock_callback, mock_state)

        mock_menu.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_level_clears_state(
        self,
        mock_callback,
        mock_state,
        test_session
    ):
        """Test FSM state is cleared after registration."""
        mock_callback.data = "select_level:B1"
        mock_callback.from_user.id = 123456789
        mock_state.get_data.return_value = {
            "native_language": "ru",
            "target_language": "en"
        }

        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            await process_level(mock_callback, mock_state)

        # Verify state is cleared
        mock_state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_level_answers_callback(
        self,
        mock_callback,
        mock_state,
        test_session
    ):
        """Test callback is answered."""
        mock_callback.data = "select_level:A1"
        mock_callback.from_user.id = 123456789
        mock_state.get_data.return_value = {
            "native_language": "ru",
            "target_language": "en"
        }

        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            await process_level(mock_callback, mock_state)

        mock_callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_level_handles_all_cefr_levels(
        self,
        mock_callback,
        mock_state,
        test_session
    ):
        """Test all CEFR levels can be selected."""
        from src.words.config.constants import CEFR_LEVELS

        for level in CEFR_LEVELS:
            # Reset session
            await test_session.rollback()

            mock_callback.data = f"select_level:{level}"
            mock_callback.from_user.id = 100000000 + CEFR_LEVELS.index(level)
            mock_state.get_data.return_value = {
                "native_language": "ru",
                "target_language": "en"
            }

            with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = test_session

                await process_level(mock_callback, mock_state)

            # Verify profile was created with correct level
            profile_repo = ProfileRepository(test_session)
            user_id = mock_callback.from_user.id
            profile = await profile_repo.get_active_profile(user_id)
            assert profile is not None
            assert profile.level == CEFRLevel[level]

    @pytest.mark.asyncio
    async def test_process_level_uses_native_as_interface_language(
        self,
        mock_callback,
        mock_state,
        test_session
    ):
        """Test interface language is set to native language."""
        mock_callback.data = "select_level:A1"
        mock_callback.from_user.id = 123456789
        mock_state.get_data.return_value = {
            "native_language": "es",
            "target_language": "en"
        }

        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session

            await process_level(mock_callback, mock_state)

        # Verify interface language
        user_repo = UserRepository(test_session)
        user = await user_repo.get_by_telegram_id(123456789)
        assert user.interface_language == "es"


class TestRegistrationFlowIntegration:
    """Integration tests for complete registration flow."""

    @pytest.mark.asyncio
    async def test_complete_registration_flow(
        self,
        mock_message,
        mock_callback,
        mock_state,
        test_session
    ):
        """Test complete registration flow from start to finish."""
        # Step 1: /start command
        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session
            await cmd_start(mock_message, mock_state)

        mock_state.set_state.assert_called_with(RegistrationStates.native_language)

        # Step 2: Select native language
        mock_callback.data = "select_language:ru"
        await process_native_language(mock_callback, mock_state)
        mock_state.set_state.assert_called_with(RegistrationStates.target_language)

        # Step 3: Select target language
        mock_callback.data = "select_language:en"
        mock_state.get_data.return_value = {"native_language": "ru"}
        await process_target_language(mock_callback, mock_state)
        mock_state.set_state.assert_called_with(RegistrationStates.level)

        # Step 4: Select level and complete
        mock_callback.data = "select_level:B1"
        mock_callback.from_user.id = 123456789
        mock_state.get_data.return_value = {
            "native_language": "ru",
            "target_language": "en"
        }

        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = test_session
            await process_level(mock_callback, mock_state)

        # Verify registration completed
        mock_state.clear.assert_called_once()

        # Verify database records
        user_repo = UserRepository(test_session)
        profile_repo = ProfileRepository(test_session)

        user = await user_repo.get_by_telegram_id(123456789)
        assert user is not None

        profile = await profile_repo.get_active_profile(123456789)
        assert profile is not None
        assert profile.target_language == "en"
        assert profile.level == CEFRLevel.B1


class TestRouterConfiguration:
    """Tests for router configuration."""

    def test_router_has_correct_name(self):
        """Test router has correct name."""
        assert router.name == "start"

    def test_router_can_be_imported(self):
        """Test router can be imported from handlers package."""
        from src.words.bot.handlers import start_router
        assert start_router is router


class TestErrorHandling:
    """Tests for error handling in handlers."""

    @pytest.mark.asyncio
    async def test_cmd_start_handles_database_error(
        self,
        mock_message,
        mock_state
    ):
        """Test /start handles database errors gracefully."""
        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.side_effect = Exception("DB error")

            with pytest.raises(Exception):
                await cmd_start(mock_message, mock_state)

    @pytest.mark.asyncio
    async def test_process_level_handles_service_error(
        self,
        mock_callback,
        mock_state
    ):
        """Test process_level handles service errors."""
        mock_callback.data = "select_level:A1"
        mock_callback.from_user.id = 123456789
        mock_state.get_data.return_value = {
            "native_language": "ru",
            "target_language": "en"
        }

        with patch('src.words.bot.handlers.start.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.side_effect = Exception("Service error")

            with pytest.raises(Exception):
                await process_level(mock_callback, mock_state)
