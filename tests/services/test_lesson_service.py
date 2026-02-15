"""
Integration tests for LessonService.

These tests exercise lesson orchestration, question generation,
and answer processing using a real database.
"""

from datetime import datetime, timedelta, timezone
import pytest
from unittest.mock import AsyncMock
from sqlalchemy import text

from src.words.config.constants import Direction, TestType as LessonTestType
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


async def _seed_profile_with_adaptive_words(session):
    user = User(user_id=40001, native_language="ru", interface_language="ru")
    profile = LanguageProfile(user_id=40001, target_language="en", level=CEFRLevel.B1)
    session.add_all([user, profile])
    await session.commit()

    overdue_word = Word(
        word="window",
        language="en",
        level="B1",
        translations={"ru": ["okno"]},
        frequency_rank=1
    )
    new_word = Word(
        word="river",
        language="en",
        level="B1",
        translations={"ru": ["reka"]},
        frequency_rank=2
    )
    mastered_word = Word(
        word="sun",
        language="en",
        level="B1",
        translations={"ru": ["solntse"]},
        frequency_rank=3
    )
    session.add_all([overdue_word, new_word, mastered_word])
    await session.commit()

    now = datetime.now(timezone.utc)
    overdue_user_word = UserWord(
        profile_id=profile.profile_id,
        word_id=overdue_word.word_id,
        status=WordStatusEnum.REVIEWING,
        next_review_at=now - timedelta(days=5),
        last_reviewed_at=now - timedelta(days=10)
    )
    new_user_word = UserWord(
        profile_id=profile.profile_id,
        word_id=new_word.word_id,
        status=WordStatusEnum.NEW
    )
    mastered_user_word = UserWord(
        profile_id=profile.profile_id,
        word_id=mastered_word.word_id,
        status=WordStatusEnum.MASTERED
    )
    session.add_all([overdue_user_word, new_user_word, mastered_user_word])
    await session.commit()

    return profile, overdue_user_word, new_user_word, mastered_user_word


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
    assert question.test_type == LessonTestType.MULTIPLE_CHOICE.value
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
        test_type=LessonTestType.MULTIPLE_CHOICE.value,
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
    assert question.test_type == LessonTestType.INPUT.value
    assert question.options is None


@pytest.mark.asyncio
async def test_get_words_for_lesson_prioritizes_overdue_and_excludes_mastered(
    integration_test_session
):
    session = integration_test_session
    profile, overdue_word, new_word, mastered_word = (
        await _seed_profile_with_adaptive_words(session)
    )

    lesson_repo = LessonRepository(session)
    attempt_repo = LessonAttemptRepository(session)
    user_word_repo = UserWordRepository(session)
    word_repo = WordRepository(session)
    stats_repo = StatisticsRepository(session)

    translation_service = AsyncMock()
    validation_service = ValidationService(translation_service)

    lesson_service = LessonService(
        lesson_repo=lesson_repo,
        attempt_repo=attempt_repo,
        user_word_repo=user_word_repo,
        word_repo=word_repo,
        stats_repo=stats_repo,
        validation_service=validation_service
    )

    selected = await lesson_service.get_words_for_lesson(
        profile_id=profile.profile_id,
        count=2
    )

    selected_ids = [word.user_word_id for word in selected]
    assert mastered_word.user_word_id not in selected_ids
    assert overdue_word.user_word_id in selected_ids
    assert new_word.user_word_id in selected_ids
    assert selected[0].user_word_id == overdue_word.user_word_id


@pytest.mark.asyncio
async def test_get_words_for_lesson_backfills_from_frequency_words(
    integration_test_session
):
    session = integration_test_session
    user = User(user_id=41001, native_language="ru", interface_language="ru")
    profile = LanguageProfile(user_id=41001, target_language="en", level=CEFRLevel.B1)
    session.add_all([user, profile])
    await session.commit()

    words = [
        Word(word="alpha", language="en", level="B1", frequency_rank=1, translations={"ru": ["альфа"]}),
        Word(word="beta", language="en", level="B1", frequency_rank=2, translations={"ru": ["бета"]}),
        Word(word="gamma", language="en", level="B1", frequency_rank=3, translations={"ru": ["гамма"]}),
    ]
    session.add_all(words)
    await session.commit()

    # User initially has only one word in personal vocabulary.
    session.add(UserWord(profile_id=profile.profile_id, word_id=words[0].word_id))
    await session.commit()

    lesson_service = LessonService(
        lesson_repo=LessonRepository(session),
        attempt_repo=LessonAttemptRepository(session),
        user_word_repo=UserWordRepository(session),
        word_repo=WordRepository(session),
        stats_repo=StatisticsRepository(session),
        validation_service=ValidationService(AsyncMock()),
    )

    selected = await lesson_service.get_words_for_lesson(
        profile_id=profile.profile_id,
        count=3,
        target_language="en",
        level="B1",
    )
    assert len(selected) == 3

    all_user_words = await lesson_service.user_word_repo.get_user_vocabulary(profile.profile_id)
    assert len(all_user_words) == 3


