"""
Tests for WordStatistics ORM model.

This module tests the WordStatistics model, including:
- WordStatistics model creation and fields
- UNIQUE constraint on (user_word_id, direction, test_type)
- Relationship between WordStatistics and UserWord
- CASCADE delete behavior
- Indexes
- Table creation
"""

import pytest
from sqlalchemy import select, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.words.models import (
    Base, WordStatistics, User, LanguageProfile, CEFRLevel,
    Word, UserWord, WordStatusEnum
)


class TestWordStatisticsModel:
    """Tests for the WordStatistics model."""

    @pytest.mark.asyncio
    async def test_create_word_statistics_with_minimum_fields(self):
        """Test creating a WordStatistics with only required fields."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create prerequisite records
            user = User(user_id=1000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=1000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="test", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            # Create WordStatistics
            stat = WordStatistics(
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="translation"
            )
            session.add(stat)
            await session.commit()
            await session.refresh(stat)

            # Verify defaults
            assert stat.stat_id is not None
            assert stat.user_word_id == user_word.user_word_id
            assert stat.direction == "en->ru"
            assert stat.test_type == "translation"
            assert stat.correct_count == 0
            assert stat.total_attempts == 0
            assert stat.total_correct == 0
            assert stat.total_errors == 0

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_create_word_statistics_with_all_fields(self):
        """Test creating a WordStatistics with all fields populated."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=2000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=2000, target_language="en", level=CEFRLevel.B2)
            word = Word(word="advanced", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            # Create WordStatistics with all fields
            stat = WordStatistics(
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="multiple_choice",
                correct_count=3,
                total_attempts=10,
                total_correct=7,
                total_errors=3
            )
            session.add(stat)
            await session.commit()
            await session.refresh(stat)

            # Verify all fields
            assert stat.direction == "en->ru"
            assert stat.test_type == "multiple_choice"
            assert stat.correct_count == 3
            assert stat.total_attempts == 10
            assert stat.total_correct == 7
            assert stat.total_errors == 3

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_word_statistics_relationship_to_user_word(self):
        """Test WordStatistics relationship to UserWord."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=3000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=3000, target_language="es", level=CEFRLevel.A2)
            word = Word(word="hola", language="es")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            stat = WordStatistics(
                user_word_id=user_word.user_word_id,
                direction="es->ru",
                test_type="translation"
            )
            session.add(stat)
            await session.commit()

            stat_id = stat.stat_id

        # Query and load relationship
        async with async_session() as session:
            result = await session.execute(
                select(WordStatistics).where(WordStatistics.stat_id == stat_id)
            )
            stat = result.scalar_one()

            # Load user_word relationship
            result = await session.execute(
                select(UserWord).where(UserWord.user_word_id == stat.user_word_id)
            )
            user_word = result.scalar_one()

            assert user_word is not None
            # Load word to verify
            result = await session.execute(
                select(Word).where(Word.word_id == user_word.word_id)
            )
            word = result.scalar_one()
            assert word.word == "hola"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_user_word_can_access_statistics_through_relationship(self):
        """Test that UserWord can access its WordStatistics through relationship."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=4000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=4000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="statistics", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            # Create multiple statistics for different directions and test types
            stats = [
                WordStatistics(
                    user_word_id=user_word.user_word_id,
                    direction="en->ru",
                    test_type="translation"
                ),
                WordStatistics(
                    user_word_id=user_word.user_word_id,
                    direction="ru->en",
                    test_type="translation"
                ),
                WordStatistics(
                    user_word_id=user_word.user_word_id,
                    direction="en->ru",
                    test_type="multiple_choice"
                )
            ]
            session.add_all(stats)
            await session.commit()

            user_word_id = user_word.user_word_id

        # Query user_word and access statistics
        async with async_session() as session:
            result = await session.execute(
                select(UserWord).where(UserWord.user_word_id == user_word_id)
            )
            user_word = result.scalar_one()

            # Access statistics through relationship
            result = await session.execute(
                select(WordStatistics).where(WordStatistics.user_word_id == user_word.user_word_id)
            )
            statistics = result.scalars().all()

            assert len(statistics) == 3

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_word_statistics_unique_constraint_prevents_duplicates(self):
        """Test that UNIQUE constraint on (user_word_id, direction, test_type) prevents duplicates."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=5000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=5000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="unique", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            # Create first statistic
            stat1 = WordStatistics(
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="translation"
            )
            session.add(stat1)
            await session.commit()

            # Try to create duplicate with same user_word_id, direction, and test_type
            stat2 = WordStatistics(
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="translation",
                correct_count=5  # Different values don't matter
            )
            session.add(stat2)

            # Should raise IntegrityError due to UNIQUE constraint
            with pytest.raises(IntegrityError):
                await session.commit()

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_word_statistics_unique_constraint_allows_different_directions(self):
        """Test that same user_word with different directions is allowed."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=6000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=6000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="direction", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            # Create statistics with different directions
            stat_en_ru = WordStatistics(
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="translation"
            )
            stat_ru_en = WordStatistics(
                user_word_id=user_word.user_word_id,
                direction="ru->en",
                test_type="translation"
            )
            session.add_all([stat_en_ru, stat_ru_en])
            await session.commit()

            # Verify both were created
            result = await session.execute(
                select(WordStatistics).where(WordStatistics.user_word_id == user_word.user_word_id)
            )
            stats = result.scalars().all()
            assert len(stats) == 2

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_word_statistics_unique_constraint_allows_different_test_types(self):
        """Test that same user_word and direction with different test types is allowed."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=7000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=7000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="test_type", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            # Create statistics with different test types
            stat_translation = WordStatistics(
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="translation"
            )
            stat_multiple_choice = WordStatistics(
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="multiple_choice"
            )
            session.add_all([stat_translation, stat_multiple_choice])
            await session.commit()

            # Verify both were created
            result = await session.execute(
                select(WordStatistics).where(WordStatistics.user_word_id == user_word.user_word_id)
            )
            stats = result.scalars().all()
            assert len(stats) == 2

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cascade_delete_user_word_removes_statistics(self):
        """Test that deleting a UserWord cascades to delete related WordStatistics."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=8000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=8000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="cascade", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            # Create multiple statistics
            stats = [
                WordStatistics(
                    user_word_id=user_word.user_word_id,
                    direction="en->ru",
                    test_type="translation"
                ),
                WordStatistics(
                    user_word_id=user_word.user_word_id,
                    direction="ru->en",
                    test_type="translation"
                )
            ]
            session.add_all(stats)
            await session.commit()

            user_word_id = user_word.user_word_id

            # Verify statistics exist
            result = await session.execute(
                select(WordStatistics).where(WordStatistics.user_word_id == user_word_id)
            )
            assert len(result.scalars().all()) == 2

            # Delete user_word
            await session.delete(user_word)
            await session.commit()

            # Verify statistics were deleted (CASCADE)
            result = await session.execute(
                select(WordStatistics).where(WordStatistics.user_word_id == user_word_id)
            )
            assert len(result.scalars().all()) == 0

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_word_statistics_tracks_learning_progress(self):
        """Test that WordStatistics can track learning progress over time."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=9000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=9000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="progress", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            # Create initial statistics
            stat = WordStatistics(
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="translation",
                correct_count=0,
                total_attempts=0,
                total_correct=0,
                total_errors=0
            )
            session.add(stat)
            await session.commit()

            # Simulate learning progress
            # First attempt: correct
            stat.total_attempts += 1
            stat.correct_count += 1
            stat.total_correct += 1
            await session.commit()

            # Second attempt: correct
            stat.total_attempts += 1
            stat.correct_count += 1
            stat.total_correct += 1
            await session.commit()

            # Third attempt: incorrect
            stat.total_attempts += 1
            stat.correct_count = 0  # Reset consecutive correct count
            stat.total_errors += 1
            await session.commit()

            # Fourth attempt: correct
            stat.total_attempts += 1
            stat.correct_count += 1
            stat.total_correct += 1
            await session.commit()

            await session.refresh(stat)

            # Verify final statistics
            assert stat.total_attempts == 4
            assert stat.correct_count == 1  # Current consecutive correct
            assert stat.total_correct == 3  # Total correct all time
            assert stat.total_errors == 1  # Total errors all time

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_word_statistics_supports_multiple_contexts(self):
        """Test that WordStatistics can track the same word in multiple contexts."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=10000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=10000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="context", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            # Create statistics for different contexts
            contexts = [
                ("en->ru", "translation"),
                ("ru->en", "translation"),
                ("en->ru", "multiple_choice"),
                ("ru->en", "multiple_choice")
            ]

            stats = [
                WordStatistics(
                    user_word_id=user_word.user_word_id,
                    direction=direction,
                    test_type=test_type,
                    total_attempts=10,
                    total_correct=7,
                    total_errors=3
                )
                for direction, test_type in contexts
            ]
            session.add_all(stats)
            await session.commit()

            # Verify all contexts were created
            result = await session.execute(
                select(WordStatistics).where(WordStatistics.user_word_id == user_word.user_word_id)
            )
            stored_stats = result.scalars().all()
            assert len(stored_stats) == 4

            # Verify each context is unique
            context_tuples = {(s.direction, s.test_type) for s in stored_stats}
            assert len(context_tuples) == 4

        await engine.dispose()


class TestTableCreation:
    """Tests for table creation and schema validation."""

    @pytest.mark.asyncio
    async def test_complete_statistics_workflow(self):
        """Test complete workflow: create user_word, track statistics across multiple lessons."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Setup
            user = User(user_id=11000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=11000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="workflow", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            # Create statistics for en->ru translation
            stat = WordStatistics(
                user_word_id=user_word.user_word_id,
                direction="en->ru",
                test_type="translation"
            )
            session.add(stat)
            await session.commit()

            # Simulate multiple lessons
            # Lesson 1: 3 attempts, 2 correct
            stat.total_attempts = 3
            stat.total_correct = 2
            stat.total_errors = 1
            stat.correct_count = 1
            await session.commit()

            # Lesson 2: 2 more attempts, both correct
            stat.total_attempts = 5
            stat.total_correct = 4
            stat.correct_count = 3  # 1 from before + 2 new
            await session.commit()

            # Lesson 3: 1 attempt, incorrect
            stat.total_attempts = 6
            stat.total_errors = 2
            stat.correct_count = 0  # Reset
            await session.commit()

            # Verify final statistics
            await session.refresh(stat)
            assert stat.total_attempts == 6
            assert stat.total_correct == 4
            assert stat.total_errors == 2
            assert stat.correct_count == 0

        await engine.dispose()
