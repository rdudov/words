"""
Integration tests for lesson/statistics repositories.

These tests exercise real DB reads/writes and repository queries.
"""

import pytest
from datetime import datetime, timedelta, timezone

from src.words.repositories.lesson import LessonRepository, LessonAttemptRepository
from src.words.repositories.statistics import StatisticsRepository
from src.words.models import (
    User,
    LanguageProfile,
    CEFRLevel,
    Word,
    UserWord,
    Lesson,
    LessonAttempt,
)


@pytest.mark.asyncio
async def test_lesson_repository_queries(integration_test_session):
    session = integration_test_session
    lesson_repo = LessonRepository(session)

    user = User(user_id=20001, native_language="ru", interface_language="ru")
    profile = LanguageProfile(user_id=20001, target_language="en", level=CEFRLevel.B1)
    session.add_all([user, profile])
    await session.commit()

    now = datetime.now(timezone.utc)
    active_lesson = Lesson(profile_id=profile.profile_id, words_count=1)
    recent_lesson = Lesson(
        profile_id=profile.profile_id,
        words_count=1,
        completed_at=now - timedelta(minutes=10)
    )
    old_lesson = Lesson(
        profile_id=profile.profile_id,
        words_count=1,
        completed_at=now - timedelta(days=1)
    )
    session.add_all([active_lesson, recent_lesson, old_lesson])
    await session.commit()

    active = await lesson_repo.get_active_lesson(profile.profile_id)
    assert active is not None
    assert active.completed_at is None

    recent = await lesson_repo.get_recent_lessons(profile.profile_id, limit=1)
    assert len(recent) == 1
    assert recent[0].completed_at == recent_lesson.completed_at

    count_today = await lesson_repo.count_lessons_today(profile.profile_id)
    assert count_today == 1


@pytest.mark.asyncio
async def test_statistics_repository_updates(integration_test_session):
    session = integration_test_session
    stats_repo = StatisticsRepository(session)

    user = User(user_id=20002, native_language="ru", interface_language="ru")
    profile = LanguageProfile(user_id=20002, target_language="en", level=CEFRLevel.B1)
    word = Word(word="house", language="en")
    session.add_all([user, profile, word])
    await session.commit()

    user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
    session.add(user_word)
    await session.commit()

    stat = await stats_repo.update_stat(
        user_word_id=user_word.user_word_id,
        direction="native_to_foreign",
        test_type="multiple_choice",
        is_correct=True
    )
    await session.commit()

    assert stat.total_attempts == 1
    assert stat.correct_count == 1
    assert stat.total_correct == 1
    assert stat.total_errors == 0

    stat = await stats_repo.update_stat(
        user_word_id=user_word.user_word_id,
        direction="native_to_foreign",
        test_type="multiple_choice",
        is_correct=False
    )
    await session.commit()

    assert stat.total_attempts == 2
    assert stat.correct_count == 0
    assert stat.total_correct == 1
    assert stat.total_errors == 1


@pytest.mark.asyncio
async def test_lesson_attempt_repository_ordering(integration_test_session):
    session = integration_test_session
    attempt_repo = LessonAttemptRepository(session)

    user = User(user_id=20003, native_language="ru", interface_language="ru")
    profile = LanguageProfile(user_id=20003, target_language="en", level=CEFRLevel.B1)
    word = Word(word="cat", language="en")
    session.add_all([user, profile, word])
    await session.commit()

    user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
    lesson = Lesson(profile_id=profile.profile_id, words_count=2)
    session.add_all([user_word, lesson])
    await session.commit()

    attempt1 = LessonAttempt(
        lesson_id=lesson.lesson_id,
        user_word_id=user_word.user_word_id,
        direction="native_to_foreign",
        test_type="multiple_choice",
        user_answer="cat",
        correct_answer="cat",
        is_correct=True
    )
    attempt2 = LessonAttempt(
        lesson_id=lesson.lesson_id,
        user_word_id=user_word.user_word_id,
        direction="native_to_foreign",
        test_type="multiple_choice",
        user_answer="cat",
        correct_answer="cat",
        is_correct=True
    )
    session.add_all([attempt1, attempt2])
    await session.commit()

    attempts = await attempt_repo.get_lesson_attempts(lesson.lesson_id)
    assert [a.attempt_id for a in attempts] == sorted(a.attempt_id for a in attempts)