@pytest.mark.asyncio
async def test_process_answer_updates_spaced_repetition_and_status(
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
        lambda _: Direction.NATIVE_TO_FOREIGN.value
    )

    selected_words = await user_word_repo.get_user_words_for_lesson(profile.profile_id)
    question = await lesson_service.generate_next_question(lesson, selected_words)
    assert question is not None

    before = await user_word_repo.get_by_id_with_details(user_word.user_word_id)
    previous_ef = before.easiness_factor

    await lesson_service.process_answer(
        lesson_id=lesson.lesson_id,
        question=question,
        user_answer=question.expected_answer
    )

    refreshed = await user_word_repo.get_by_id_with_details(user_word.user_word_id)
    assert refreshed.review_interval == 1
    assert refreshed.next_review_at is not None
    assert refreshed.next_review_at.tzinfo is not None
    assert refreshed.easiness_factor > previous_ef
    assert refreshed.status == WordStatusEnum.LEARNING


@pytest.mark.asyncio
async def test_process_answer_incorrect_resets_interval_and_decreases_ef(
    integration_test_session, monkeypatch
):
    session = integration_test_session
    _, profile, user_word = await _seed_profile_with_words(session)

    user_word.review_interval = 6
    user_word.easiness_factor = 2.5
    await session.commit()

    lesson_repo = LessonRepository(session)
    attempt_repo = LessonAttemptRepository(session)
    user_word_repo = UserWordRepository(session)
    word_repo = WordRepository(session)
    stats_repo = StatisticsRepository(session)

    translation_service = AsyncMock()
    translation_service.validate_answer_with_llm.return_value = (False, "no")
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
        lambda _: Direction.NATIVE_TO_FOREIGN.value
    )

    selected_words = await user_word_repo.get_user_words_for_lesson(profile.profile_id)
    question = await lesson_service.generate_next_question(lesson, selected_words)
    assert question is not None

    await lesson_service.process_answer(
        lesson_id=lesson.lesson_id,
        question=question,
        user_answer="wrong-answer"
    )

    refreshed = await user_word_repo.get_by_id_with_details(user_word.user_word_id)
    assert refreshed.review_interval == 1
    assert refreshed.next_review_at is not None
    assert refreshed.easiness_factor < 2.5
    assert refreshed.easiness_factor >= 1.3


@pytest.mark.asyncio
async def test_generate_options_returns_none_when_insufficient_distractors(
    integration_test_session
):
    """Test that _generate_options returns None if < 2 options found."""
    session = integration_test_session
    _, profile, user_word = await _seed_profile_with_words(session)

    lesson_repo = LessonRepository(session)
    attempt_repo = LessonAttemptRepository(session)
    user_word_repo = UserWordRepository(session)
    word_repo = WordRepository(session)
    stats_repo = StatisticsRepository(session)

    translation_service = AsyncMock()
    validation_service = ValidationService(translation_service)

    lesson_service = LessonService(
        lesson_repo=lesson_repo,
        attempt_repo=attempt_repo,
        user_word_repo=user_word_repo,
        word_repo=word_repo,
        stats_repo=stats_repo,
        validation_service=validation_service
    )

    # Delete all distractor words from DB
    await session.execute(text("DELETE FROM words WHERE word != 'house'"))
    await session.commit()

    detailed = await user_word_repo.get_by_id_with_details(user_word.user_word_id)
    word = detailed.word

    options = await lesson_service._generate_options(
        correct_answer="дом",
        word=word,
        direction=Direction.NATIVE_TO_FOREIGN.value,
        native_lang="ru",
        target_lang="en",
        level="B1",
        count=4
    )

    # Should return None (insufficient options)
    assert options is None


@pytest.mark.asyncio
async def test_question_falls_back_to_input_when_no_distractors(
    integration_test_session, monkeypatch
):
    """Test that question type falls back to INPUT when no distractors available."""
    session = integration_test_session
    _, profile, user_word = await _seed_profile_with_words(session)

    # Delete all distractor words from DB
    await session.execute(text("DELETE FROM words WHERE word != 'house'"))
    await session.commit()

    lesson_repo = LessonRepository(session)
    attempt_repo = LessonAttemptRepository(session)
    user_word_repo = UserWordRepository(session)
    word_repo = WordRepository(session)
    stats_repo = StatisticsRepository(session)

    translation_service = AsyncMock()
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
        lambda _: Direction.NATIVE_TO_FOREIGN.value
    )

    selected_words = await user_word_repo.get_user_words_for_lesson(profile.profile_id)
    question = await lesson_service.generate_next_question(lesson, selected_words)

    assert question is not None
    # Should fallback to INPUT when no distractors
    assert question.test_type == LessonTestType.INPUT.value
    assert question.options is None
