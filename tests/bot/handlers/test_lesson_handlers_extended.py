"""
Extended integration tests for lesson handlers focusing on edge cases and user interactions.

These tests complement test_lesson_integration.py by testing:
- Answer processing and lesson continuation
- Callback-based answers (multiple choice)
- Error handling in handlers
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Message, CallbackQuery, User as TgUser, Chat

from src.words.bot.handlers.lesson import (
    cmd_start_lesson,
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
    Lesson,
    WordStatistics,
)


class InMemoryFSMContext:
    """Minimal async FSM context for handler integration tests."""

    def __init__(self) -> None:
        self._data: dict = {}
        self.state = None

    async def set_state(self, state) -> None:
        self.state = state

    async def get_state(self):
        """Get current state."""
        return self.state

    async def update_data(self, **kwargs) -> None:
        self._data.update(kwargs)

    async def get_data(self) -> dict:
        return dict(self._data)

    async def clear(self) -> None:
        self._data.clear()
        self.state = None


async def _seed_lesson_data(session, user_id: int, word_count: int = 3, input_ready: bool = False):
    """Seed database with user, profile and words for lesson testing."""
    user = User(user_id=user_id, native_language="ru", interface_language="ru")
    profile = LanguageProfile(
        user_id=user_id,
        target_language="en",
        level=CEFRLevel.B1,
        is_active=True
    )
    session.add_all([user, profile])
    await session.commit()

    # Create words with translations
    words = []
    for i in range(word_count):
        word = Word(
            word=f"testword{i}",
            language="en",
            level="B1",
            translations={"ru": [f"тестслово{i}"]},
            frequency_rank=i + 1
        )
        words.append(word)
    
    session.add_all(words)
    await session.commit()

    user_words = []
    for word in words:
        user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
        user_words.append(user_word)
    
    session.add_all(user_words)
    await session.commit()

    if input_ready and user_words:
        # Add statistics to trigger input mode
        stat = WordStatistics(
            user_word_id=user_words[0].user_word_id,
            direction="native_to_foreign",
            test_type="multiple_choice",
            correct_count=settings.choice_to_input_threshold,
            total_attempts=settings.choice_to_input_threshold
        )
        session.add(stat)
        await session.commit()

    return profile, user_words


@pytest.mark.asyncio
async def test_lesson_handler_processes_answer_and_continues(
    integration_test_session, monkeypatch
):
    """Test answering question and continuing to next question."""
    session = integration_test_session
    profile, user_words = await _seed_lesson_data(session, user_id=88001, word_count=3)
    
    # Mock message and state
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TgUser)
    message.from_user.id = 88001
    message.text = "📚 Start Lesson"
    processing_msg = MagicMock()
    processing_msg.delete = AsyncMock()
    message.answer = AsyncMock(side_effect=[processing_msg] + [MagicMock()] * 10)
    
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
        # Force direction
        import src.words.services.lesson as lesson_module
        from src.words.config.constants import Direction
        monkeypatch.setattr(
            lesson_module.random,
            "choice",
            lambda _: Direction.NATIVE_TO_FOREIGN.value
        )
        
        # Start lesson
        await cmd_start_lesson(message, state)
        
        # Get the question data from state
        data = await state.get_data()
        question_dict = data.get("current_question")
        assert question_dict is not None
        
        # Answer the question correctly
        message.text = question_dict["expected_answer"]
        message.answer = AsyncMock(side_effect=[MagicMock()] * 10)
        
        await process_input_answer(message, state)
        
        # Verify answer was processed
        assert message.answer.call_count >= 1
        
        # Verify we're still in answering state (lesson continues)
        assert state.state == LessonStates.answering_question
        
        # Verify new question was generated
        data_after = await state.get_data()
        new_question = data_after.get("current_question")
        assert new_question is not None
        assert new_question != question_dict


@pytest.mark.asyncio
async def test_lesson_handler_processes_callback_answer(
    integration_test_session, monkeypatch
):
    """Test processing answer from inline keyboard callback."""
    session = integration_test_session
    profile, user_words = await _seed_lesson_data(session, user_id=88002, word_count=1)
    
    # Add distractor words for multiple choice generation
    distractor_words = []
    for i in range(10, 15):
        word = Word(
            word=f"distword{i}",
            language="en",
            level="B1",
            translations={"ru": [f"дистракт{i}"]},
            frequency_rank=i + 100
        )
        distractor_words.append(word)
    session.add_all(distractor_words)
    await session.commit()
    
    # Mock callback and state
    callback = MagicMock(spec=CallbackQuery)
    callback.data = "answer:0:тестслово0"
    callback.message = MagicMock(spec=Message)
    processing_msg = MagicMock()
    processing_msg.delete = AsyncMock()
    callback.message.answer = AsyncMock(side_effect=[processing_msg, MagicMock(), MagicMock()])
    callback.message.from_user = MagicMock(spec=TgUser)
    callback.message.from_user.id = 88002
    callback.answer = AsyncMock()
    
    state = InMemoryFSMContext()
    
    # Set up lesson state
    lesson = Lesson(profile_id=profile.profile_id, words_count=1)
    session.add(lesson)
    await session.commit()
    
    # Create question dict
    question_dict = {
        "user_word_id": user_words[0].user_word_id,
        "word_id": user_words[0].word_id,
        "question_text": "testword0",
        "expected_answer": "тестслово0",
        "alternative_answers": [],
        "direction": "foreign_to_native",
        "test_type": "multiple_choice",
        "source_language": "en",
        "target_language": "ru",
        "options": ["тестслово0", "другое1", "другое2", "другое3"]
    }
    
    await state.update_data(
        lesson_id=lesson.lesson_id,
        selected_words=[user_words[0].user_word_id],
        current_question=question_dict
    )
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
        await process_multiple_choice_answer(callback, state)
        
        # Verify callback was answered
        callback.answer.assert_called_once()
        
        # Verify answer was processed
        callback.message.answer.assert_called()
        
        # Verify lesson completed (only 1 word)
        assert state.state is None


@pytest.mark.asyncio
async def test_lesson_handler_handles_incorrect_answer(
    integration_test_session, monkeypatch
):
    """Test that incorrect answer is handled properly."""
    session = integration_test_session
    profile, user_words = await _seed_lesson_data(session, user_id=88003, word_count=1)
    
    # Mock message
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TgUser)
    message.from_user.id = 88003
    message.text = "📚 Start Lesson"
    processing_msg = MagicMock()
    processing_msg.delete = AsyncMock()
    message.answer = AsyncMock(side_effect=[processing_msg] + [MagicMock()] * 10)
    
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
        # Force direction
        import src.words.services.lesson as lesson_module
        from src.words.config.constants import Direction
        monkeypatch.setattr(
            lesson_module.random,
            "choice",
            lambda _: Direction.NATIVE_TO_FOREIGN.value
        )
        
        # Start lesson
        await cmd_start_lesson(message, state)
        
        # Get the question
        data = await state.get_data()
        question_dict = data.get("current_question")
        
        # Answer INCORRECTLY
        message.text = "wrong_answer_xyz"
        message.answer = AsyncMock(side_effect=[MagicMock()] * 10)
        
        await process_input_answer(message, state)
        
        # Verify incorrect feedback was shown
        call_args_list = [call[0][0] for call in message.answer.call_args_list]
        incorrect_messages = [msg for msg in call_args_list if "incorrect" in msg.lower()]
        assert len(incorrect_messages) > 0
        
        # Lesson should complete (only 1 word)
        assert state.state is None


@pytest.mark.asyncio
async def test_lesson_handler_lost_state_recovery(
    integration_test_session, monkeypatch
):
    """Test that handler recovers gracefully when state is lost."""
    session = integration_test_session
    
    # Mock message with no state
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TgUser)
    message.from_user.id = 88004
    message.text = "some answer"
    message.answer = AsyncMock(return_value=MagicMock())
    
    state = InMemoryFSMContext()
    # State is empty (no lesson_id or question)
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
        await process_input_answer(message, state)
        
        # Should show error message
        message.answer.assert_called_once()
        args, kwargs = message.answer.call_args
        assert "state lost" in args[0].lower() or "start a new lesson" in args[0].lower()
        
        # State should be cleared
        assert state.state is None
