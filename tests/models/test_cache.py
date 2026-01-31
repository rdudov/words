"""
Tests for Cache ORM models (CachedTranslation and CachedValidation).

This module tests the cache models, including:
- CachedTranslation model creation and fields
- CachedValidation model creation and fields
- JSON field in CachedTranslation
- Text field in CachedValidation (llm_comment)
- UNIQUE constraints on both models
- Timezone-aware datetime fields
- expires_at can be set for TTL
- Foreign key relationship to Word model
- Indexes
- Table creation
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, inspect, text as sa_text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.words.models import Base, CachedTranslation, CachedValidation, Word


class TestCachedTranslationModel:
    """Tests for the CachedTranslation model."""

    @pytest.mark.asyncio
    async def test_create_cached_translation_with_minimum_fields(self):
        """Test creating a CachedTranslation with only required fields."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            cached_translation = CachedTranslation(
                word="house",
                source_language="en",
                target_language="ru",
                translation_data={"translations": ["дом", "здание"]}
            )
            session.add(cached_translation)
            await session.commit()
            await session.refresh(cached_translation)

            # Verify fields
            assert cached_translation.cache_id is not None
            assert cached_translation.word == "house"
            assert cached_translation.source_language == "en"
            assert cached_translation.target_language == "ru"
            assert cached_translation.translation_data == {"translations": ["дом", "здание"]}
            assert cached_translation.cached_at is not None
            assert cached_translation.cached_at.tzinfo is not None
            assert cached_translation.expires_at is None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_create_cached_translation_with_all_fields(self):
        """Test creating a CachedTranslation with all fields including expires_at."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=30)

        async with async_session() as session:
            cached_translation = CachedTranslation(
                word="cat",
                source_language="en",
                target_language="es",
                translation_data={
                    "translations": ["gato"],
                    "examples": ["The cat is sleeping"],
                    "pronunciation": "gato"
                },
                cached_at=now,
                expires_at=expires
            )
            session.add(cached_translation)
            await session.commit()
            await session.refresh(cached_translation)

            # Verify all fields
            assert cached_translation.cache_id is not None
            assert cached_translation.word == "cat"
            assert cached_translation.source_language == "en"
            assert cached_translation.target_language == "es"
            assert cached_translation.translation_data["translations"] == ["gato"]
            assert "examples" in cached_translation.translation_data
            assert cached_translation.cached_at.tzinfo is not None
            assert cached_translation.expires_at is not None
            assert cached_translation.expires_at.tzinfo is not None
            assert cached_translation.expires_at > cached_translation.cached_at

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cached_translation_json_field_works_correctly(self):
        """Test that JSON field (translation_data) works correctly."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Test complex JSON structure
            complex_data = {
                "translations": ["собака", "пёс"],
                "part_of_speech": "noun",
                "gender": "feminine",
                "examples": [
                    {"en": "The dog is barking", "ru": "Собака лает"},
                    {"en": "I have a dog", "ru": "У меня есть собака"}
                ],
                "synonyms": ["hound", "canine"],
                "frequency": 1500
            }

            cached_translation = CachedTranslation(
                word="dog",
                source_language="en",
                target_language="ru",
                translation_data=complex_data
            )
            session.add(cached_translation)
            await session.commit()
            await session.refresh(cached_translation)

            # Verify JSON data integrity
            assert isinstance(cached_translation.translation_data, dict)
            assert len(cached_translation.translation_data["translations"]) == 2
            assert "собака" in cached_translation.translation_data["translations"]
            assert cached_translation.translation_data["part_of_speech"] == "noun"
            assert len(cached_translation.translation_data["examples"]) == 2
            assert cached_translation.translation_data["frequency"] == 1500

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cached_translation_datetime_fields_are_timezone_aware(self):
        """Test that datetime fields are timezone-aware."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Test with naive datetimes (should be converted to UTC)
        naive_cached = datetime(2025, 1, 1, 10, 0, 0)
        naive_expires = datetime(2025, 2, 1, 10, 0, 0)

        async with async_session() as session:
            cached_translation = CachedTranslation(
                word="time",
                source_language="en",
                target_language="ru",
                translation_data={"translations": ["время"]},
                cached_at=naive_cached,
                expires_at=naive_expires
            )
            session.add(cached_translation)
            await session.commit()
            await session.refresh(cached_translation)

            # Verify all datetime fields are timezone-aware
            assert cached_translation.cached_at.tzinfo is not None
            assert cached_translation.cached_at.tzinfo == timezone.utc
            assert cached_translation.expires_at.tzinfo is not None
            assert cached_translation.expires_at.tzinfo == timezone.utc

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cached_translation_unique_constraint_prevents_duplicates(self):
        """Test that UNIQUE constraint on (word, source_language, target_language) prevents duplicates."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create first cached translation
            cached1 = CachedTranslation(
                word="hello",
                source_language="en",
                target_language="ru",
                translation_data={"translations": ["привет"]}
            )
            session.add(cached1)
            await session.commit()

            # Try to create duplicate with same word, source, and target languages
            cached2 = CachedTranslation(
                word="hello",
                source_language="en",
                target_language="ru",
                translation_data={"translations": ["здравствуй"]}  # Different data doesn't matter
            )
            session.add(cached2)

            # Should raise IntegrityError due to UNIQUE constraint
            with pytest.raises(IntegrityError):
                await session.commit()

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cached_translation_unique_constraint_allows_different_language_pairs(self):
        """Test that same word with different language pairs is allowed."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create translations for same word but different language pairs
            cached_en_ru = CachedTranslation(
                word="test",
                source_language="en",
                target_language="ru",
                translation_data={"translations": ["тест"]}
            )
            cached_en_es = CachedTranslation(
                word="test",
                source_language="en",
                target_language="es",
                translation_data={"translations": ["prueba"]}
            )
            cached_ru_en = CachedTranslation(
                word="test",
                source_language="ru",
                target_language="en",
                translation_data={"translations": ["test"]}
            )
            session.add_all([cached_en_ru, cached_en_es, cached_ru_en])
            await session.commit()

            # Verify all were created
            result = await session.execute(
                select(CachedTranslation).where(CachedTranslation.word == "test")
            )
            cached_translations = result.scalars().all()
            assert len(cached_translations) == 3

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cached_translation_expires_at_for_ttl(self):
        """Test that expires_at can be set for TTL (Time To Live) functionality."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        now = datetime.now(timezone.utc)

        async with async_session() as session:
            # Create translation with 7-day TTL
            cached_7days = CachedTranslation(
                word="expire_test",
                source_language="en",
                target_language="ru",
                translation_data={"translations": ["тест"]},
                expires_at=now + timedelta(days=7)
            )

            # Create translation with no expiration
            cached_forever = CachedTranslation(
                word="forever",
                source_language="en",
                target_language="ru",
                translation_data={"translations": ["вечно"]},
                expires_at=None
            )

            session.add_all([cached_7days, cached_forever])
            await session.commit()

            # Query unexpired translations (as if checking before expiration)
            result = await session.execute(
                select(CachedTranslation).where(
                    (CachedTranslation.expires_at.is_(None)) |
                    (CachedTranslation.expires_at > now)
                )
            )
            unexpired = result.scalars().all()
            assert len(unexpired) == 2

            # Query expired translations (as if checking after 8 days)
            future_time = now + timedelta(days=8)
            result = await session.execute(
                select(CachedTranslation).where(
                    CachedTranslation.expires_at.isnot(None),
                    CachedTranslation.expires_at < future_time
                )
            )
            expired = result.scalars().all()
            assert len(expired) == 1
            assert expired[0].word == "expire_test"

        await engine.dispose()


