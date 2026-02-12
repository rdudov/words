"""
Integration tests for lesson handlers with real database state.

These tests exercise the end-to-end lesson flow using real repositories
and database queries, while patching the async session factory.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Message, CallbackQuery, User as TgUser, Chat

from src.words.bot.handlers.lesson import (
    cmd_start_lesson,
    cancel_lesson_by_menu,
    process_multiple_choice_answer,
    process_input_answer,
)
from src.words.bot.states.registration import LessonStates
from src.words.config.settings import settings
from src.words.models import (
    User,
    LanguageProfile,
    CEFRLevel,
    Word,
    UserWord,
    WordStatistics,
)
from src.words.repositories.lesson import LessonRepository
from src.words.repositories.word import UserWordRepository


class InMemoryFSMContext:
    """Minimal async FSM context for handler integration tests."""

    def __init__(self) -> None:
        self._data: dict = {}
        self.state = None

    async def set_state(self, state) -> None:
        self.state = state

    async def update_data(self, **kwargs) -> None:
        self._data.update(kwargs)

    async def get_data(self) -> dict:
        return dict(self._data)

    async def get_state(self):
        return self.state

    async def clear(self) -> None:
        self._data.clear()
        self.state = None


async def _seed_lesson_data(session, user_id: int, input_ready: bool = False):
    user = User(user_id=user_id, native_language="ru", interface_language="ru")
    profile = LanguageProfile(
        user_id=user_id,
        target_language="en",
        level=CEFRLevel.B1,
        is_active=True
    )
    session.add_all([user, profile])
    await session.commit()

    # Create at least 3 words for the user's vocabulary to enable lessons
    words = [
        Word(word="forest", language="en", level="B1", translations={"ru": ["les"]}, frequency_rank=1),
        Word(word="road", language="en", level="B1", translations={"ru": ["doroga"]}, frequency_rank=2),
        Word(word="field", language="en", level="B1", translations={"ru": ["pole"]}, frequency_rank=3),
        Word(word="lake", language="en", level="B1", translations={"ru": ["ozero"]}, frequency_rank=4),
    ]
    session.add_all(words)
    await session.commit()

    # Add all words to user's vocabulary (need at least 3 for lessons to work)
    user_words = [
        UserWord(profile_id=profile.profile_id, word_id=word.word_id)
        for word in words
    ]
    session.add_all(user_words)
    await session.commit()

    if input_ready:
        # Mark all words as ready for input test to ensure selected word is input_ready
        stats = [
            WordStatistics(
                user_word_id=uw.user_word_id,
                direction="native_to_foreign",
                test_type="multiple_choice",
                correct_count=settings.choice_to_input_threshold,
                total_attempts=settings.choice_to_input_threshold
            )
            for uw in user_words
        ]
        session.add_all(stats)
        await session.commit()

    return profile, user_words[0]


@pytest.mark.asyncio
async def test_lesson_handler_cancels_on_menu_click(
    integration_test_session, monkeypatch
):
    """Test that clicking menu button during lesson cancels it properly."""
    session = integration_test_session
    profile, user_word = await _seed_lesson_data(session, user_id=77001)
    
    # Mock message and state
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TgUser)
    message.from_user.id = 77001
    message.text = "📚 Start Lesson"
    message.answer = AsyncMock(return_value=MagicMock())
    
    state = InMemoryFSMContext()
    
    # Patch get_session to return our test session
    def mock_get_session():
        class MockSessionContext:
            async def __aenter__(self):
                return session
            async def __aexit__(self, *args):
                pass
        return MockSessionContext()
    
    with patch('src.words.bot.handlers.lesson.get_session', mock_get_session):
        # Force native->foreign direction
        import src.words.services.lesson as lesson_module
        from src.words.config.constants import Direction
        monkeypatch.setattr(
            lesson_module.random,
            "choice",
            lambda _: Direction.NATIVE_TO_FOREIGN.value
        )
        
        # Start lesson
        await cmd_start_lesson(message, state)
        
        # Verify lesson started
        data = await state.get_data()
        assert data.get("lesson_id") is not None
        assert state.state == LessonStates.answering_question
        
        # Now user clicks "➕ Add Word" during lesson
        message.text = "➕ Add Word"
        message.answer = AsyncMock(return_value=MagicMock())
        
        await cancel_lesson_by_menu(message, state)
        
        # Verify lesson cancelled
        assert state.state is None
        data_after = await state.get_data()
        assert data_after == {}
        
        # Verify cancellation message was sent
        message.answer.assert_called_once()
        args, kwargs = message.answer.call_args
        assert "cancelled" in args[0].lower()


@pytest.mark.asyncio
async def test_lesson_handler_no_words_shows_helpful_message(
    integration_test_session, monkeypatch
):
    """Test that starting lesson with no words shows helpful message."""
    session = integration_test_session
    
    # Create user/profile but NO words
    from src.words.models import User, LanguageProfile, CEFRLevel
    user = User(user_id=77002, native_language="ru", interface_language="ru")
    profile = LanguageProfile(
        user_id=77002,
        target_language="en",
        level=CEFRLevel.B1,
        is_active=True
    )
    session.add_all([user, profile])
    await session.commit()
    
    # Mock message
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TgUser)
    message.from_user.id = 77002
    message.text = "📚 Start Lesson"
    processing_msg = MagicMock()
    processing_msg.delete = AsyncMock()
    message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])
    
    state = InMemoryFSMContext()
    
    # Patch get_session
    def mock_get_session():
        class MockSessionContext:
            async def __aenter__(self):
                return session
            async def __aexit__(self, *args):
                pass
        return MockSessionContext()
    
    with patch('src.words.bot.handlers.lesson.get_session', mock_get_session):
        await cmd_start_lesson(message, state)
        
        # Should show "no words" message
        assert message.answer.call_count == 2
        args, kwargs = message.answer.call_args
        assert "don't have any words" in args[0].lower()
        assert "add word" in args[0].lower()


@pytest.mark.asyncio
async def test_lesson_handler_works_with_few_words(
    integration_test_session, monkeypatch
):
    """Test that lessons can start even with only 2 words (will use input mode)."""
    session = integration_test_session
    
    # Create user/profile with only 2 words
    from src.words.models import User, LanguageProfile, CEFRLevel, Word, UserWord
    user = User(user_id=77003, native_language="ru", interface_language="ru")
    profile = LanguageProfile(
        user_id=77003,
        target_language="en",
        level=CEFRLevel.B1,
        is_active=True
    )
    session.add_all([user, profile])
    await session.commit()
    
    # Add only 2 words
    word1 = Word(word="cat", language="en", level="B1", translations={"ru": ["кот"]}, frequency_rank=1)
    word2 = Word(word="dog", language="en", level="B1", translations={"ru": ["собака"]}, frequency_rank=2)
    session.add_all([word1, word2])
    await session.commit()
    
    user_word1 = UserWord(profile_id=profile.profile_id, word_id=word1.word_id)
    user_word2 = UserWord(profile_id=profile.profile_id, word_id=word2.word_id)
    session.add_all([user_word1, user_word2])
    await session.commit()
    
    # Mock message
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TgUser)
    message.from_user.id = 77003
    message.text = "📚 Start Lesson"
    processing_msg = MagicMock()
    processing_msg.delete = AsyncMock()
    message.answer = AsyncMock(side_effect=[processing_msg, MagicMock()])
    
    state = InMemoryFSMContext()
    
    # Patch get_session
    def mock_get_session():
        class MockSessionContext:
            async def __aenter__(self):
                return session
            async def __aexit__(self, *args):
                pass
        return MockSessionContext()
    
    with patch('src.words.bot.handlers.lesson.get_session', mock_get_session):
        await cmd_start_lesson(message, state)
        
        # Should start lesson successfully (will fall back to input mode)
        assert message.answer.call_count == 2
        data = await state.get_data()
        assert data.get("lesson_id") is not None
        assert data.get("current_question") is not None
        # With only 2 words, multiple choice might not be possible, but lesson starts
        assert state.state == LessonStates.answering_question


@pytest.mark.asyncio
async def test_lesson_handler_clears_previous_state(
    integration_test_session, monkeypatch
):
    """Test that starting new lesson clears previous lesson state."""
    session = integration_test_session
    profile, user_word = await _seed_lesson_data(session, user_id=77004)
    
    # Mock message
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TgUser)
    message.from_user.id = 77004
    message.text = "📚 Start Lesson"
    message.answer = AsyncMock(return_value=MagicMock())
    
    state = InMemoryFSMContext()
    
    # Set some previous state
    await state.update_data(lesson_id=999, old_data="should_be_cleared")
    await state.set_state(LessonStates.answering_question)
    
    # Patch get_session
    def mock_get_session():
        class MockSessionContext:
            async def __aenter__(self):
                return session
            async def __aexit__(self, *args):
                pass
        return MockSessionContext()
    
    with patch('src.words.bot.handlers.lesson.get_session', mock_get_session):
        # Force direction
        import src.words.services.lesson as lesson_module
        from src.words.config.constants import Direction
        monkeypatch.setattr(
            lesson_module.random,
            "choice",
            lambda _: Direction.NATIVE_TO_FOREIGN.value
        )
        
        await cmd_start_lesson(message, state)
        
        # Verify new lesson started
        data = await state.get_data()
        assert data.get("old_data") is None  # Old data cleared
        assert data.get("lesson_id") is not None
        assert data.get("lesson_id") != 999  # New lesson ID


@pytest.mark.asyncio
async def test_lesson_handler_flow_completes_and_updates_schedule(
    integration_test_session, monkeypatch
):
    session = integration_test_session
    profile, user_word = await _seed_lesson_data(session, user_id=50001)

    monkeypatch.setattr(settings, "words_per_lesson", 1)

    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TgUser)
    message.from_user.id = profile.user_id
    message.chat = MagicMock(spec=Chat)
    message.chat.id = profile.user_id
    message.text = "📚 Start Lesson"

    processing_msg = MagicMock(spec=Message)
    processing_msg.delete = AsyncMock()
    message.answer = AsyncMock(return_value=processing_msg)

    state = InMemoryFSMContext()

    with patch("src.words.bot.handlers.lesson.get_session") as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = session

        await cmd_start_lesson(message, state)

        data = await state.get_data()
        question = data.get("current_question")
        assert question is not None

        callback = MagicMock(spec=CallbackQuery)
        callback.data = f"answer:0:{question['expected_answer']}"
        callback.message = message
        callback.answer = AsyncMock()

        await process_multiple_choice_answer(callback, state)

    assert await state.get_data() == {}

    user_word_repo = UserWordRepository(session)
    refreshed = await user_word_repo.get_by_id_with_details(user_word.user_word_id)
    assert refreshed.next_review_at is not None
    assert refreshed.review_interval == 1

    lesson_repo = LessonRepository(session)
    assert await lesson_repo.get_active_lesson(profile.profile_id) is None
    completed = await lesson_repo.get_recent_lessons(profile.profile_id, limit=1)
    assert completed
    assert completed[0].completed_at is not None


@pytest.mark.asyncio
async def test_lesson_handler_input_flow(
    integration_test_session, monkeypatch
):
    session = integration_test_session
    profile, user_word = await _seed_lesson_data(
        session,
        user_id=50002,
        input_ready=True
    )

    monkeypatch.setattr(settings, "words_per_lesson", 1)

    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TgUser)
    message.from_user.id = profile.user_id
    message.chat = MagicMock(spec=Chat)
    message.chat.id = profile.user_id
    message.text = "📚 Start Lesson"

    processing_msg = MagicMock(spec=Message)
    processing_msg.delete = AsyncMock()
    message.answer = AsyncMock(return_value=processing_msg)

    state = InMemoryFSMContext()

    with patch("src.words.bot.handlers.lesson.get_session") as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = session

        await cmd_start_lesson(message, state)

        data = await state.get_data()
        question = data.get("current_question")
        assert question is not None
        assert question["test_type"] == "input"

        input_message = MagicMock(spec=Message)
        input_message.text = question["expected_answer"]
        input_message.answer = AsyncMock(return_value=processing_msg)

        await process_input_answer(input_message, state)

    assert await state.get_data() == {}

    user_word_repo = UserWordRepository(session)
    refreshed = await user_word_repo.get_by_id_with_details(user_word.user_word_id)
    assert refreshed.next_review_at is not None
    assert refreshed.review_interval == 1
