"""
Tests for Lesson and LessonAttempt ORM models.

This module tests the Lesson and LessonAttempt models, including:
- Lesson model creation and fields
- LessonAttempt model creation and fields
- Relationships between Lesson, LessonAttempt, LanguageProfile, and UserWord
- CASCADE delete behavior
- Timezone-aware datetime handling
- Indexes
- Table creation
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, inspect, event as sa_event, text as sa_text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.words.models import (
    Base, Lesson, LessonAttempt, User, LanguageProfile, CEFRLevel,
    Word, UserWord, WordStatusEnum
)


class TestLessonModel:
    """Tests for the Lesson model."""

    def test_lesson_model_has_required_fields(self):
        """Test that Lesson model has all required fields."""
        assert hasattr(Lesson, 'lesson_id')
        assert hasattr(Lesson, 'profile_id')
        assert hasattr(Lesson, 'started_at')
        assert hasattr(Lesson, 'completed_at')
        assert hasattr(Lesson, 'words_count')
        assert hasattr(Lesson, 'correct_answers')
        assert hasattr(Lesson, 'incorrect_answers')
        assert hasattr(Lesson, 'profile')
        assert hasattr(Lesson, 'attempts')

    def test_lesson_model_has_correct_tablename(self):
        """Test that Lesson model has the correct table name."""
        assert Lesson.__tablename__ == "lessons"

    @pytest.mark.asyncio
    async def test_create_lesson_with_minimum_fields(self):
        """Test creating a Lesson with only required fields."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create prerequisite records
            user = User(user_id=1000, native_language="ru", interface_language="ru")
            session.add(user)
            await session.commit()

            profile = LanguageProfile(user_id=1000, target_language="en", level=CEFRLevel.B1)
            session.add(profile)
            await session.commit()

            # Create Lesson
            lesson = Lesson(
                profile_id=profile.profile_id,
                words_count=10
            )
            session.add(lesson)
            await session.commit()
            await session.refresh(lesson)

            # Verify defaults
            assert lesson.lesson_id is not None
            assert lesson.profile_id == profile.profile_id
            assert lesson.started_at is not None
            assert lesson.started_at.tzinfo is not None
            assert lesson.completed_at is None
            assert lesson.words_count == 10
            assert lesson.correct_answers == 0
            assert lesson.incorrect_answers == 0

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_create_lesson_with_all_fields(self):
        """Test creating a Lesson with all fields populated."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        now = datetime.now(timezone.utc)
        started = now - timedelta(minutes=10)
        completed = now

        async with async_session() as session:
            user = User(user_id=2000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=2000, target_language="en", level=CEFRLevel.B2)
            session.add_all([user, profile])
            await session.commit()

            # Create Lesson with all fields
            lesson = Lesson(
                profile_id=profile.profile_id,
                started_at=started,
                completed_at=completed,
                words_count=20,
                correct_answers=15,
                incorrect_answers=5
            )
            session.add(lesson)
            await session.commit()
            await session.refresh(lesson)

            # Verify all fields
            assert lesson.started_at.tzinfo is not None
            assert lesson.completed_at is not None
            assert lesson.completed_at.tzinfo is not None
            assert lesson.words_count == 20
            assert lesson.correct_answers == 15
            assert lesson.incorrect_answers == 5

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_lesson_datetime_fields_are_timezone_aware(self):
        """Test that datetime fields are timezone-aware."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Test with naive datetimes (should be converted to UTC)
        naive_started = datetime(2025, 1, 1, 10, 0, 0)
        naive_completed = datetime(2025, 1, 1, 10, 30, 0)

        async with async_session() as session:
            user = User(user_id=3000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=3000, target_language="en", level=CEFRLevel.B1)
            session.add_all([user, profile])
            await session.commit()

            lesson = Lesson(
                profile_id=profile.profile_id,
                started_at=naive_started,
                completed_at=naive_completed,
                words_count=5
            )
            session.add(lesson)
            await session.commit()
            await session.refresh(lesson)

            # Verify all datetime fields are timezone-aware
            assert lesson.started_at.tzinfo is not None
            assert lesson.started_at.tzinfo == timezone.utc
            assert lesson.completed_at.tzinfo is not None
            assert lesson.completed_at.tzinfo == timezone.utc

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_lesson_relationship_to_profile(self):
        """Test Lesson relationship to LanguageProfile."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=4000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=4000, target_language="es", level=CEFRLevel.A2)
            session.add_all([user, profile])
            await session.commit()

            lesson = Lesson(profile_id=profile.profile_id, words_count=15)
            session.add(lesson)
            await session.commit()

            lesson_id = lesson.lesson_id

        # Query and load relationship
        async with async_session() as session:
            result = await session.execute(
                select(Lesson).where(Lesson.lesson_id == lesson_id)
            )
            lesson = result.scalar_one()

            # Load profile relationship
            result = await session.execute(
                select(LanguageProfile).where(LanguageProfile.profile_id == lesson.profile_id)
            )
            profile = result.scalar_one()

            assert profile is not None
            assert profile.target_language == "es"
            assert profile.level == CEFRLevel.A2

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cascade_delete_profile_removes_lessons(self):
        """Test that deleting a LanguageProfile cascades to delete related Lessons."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=5000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=5000, target_language="en", level=CEFRLevel.B1)
            session.add_all([user, profile])
            await session.commit()

            lesson1 = Lesson(profile_id=profile.profile_id, words_count=10)
            lesson2 = Lesson(profile_id=profile.profile_id, words_count=15)
            session.add_all([lesson1, lesson2])
            await session.commit()

            profile_id = profile.profile_id

            # Verify lessons exist
            result = await session.execute(
                select(Lesson).where(Lesson.profile_id == profile_id)
            )
            assert len(result.scalars().all()) == 2

            # Delete profile
            await session.delete(profile)
            await session.commit()

            # Verify lessons were deleted (CASCADE)
            result = await session.execute(
                select(Lesson).where(Lesson.profile_id == profile_id)
            )
            assert len(result.scalars().all()) == 0

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_profile_can_access_lessons_through_relationship(self):
        """Test that LanguageProfile can access its Lessons through relationship."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=6000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=6000, target_language="en", level=CEFRLevel.B1)
            session.add_all([user, profile])
            await session.commit()

            lesson1 = Lesson(profile_id=profile.profile_id, words_count=5)
            lesson2 = Lesson(profile_id=profile.profile_id, words_count=10)
            lesson3 = Lesson(profile_id=profile.profile_id, words_count=15)
            session.add_all([lesson1, lesson2, lesson3])
            await session.commit()

            profile_id = profile.profile_id

        # Query profile and access lessons
        async with async_session() as session:
            result = await session.execute(
                select(LanguageProfile).where(LanguageProfile.profile_id == profile_id)
            )
            profile = result.scalar_one()

            # Access lessons through relationship
            result = await session.execute(
                select(Lesson).where(Lesson.profile_id == profile.profile_id)
            )
            lessons = result.scalars().all()

            assert len(lessons) == 3

        await engine.dispose()


class TestLessonAttemptModel:
    """Tests for the LessonAttempt model."""

    def test_lesson_attempt_model_has_required_fields(self):
        """Test that LessonAttempt model has all required fields."""
        assert hasattr(LessonAttempt, 'attempt_id')
        assert hasattr(LessonAttempt, 'lesson_id')
        assert hasattr(LessonAttempt, 'user_word_id')
        assert hasattr(LessonAttempt, 'direction')
        assert hasattr(LessonAttempt, 'test_type')
        assert hasattr(LessonAttempt, 'user_answer')
        assert hasattr(LessonAttempt, 'correct_answer')
        assert hasattr(LessonAttempt, 'is_correct')
        assert hasattr(LessonAttempt, 'validation_method')
        assert hasattr(LessonAttempt, 'attempted_at')
        assert hasattr(LessonAttempt, 'lesson')
        assert hasattr(LessonAttempt, 'user_word')

    def test_lesson_attempt_model_has_correct_tablename(self):
        """Test that LessonAttempt model has the correct table name."""
        assert LessonAttempt.__tablename__ == "lesson_attempts"

    @pytest.mark.asyncio
    async def test_create_lesson_attempt_with_minimum_fields(self):
        """Test creating a LessonAttempt with only required fields."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create prerequisite records
            user = User(user_id=7000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=7000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="test", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            lesson = Lesson(profile_id=profile.profile_id, words_count=1)
            session.add(lesson)
            await session.commit()

            # Create LessonAttempt
            attempt = LessonAttempt(
                lesson_id=lesson.lesson_id,
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="translation",
                correct_answer="тест",
                is_correct=True
            )
            session.add(attempt)
            await session.commit()
            await session.refresh(attempt)

            # Verify fields
            assert attempt.attempt_id is not None
            assert attempt.lesson_id == lesson.lesson_id
            assert attempt.user_word_id == user_word.user_word_id
            assert attempt.direction == "en->ru"
            assert attempt.test_type == "translation"
            assert attempt.user_answer is None
            assert attempt.correct_answer == "тест"
            assert attempt.is_correct is True
            assert attempt.validation_method is None
            assert attempt.attempted_at is not None
            assert attempt.attempted_at.tzinfo is not None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_create_lesson_attempt_with_all_fields(self):
        """Test creating a LessonAttempt with all fields populated."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        now = datetime.now(timezone.utc)

        async with async_session() as session:
            user = User(user_id=8000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=8000, target_language="en", level=CEFRLevel.B2)
            word = Word(word="house", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            lesson = Lesson(profile_id=profile.profile_id, words_count=1)
            session.add_all([user_word, lesson])
            await session.commit()

            # Create LessonAttempt with all fields
            attempt = LessonAttempt(
                lesson_id=lesson.lesson_id,
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="translation",
                user_answer="дом",
                correct_answer="дом",
                is_correct=True,
                validation_method="exact",
                attempted_at=now
            )
            session.add(attempt)
            await session.commit()
            await session.refresh(attempt)

            # Verify all fields
            assert attempt.direction == "en->ru"
            assert attempt.test_type == "translation"
            assert attempt.user_answer == "дом"
            assert attempt.correct_answer == "дом"
            assert attempt.is_correct is True
            assert attempt.validation_method == "exact"
            assert attempt.attempted_at.tzinfo is not None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_lesson_attempt_datetime_fields_are_timezone_aware(self):
        """Test that datetime fields are timezone-aware."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Test with naive datetime (should be converted to UTC)
        naive_attempted = datetime(2025, 1, 1, 10, 0, 0)

        async with async_session() as session:
            user = User(user_id=9000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=9000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="time", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            lesson = Lesson(profile_id=profile.profile_id, words_count=1)
            session.add_all([user_word, lesson])
            await session.commit()

            attempt = LessonAttempt(
                lesson_id=lesson.lesson_id,
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="translation",
                correct_answer="время",
                is_correct=False,
                attempted_at=naive_attempted
            )
            session.add(attempt)
            await session.commit()
            await session.refresh(attempt)

            # Verify datetime field is timezone-aware
            assert attempt.attempted_at.tzinfo is not None
            assert attempt.attempted_at.tzinfo == timezone.utc

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_lesson_attempt_relationship_to_lesson(self):
        """Test LessonAttempt relationship to Lesson."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=10000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=10000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="relate", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            lesson = Lesson(profile_id=profile.profile_id, words_count=1)
            session.add_all([user_word, lesson])
            await session.commit()

            attempt = LessonAttempt(
                lesson_id=lesson.lesson_id,
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="translation",
                correct_answer="относиться",
                is_correct=True
            )
            session.add(attempt)
            await session.commit()

            attempt_id = attempt.attempt_id

        # Query and load relationship
        async with async_session() as session:
            result = await session.execute(
                select(LessonAttempt).where(LessonAttempt.attempt_id == attempt_id)
            )
            attempt = result.scalar_one()

            # Load lesson relationship
            result = await session.execute(
                select(Lesson).where(Lesson.lesson_id == attempt.lesson_id)
            )
            lesson = result.scalar_one()

            assert lesson is not None
            assert lesson.words_count == 1

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_lesson_attempt_relationship_to_user_word(self):
        """Test LessonAttempt relationship to UserWord."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=11000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=11000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="connect", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            lesson = Lesson(profile_id=profile.profile_id, words_count=1)
            session.add_all([user_word, lesson])
            await session.commit()

            attempt = LessonAttempt(
                lesson_id=lesson.lesson_id,
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="translation",
                correct_answer="соединять",
                is_correct=False
            )
            session.add(attempt)
            await session.commit()

            attempt_id = attempt.attempt_id

        # Query and load relationship
        async with async_session() as session:
            result = await session.execute(
                select(LessonAttempt).where(LessonAttempt.attempt_id == attempt_id)
            )
            attempt = result.scalar_one()

            # Load user_word relationship
            result = await session.execute(
                select(UserWord).where(UserWord.user_word_id == attempt.user_word_id)
            )
            user_word = result.scalar_one()

            assert user_word is not None
            # Load word to verify
            result = await session.execute(
                select(Word).where(Word.word_id == user_word.word_id)
            )
            word = result.scalar_one()
            assert word.word == "connect"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cascade_delete_lesson_removes_attempts(self):
        """Test that deleting a Lesson cascades to delete related LessonAttempts."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=12000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=12000, target_language="en", level=CEFRLevel.B1)
            word1 = Word(word="first", language="en")
            word2 = Word(word="second", language="en")
            session.add_all([user, profile, word1, word2])
            await session.commit()

            user_word1 = UserWord(profile_id=profile.profile_id, word_id=word1.word_id)
            user_word2 = UserWord(profile_id=profile.profile_id, word_id=word2.word_id)
            lesson = Lesson(profile_id=profile.profile_id, words_count=2)
            session.add_all([user_word1, user_word2, lesson])
            await session.commit()

            attempt1 = LessonAttempt(
                lesson_id=lesson.lesson_id,
                user_word_id=user_word1.user_word_id,
                direction="en->ru",
                test_type="translation",
                correct_answer="первый",
                is_correct=True
            )
            attempt2 = LessonAttempt(
                lesson_id=lesson.lesson_id,
                user_word_id=user_word2.user_word_id,
                direction="en->ru",
                test_type="translation",
                correct_answer="второй",
                is_correct=True
            )
            session.add_all([attempt1, attempt2])
            await session.commit()

            lesson_id = lesson.lesson_id

            # Verify attempts exist
            result = await session.execute(
                select(LessonAttempt).where(LessonAttempt.lesson_id == lesson_id)
            )
            assert len(result.scalars().all()) == 2

            # Delete lesson
            await session.delete(lesson)
            await session.commit()

            # Verify attempts were deleted (CASCADE)
            result = await session.execute(
                select(LessonAttempt).where(LessonAttempt.lesson_id == lesson_id)
            )
            assert len(result.scalars().all()) == 0

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_lesson_can_access_attempts_through_relationship(self):
        """Test that Lesson can access its LessonAttempts through relationship."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=13000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=13000, target_language="en", level=CEFRLevel.B1)
            words = [
                Word(word="apple", language="en"),
                Word(word="banana", language="en"),
                Word(word="cherry", language="en")
            ]
            session.add_all([user, profile] + words)
            await session.commit()

            user_words = [
                UserWord(profile_id=profile.profile_id, word_id=word.word_id)
                for word in words
            ]
            lesson = Lesson(profile_id=profile.profile_id, words_count=3)
            session.add_all(user_words + [lesson])
            await session.commit()

            attempts = [
                LessonAttempt(
                    lesson_id=lesson.lesson_id,
                    user_word_id=user_word.user_word_id,
                    direction="en->ru",
                    test_type="translation",
                    correct_answer=f"ответ{i}",
                    is_correct=True
                )
                for i, user_word in enumerate(user_words)
            ]
            session.add_all(attempts)
            await session.commit()

            lesson_id = lesson.lesson_id

        # Query lesson and access attempts
        async with async_session() as session:
            result = await session.execute(
                select(Lesson).where(Lesson.lesson_id == lesson_id)
            )
            lesson = result.scalar_one()

            # Access attempts through relationship
            result = await session.execute(
                select(LessonAttempt).where(LessonAttempt.lesson_id == lesson.lesson_id)
            )
            attempts = result.scalars().all()

            assert len(attempts) == 3

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_lesson_attempt_text_fields_can_store_long_answers(self):
        """Test that Text fields can store long answers."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        long_answer = "This is a very long answer. " * 50  # 1450 characters

        async with async_session() as session:
            user = User(user_id=14000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=14000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="long", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            lesson = Lesson(profile_id=profile.profile_id, words_count=1)
            session.add_all([user_word, lesson])
            await session.commit()

            attempt = LessonAttempt(
                lesson_id=lesson.lesson_id,
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="translation",
                user_answer=long_answer,
                correct_answer=long_answer,
                is_correct=True
            )
            session.add(attempt)
            await session.commit()
            await session.refresh(attempt)

            # Verify long text was stored
            assert len(attempt.user_answer) > 1000
            assert len(attempt.correct_answer) > 1000
            assert attempt.user_answer == long_answer

        await engine.dispose()


class TestIndexesAndConstraints:
    """Tests for database indexes on lessons and lesson_attempts tables."""

    @pytest.mark.asyncio
    async def test_lessons_table_has_profile_started_index(self):
        """Test that lessons table has composite index on (profile_id, started_at)."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            def check_index(connection):
                inspector = inspect(connection)
                indexes = inspector.get_indexes('lessons')
                index_names = [idx['name'] for idx in indexes]
                return 'idx_lessons_profile' in index_names

            has_index = await conn.run_sync(check_index)
            assert has_index, "Index 'idx_lessons_profile' not found on lessons table"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_lesson_attempts_table_has_lesson_index(self):
        """Test that lesson_attempts table has index on lesson_id."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            def check_index(connection):
                inspector = inspect(connection)
                indexes = inspector.get_indexes('lesson_attempts')
                index_names = [idx['name'] for idx in indexes]
                return 'idx_attempts_lesson' in index_names

            has_index = await conn.run_sync(check_index)
            assert has_index, "Index 'idx_attempts_lesson' not found on lesson_attempts table"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_lesson_attempts_table_has_user_word_index(self):
        """Test that lesson_attempts table has index on user_word_id."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            def check_index(connection):
                inspector = inspect(connection)
                indexes = inspector.get_indexes('lesson_attempts')
                index_names = [idx['name'] for idx in indexes]
                return 'idx_attempts_user_word' in index_names

            has_index = await conn.run_sync(check_index)
            assert has_index, "Index 'idx_attempts_user_word' not found on lesson_attempts table"

        await engine.dispose()


class TestTableCreation:
    """Tests for table creation and schema validation."""

    @pytest.mark.asyncio
    async def test_create_all_tables_including_lessons(self):
        """Test that all tables including lessons and lesson_attempts can be created without errors."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        # This should not raise any exceptions
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Verify tables were created
        table_names = list(Base.metadata.tables.keys())

        assert "lessons" in table_names
        assert "lesson_attempts" in table_names

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_complete_lesson_workflow(self):
        """Test complete workflow: create lesson, add attempts, mark as complete."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Setup
            user = User(user_id=15000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=15000, target_language="en", level=CEFRLevel.B1)
            words = [
                Word(word="one", language="en"),
                Word(word="two", language="en"),
                Word(word="three", language="en")
            ]
            session.add_all([user, profile] + words)
            await session.commit()

            user_words = [
                UserWord(profile_id=profile.profile_id, word_id=word.word_id)
                for word in words
            ]
            session.add_all(user_words)
            await session.commit()

            # Start lesson
            lesson = Lesson(
                profile_id=profile.profile_id,
                words_count=3,
                correct_answers=0,
                incorrect_answers=0
            )
            session.add(lesson)
            await session.commit()

            # Add attempts
            attempts = [
                LessonAttempt(
                    lesson_id=lesson.lesson_id,
                    user_word_id=user_words[0].user_word_id,
                    direction="en->ru",
                    test_type="translation",
                    user_answer="один",
                    correct_answer="один",
                    is_correct=True,
                    validation_method="exact"
                ),
                LessonAttempt(
                    lesson_id=lesson.lesson_id,
                    user_word_id=user_words[1].user_word_id,
                    direction="en->ru",
                    test_type="translation",
                    user_answer="два",
                    correct_answer="два",
                    is_correct=True,
                    validation_method="exact"
                ),
                LessonAttempt(
                    lesson_id=lesson.lesson_id,
                    user_word_id=user_words[2].user_word_id,
                    direction="en->ru",
                    test_type="translation",
                    user_answer="четыре",
                    correct_answer="три",
                    is_correct=False,
                    validation_method="exact"
                )
            ]
            session.add_all(attempts)
            await session.commit()

            # Update lesson statistics
            lesson.correct_answers = 2
            lesson.incorrect_answers = 1
            lesson.completed_at = datetime.now(timezone.utc)
            await session.commit()

            # Verify final state
            await session.refresh(lesson)
            assert lesson.completed_at is not None
            assert lesson.correct_answers == 2
            assert lesson.incorrect_answers == 1

            result = await session.execute(
                select(LessonAttempt).where(LessonAttempt.lesson_id == lesson.lesson_id)
            )
            stored_attempts = result.scalars().all()
            assert len(stored_attempts) == 3
            correct_count = sum(1 for a in stored_attempts if a.is_correct)
            assert correct_count == 2

        await engine.dispose()