class TestCachedValidationModel:
    """Tests for the CachedValidation model."""

    @pytest.mark.asyncio
    async def test_create_cached_validation_with_minimum_fields(self):
        """Test creating a CachedValidation with only required fields."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create prerequisite word
            word = Word(word="house", language="en")
            session.add(word)
            await session.commit()

            # Create cached validation
            cached_validation = CachedValidation(
                word_id=word.word_id,
                direction="forward",
                expected_answer="дом",
                user_answer="дом",
                is_correct=True
            )
            session.add(cached_validation)
            await session.commit()
            await session.refresh(cached_validation)

            # Verify fields
            assert cached_validation.validation_id is not None
            assert cached_validation.word_id == word.word_id
            assert cached_validation.direction == "forward"
            assert cached_validation.expected_answer == "дом"
            assert cached_validation.user_answer == "дом"
            assert cached_validation.is_correct is True
            assert cached_validation.llm_comment is None
            assert cached_validation.cached_at is not None
            assert cached_validation.cached_at.tzinfo is not None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_create_cached_validation_with_all_fields(self):
        """Test creating a CachedValidation with all fields including llm_comment."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        now = datetime.now(timezone.utc)

        async with async_session() as session:
            # Create prerequisite word
            word = Word(word="cat", language="en")
            session.add(word)
            await session.commit()

            # Create cached validation with LLM comment
            cached_validation = CachedValidation(
                word_id=word.word_id,
                direction="backward",
                expected_answer="cat",
                user_answer="kat",
                is_correct=False,
                llm_comment="Your answer 'kat' is phonetically similar to 'cat', but it's spelled incorrectly. The correct spelling is 'cat' with a 'c', not 'k'.",
                cached_at=now
            )
            session.add(cached_validation)
            await session.commit()
            await session.refresh(cached_validation)

            # Verify all fields
            assert cached_validation.validation_id is not None
            assert cached_validation.word_id == word.word_id
            assert cached_validation.direction == "backward"
            assert cached_validation.expected_answer == "cat"
            assert cached_validation.user_answer == "kat"
            assert cached_validation.is_correct is False
            assert cached_validation.llm_comment is not None
            assert "phonetically similar" in cached_validation.llm_comment
            assert cached_validation.cached_at.tzinfo is not None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cached_validation_text_field_handles_long_comments(self):
        """Test that Text field (llm_comment) can handle long text."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create prerequisite word
            word = Word(word="complex", language="en")
            session.add(word)
            await session.commit()

            # Create a very long LLM comment (simulating detailed feedback)
            long_comment = """
            Your answer 'сложный' is partially correct, but 'комплексный' would be more accurate in this context.
            Let me explain the difference:

            1. 'сложный' (slozhnyy) means 'complex' in the sense of 'complicated' or 'difficult'.
               Example: "Это сложная задача" (This is a complex/difficult task)

            2. 'комплексный' (kompleksnyy) means 'complex' in the sense of 'comprehensive' or 'composite'.
               Example: "Комплексный подход" (A complex/comprehensive approach)

            In mathematical or technical contexts, 'комплексный' is often preferred.
            For example, "complex number" is "комплексное число" in Russian.

            Your answer shows good understanding, but pay attention to the specific context
            to choose between these synonyms correctly.
            """ * 3  # Make it even longer

            cached_validation = CachedValidation(
                word_id=word.word_id,
                direction="forward",
                expected_answer="комплексный",
                user_answer="сложный",
                is_correct=False,
                llm_comment=long_comment
            )
            session.add(cached_validation)
            await session.commit()
            await session.refresh(cached_validation)

            # Verify long text was stored correctly
            assert cached_validation.llm_comment is not None
            assert len(cached_validation.llm_comment) > 500
            assert "сложный" in cached_validation.llm_comment
            assert "комплексный" in cached_validation.llm_comment

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cached_validation_datetime_fields_are_timezone_aware(self):
        """Test that datetime fields are timezone-aware."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Test with naive datetime (should be converted to UTC)
        naive_cached = datetime(2025, 1, 15, 14, 30, 0)

        async with async_session() as session:
            word = Word(word="timezone", language="en")
            session.add(word)
            await session.commit()

            cached_validation = CachedValidation(
                word_id=word.word_id,
                direction="forward",
                expected_answer="временная зона",
                user_answer="временная зона",
                is_correct=True,
                cached_at=naive_cached
            )
            session.add(cached_validation)
            await session.commit()
            await session.refresh(cached_validation)

            # Verify datetime field is timezone-aware
            assert cached_validation.cached_at.tzinfo is not None
            assert cached_validation.cached_at.tzinfo == timezone.utc

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cached_validation_unique_constraint_prevents_duplicates(self):
        """Test that UNIQUE constraint on (word_id, direction, expected_answer, user_answer) prevents duplicates."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            word = Word(word="unique", language="en")
            session.add(word)
            await session.commit()

            # Create first cached validation
            cached1 = CachedValidation(
                word_id=word.word_id,
                direction="forward",
                expected_answer="уникальный",
                user_answer="уникальный",
                is_correct=True
            )
            session.add(cached1)
            await session.commit()

            # Try to create duplicate with same word_id, direction, expected_answer, user_answer
            cached2 = CachedValidation(
                word_id=word.word_id,
                direction="forward",
                expected_answer="уникальный",
                user_answer="уникальный",
                is_correct=True,  # Same correctness doesn't matter
                llm_comment="Different comment"  # Different comment doesn't matter
            )
            session.add(cached2)

            # Should raise IntegrityError due to UNIQUE constraint
            with pytest.raises(IntegrityError):
                await session.commit()

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cached_validation_unique_constraint_allows_different_user_answers(self):
        """Test that same word with different user answers is allowed."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            word = Word(word="dog", language="en")
            session.add(word)
            await session.commit()

            # Create validations for same word but different user answers
            cached_correct = CachedValidation(
                word_id=word.word_id,
                direction="forward",
                expected_answer="собака",
                user_answer="собака",
                is_correct=True
            )
            cached_typo = CachedValidation(
                word_id=word.word_id,
                direction="forward",
                expected_answer="собака",
                user_answer="сабака",  # Typo
                is_correct=False
            )
            cached_wrong = CachedValidation(
                word_id=word.word_id,
                direction="forward",
                expected_answer="собака",
                user_answer="кот",  # Completely wrong
                is_correct=False
            )
            session.add_all([cached_correct, cached_typo, cached_wrong])
            await session.commit()

            # Verify all were created
            result = await session.execute(
                select(CachedValidation).where(CachedValidation.word_id == word.word_id)
            )
            cached_validations = result.scalars().all()
            assert len(cached_validations) == 3

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cached_validation_unique_constraint_allows_different_directions(self):
        """Test that same word with different directions is allowed."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            word = Word(word="book", language="en")
            session.add(word)
            await session.commit()

            # Create validations for same word but different directions
            cached_forward = CachedValidation(
                word_id=word.word_id,
                direction="forward",
                expected_answer="книга",
                user_answer="книга",
                is_correct=True
            )
            cached_backward = CachedValidation(
                word_id=word.word_id,
                direction="backward",
                expected_answer="book",
                user_answer="book",
                is_correct=True
            )
            session.add_all([cached_forward, cached_backward])
            await session.commit()

            # Verify both were created
            result = await session.execute(
                select(CachedValidation).where(CachedValidation.word_id == word.word_id)
            )
            cached_validations = result.scalars().all()
            assert len(cached_validations) == 2

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cached_validation_foreign_key_relationship_to_word(self):
        """Test CachedValidation foreign key relationship to Word."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            word = Word(word="relationship", language="en", translations={"ru": ["отношение"]})
            session.add(word)
            await session.commit()

            cached_validation = CachedValidation(
                word_id=word.word_id,
                direction="forward",
                expected_answer="отношение",
                user_answer="отношение",
                is_correct=True
            )
            session.add(cached_validation)
            await session.commit()

            validation_id = cached_validation.validation_id

        # Query and load relationship
        async with async_session() as session:
            result = await session.execute(
                select(CachedValidation).where(CachedValidation.validation_id == validation_id)
            )
            cached_validation = result.scalar_one()

            # Load word relationship
            result = await session.execute(
                select(Word).where(Word.word_id == cached_validation.word_id)
            )
            word = result.scalar_one()

            assert word is not None
            assert word.word == "relationship"
            assert word.translations == {"ru": ["отношение"]}

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cascade_delete_word_removes_cached_validations(self):
        """Test that deleting a Word cascades to delete related CachedValidations."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.execute(sa_text("PRAGMA foreign_keys=ON"))
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            await session.execute(sa_text("PRAGMA foreign_keys=ON"))

            word = Word(word="cascade", language="en")
            session.add(word)
            await session.commit()

            # Create multiple cached validations
            cached1 = CachedValidation(
                word_id=word.word_id,
                direction="forward",
                expected_answer="каскад",
                user_answer="каскад",
                is_correct=True
            )
            cached2 = CachedValidation(
                word_id=word.word_id,
                direction="backward",
                expected_answer="cascade",
                user_answer="cascade",
                is_correct=True
            )
            session.add_all([cached1, cached2])
            await session.commit()

            word_id = word.word_id

            # Verify cached validations exist
            result = await session.execute(
                select(CachedValidation).where(CachedValidation.word_id == word_id)
            )
            assert len(result.scalars().all()) == 2

            # Delete word
            await session.delete(word)
            await session.commit()

            # Verify cached validations were deleted (CASCADE)
            result = await session.execute(
                select(CachedValidation).where(CachedValidation.word_id == word_id)
            )
            assert len(result.scalars().all()) == 0

        await engine.dispose()

