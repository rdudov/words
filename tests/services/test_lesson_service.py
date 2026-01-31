"""
Integration tests for LessonService.

These tests exercise lesson orchestration, question generation,
and answer processing using a real database.
"""

import pytest
from unittest.mock import AsyncMock

from src.words.config.constants import Direction, TestType
from src.words.config.settings import settings
from src.words.models import (
    User,
    LanguageProfile,
    CEFRLevel,
    Word,
    UserWord,
    WordStatistics,
    WordStatusEnum,
)
from src.words.repositories.lesson import LessonRepository, LessonAttemptRepository
from src.words.repositories.statistics import StatisticsRepository
from src.words.repositories.word import UserWordRepository, WordRepository
from src.words.services.lesson import LessonService
from src.words.services.validation import ValidationService


async def _seed_profile_with_words(session):
    user = User(user_id=30001, native_language="ru", interface_language="ru")
    profile = LanguageProfile(user_id=30001, target_language="en", level=CEFRLevel.B1)
    session.add_all([user, profile])
    await session.commit()

    main_word = Word(
        word="house",
        language="en",
        level="B1",
        translations={"ru": ["дом", "жилище"]},
        frequency_rank=1
    )
    distractors = [
        Word(word="cat", language="en", level="B1", translations={"ru": ["кот"]}, frequency_rank=2),
        Word(word="dog", language="en", level="B1", translations={"ru": ["собака"]}, frequency_rank=3),
        Word(word="tree", language="en", level="B1", translations={"ru": ["дерево"]}, frequency_rank=4),
    ]
    session.add_all([main_word] + distractors)
    await session.commit()

    user_word = UserWord(profile_id=profile.profile_id, word_id=main_word.word_id)
    session.add(user_word)
    await session.commit()

    return user, profile, user_word


@pytest.mark.asyncio
async def test_lesson_flow_records_attempt_and_updates_stats(
    integration_test_session, monkeypatch
):
    session = integration_test_session
    _, profile, user_word = await _seed_profile_with_words(session)

    lesson_repo = LessonRepository(session)
    attempt_repo = LessonAttemptRepository(session)
    user_word_repo = UserWordRepository(session)
    word_repo = WordRepository(session)
    stats_repo = StatisticsRepository(session)

    translation_service = AsyncMock()
    translation_service.validate_answer_with_llm.return_value = (True, "ok")
    validation_service = ValidationService(translation_service)

    lesson_service = LessonService(
        lesson_repo=lesson_repo,
        attempt_repo=attempt_repo,
        user_word_repo=user_word_repo,
        word_repo=word_repo,
        stats_repo=stats_repo,
        validation_service=validation_service
    )

    lesson = await lesson_service.get_or_create_active_lesson(
        profile_id=profile.profile_id,
        words_count=1
    )

    # Force deterministic direction (native -> foreign)
    import src.words.services.lesson as lesson_module
    monkeypatch.setattr(
        lesson_module.random,
        "choice",
        lambda _: Direction.NATIVE_TO_FOREIGN.value
    )

    selected_words = await user_word_repo.get_user_words_for_lesson(profile.profile_id)
    question = await lesson_service.generate_next_question(lesson, selected_words)
    assert question is not None
    assert question.test_type == TestType.MULTIPLE_CHOICE.value
    assert question.options is not None
    assert question.expected_answer in question.options

    await lesson_service.process_answer(
        lesson_id=lesson.lesson_id,
        question=question,
        user_answer=question.expected_answer
    )

    attempts = await attempt_repo.get_lesson_attempts(lesson.lesson_id)
    assert len(attempts) == 1
    assert attempts[0].is_correct is True

    # Stats updated
    stats = await stats_repo.get_or_create_stat(
        user_word_id=user_word.user_word_id,
        direction=question.direction,
        test_type=question.test_type
    )
    assert stats.total_attempts == 1
    assert stats.correct_count == 1
    assert stats.total_correct == 1

    # Lesson counters updated
    refreshed_lesson = await lesson_repo.get_by_id(lesson.lesson_id)
    assert refreshed_lesson.correct_answers == 1
    assert refreshed_lesson.incorrect_answers == 0

    # User word status progresses from NEW -> LEARNING
    refreshed_user_word = await user_word_repo.get_by_id_with_details(user_word.user_word_id)
    assert refreshed_user_word.status == WordStatusEnum.LEARNING
    assert refreshed_user_word.last_reviewed_at is not None


@pytest.mark.asyncio
async def test_question_switches_to_input_after_threshold(
    integration_test_session, monkeypatch
):
    session = integration_test_session
    _, profile, user_word = await _seed_profile_with_words(session)

    # Add statistics to trigger input mode
    stat = WordStatistics(
        user_word_id=user_word.user_word_id,
        direction=Direction.NATIVE_TO_FOREIGN.value,
        test_type=TestType.MULTIPLE_CHOICE.value,
        correct_count=settings.choice_to_input_threshold,
        total_attempts=settings.choice_to_input_threshold
    )
    session.add(stat)
    await session.commit()

    lesson_repo = LessonRepository(session)
    attempt_repo = LessonAttemptRepository(session)
    user_word_repo = UserWordRepository(session)
    word_repo = WordRepository(session)
    stats_repo = StatisticsRepository(session)

    translation_service = AsyncMock()
    translation_service.validate_answer_with_llm.return_value = (True, "ok")
    validation_service = ValidationService(translation_service)

    lesson_service = LessonService(
        lesson_repo=lesson_repo,
        attempt_repo=attempt_repo,
        user_word_repo=user_word_repo,
        word_repo=word_repo,
        stats_repo=stats_repo,
        validation_service=validation_service
    )

    lesson = await lesson_service.get_or_create_active_lesson(
        profile_id=profile.profile_id,
        words_count=1
    )

    import src.words.services.lesson as lesson_module
    monkeypatch.setattr(
        lesson_module.random,
        "choice",
        lambda _: Direction.FOREIGN_TO_NATIVE.value
    )

    selected_words = await user_word_repo.get_user_words_for_lesson(profile.profile_id)
    question = await lesson_service.generate_next_question(lesson, selected_words)

    assert question is not None
    assert question.test_type == TestType.INPUT.value
    assert question.options is None
