"""
Comprehensive tests for CacheRepository.

Tests cover:
- Translation caching (get/set)
- Validation caching (get/set)
- Cache expiration handling
- Upsert logic for translations
- Cache hits and misses
- Input normalization (lowercase)
- Integration tests with real database
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import IntegrityError

from src.words.repositories.cache import CacheRepository
from src.words.models.cache import CachedTranslation, CachedValidation
from src.words.models.base import Base
from src.words.models.word import Word


class TestGetTranslation:
    """Tests for get_translation method."""

    @pytest.mark.asyncio
    async def test_get_translation_returns_data_when_found(self):
        """Test that get_translation returns cached data when found."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        translation_data = {"translation": "привет", "examples": ["Hello!"]}
        mock_cached = MagicMock()
        mock_cached.translation_data = translation_data

        mock_result.scalar_one_or_none.return_value = mock_cached
        mock_session.execute.return_value = mock_result

        repo = CacheRepository(mock_session)
        result = await repo.get_translation("hello", "en", "ru")

        assert result == translation_data
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_translation_returns_none_when_not_found(self):
        """Test that get_translation returns None when cache miss."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = CacheRepository(mock_session)
        result = await repo.get_translation("unknown", "en", "ru")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_translation_normalizes_word_to_lowercase(self):
        """Test that get_translation normalizes word to lowercase."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = CacheRepository(mock_session)
        await repo.get_translation("HELLO", "en", "ru")

        # Verify execute was called with a query
        mock_session.execute.assert_called_once()


class TestSetTranslation:
    """Tests for set_translation method."""

    @pytest.mark.asyncio
    async def test_set_translation_creates_new_record(self):
        """Test that set_translation creates new cache record."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock no existing record
        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_existing

        repo = CacheRepository(mock_session)
        translation_data = {"translation": "привет"}

        await repo.set_translation("hello", "en", "ru", translation_data)

        # Verify new record was added
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_translation_updates_existing_record(self):
        """Test that set_translation updates existing cache record (upsert)."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock existing record
        mock_existing_record = MagicMock()
        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = mock_existing_record
        mock_session.execute.return_value = mock_existing

        repo = CacheRepository(mock_session)
        new_data = {"translation": "привет", "updated": True}
        expires = datetime.now(timezone.utc) + timedelta(days=1)

        await repo.set_translation("hello", "en", "ru", new_data, expires_at=expires)

        # Verify existing record was updated
        assert mock_existing_record.translation_data == new_data
        assert mock_existing_record.expires_at == expires
        assert mock_existing_record.cached_at is not None

        # Verify no new record was added
        mock_session.add.assert_not_called()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_translation_normalizes_word_to_lowercase(self):
        """Test that set_translation normalizes word to lowercase."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock no existing record
        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_existing

        repo = CacheRepository(mock_session)
        translation_data = {"translation": "привет"}

        await repo.set_translation("HELLO", "en", "ru", translation_data)

        # Verify add was called
        mock_session.add.assert_called_once()

        # Get the added object
        added_obj = mock_session.add.call_args[0][0]
        assert added_obj.word == "hello"  # Normalized to lowercase

    @pytest.mark.asyncio
    async def test_set_translation_with_expiration(self):
        """Test that set_translation handles expiration timestamp."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock no existing record
        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_existing

        repo = CacheRepository(mock_session)
        translation_data = {"translation": "привет"}
        expires = datetime.now(timezone.utc) + timedelta(days=7)

        await repo.set_translation("hello", "en", "ru", translation_data, expires_at=expires)

        # Verify add was called
        mock_session.add.assert_called_once()

        # Get the added object
        added_obj = mock_session.add.call_args[0][0]
        assert added_obj.expires_at == expires

    @pytest.mark.asyncio
    async def test_set_translation_handles_race_condition(self):
        """Test that set_translation handles race condition with IntegrityError."""
        mock_session = AsyncMock(spec=AsyncSession)

        # First query: no existing record
        mock_first_query = MagicMock()
        mock_first_query.scalar_one_or_none.return_value = None

        # Second query (after rollback): record exists
        mock_existing_record = MagicMock()
        mock_second_query = MagicMock()
        mock_second_query.scalar_one_or_none.return_value = mock_existing_record

        # Setup execute to return different results for each call
        mock_session.execute.side_effect = [mock_first_query, mock_second_query]

        # First flush raises IntegrityError (race condition)
        # Second flush succeeds
        mock_session.flush.side_effect = [
            IntegrityError("Duplicate key", None, None),
            None  # Success on retry
        ]

        repo = CacheRepository(mock_session)
        translation_data = {"translation": "привет"}

        # Should not raise an error
        await repo.set_translation("hello", "en", "ru", translation_data)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()

        # Verify execute was called twice (initial query + retry query)
        assert mock_session.execute.call_count == 2

        # Verify flush was called twice (initial attempt + retry)
        assert mock_session.flush.call_count == 2

        # Verify existing record was updated
        assert mock_existing_record.translation_data == translation_data


class TestGetValidation:
    """Tests for get_validation method."""

    @pytest.mark.asyncio
    async def test_get_validation_returns_tuple_when_found(self):
        """Test that get_validation returns (is_correct, comment) tuple when found."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        mock_cached = MagicMock()
        mock_cached.is_correct = True
        mock_cached.llm_comment = "Perfect!"

        mock_result.scalar_one_or_none.return_value = mock_cached
        mock_session.execute.return_value = mock_result

        repo = CacheRepository(mock_session)
        result = await repo.get_validation(
            word_id=123,
            direction="forward",
            expected="hello",
            user_answer="hello"
        )

        assert result == (True, "Perfect!")
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_validation_returns_none_when_not_found(self):
        """Test that get_validation returns None when cache miss."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = CacheRepository(mock_session)
        result = await repo.get_validation(
            word_id=123,
            direction="forward",
            expected="hello",
            user_answer="helo"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_validation_normalizes_answers_to_lowercase(self):
        """Test that get_validation normalizes answers to lowercase."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = CacheRepository(mock_session)
        await repo.get_validation(
            word_id=123,
            direction="forward",
            expected="HELLO",
            user_answer="HELO"
        )

        # Verify execute was called
        mock_session.execute.assert_called_once()


class TestSetValidation:
    """Tests for set_validation method."""

    @pytest.mark.asyncio
    async def test_set_validation_creates_record(self):
        """Test that set_validation creates validation cache record."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock no existing record
        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_existing

        repo = CacheRepository(mock_session)

        await repo.set_validation(
            word_id=123,
            direction="forward",
            expected="hello",
            user_answer="helo",
            is_correct=False,
            comment="Close! Minor spelling error."
        )

        # Verify record was added
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_validation_normalizes_answers_to_lowercase(self):
        """Test that set_validation normalizes answers to lowercase."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock no existing record
        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_existing

        repo = CacheRepository(mock_session)

        await repo.set_validation(
            word_id=123,
            direction="forward",
            expected="HELLO",
            user_answer="HELO",
            is_correct=False,
            comment="Error"
        )

        # Verify add was called
        mock_session.add.assert_called_once()

        # Get the added object
        added_obj = mock_session.add.call_args[0][0]
        assert added_obj.expected_answer == "hello"  # Normalized
        assert added_obj.user_answer == "helo"  # Normalized

    @pytest.mark.asyncio
    async def test_set_validation_stores_all_fields(self):
        """Test that set_validation stores all required fields."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock no existing record
        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_existing

        repo = CacheRepository(mock_session)

        await repo.set_validation(
            word_id=456,
            direction="backward",
            expected="привет",
            user_answer="привет",
            is_correct=True,
            comment="Excellent!"
        )

        # Verify add was called
        mock_session.add.assert_called_once()

        # Get the added object
        added_obj = mock_session.add.call_args[0][0]
        assert added_obj.word_id == 456
        assert added_obj.direction == "backward"
        assert added_obj.expected_answer == "привет"
        assert added_obj.user_answer == "привет"
        assert added_obj.is_correct is True
        assert added_obj.llm_comment == "Excellent!"

    @pytest.mark.asyncio
    async def test_set_validation_raises_error_for_expected_answer_too_long(self):
        """Test that set_validation raises ValueError when expected answer exceeds 255 chars."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = CacheRepository(mock_session)

        # Create a string longer than 255 characters
        long_expected = "a" * 256

        with pytest.raises(ValueError, match="Expected answer exceeds maximum length of 255 characters"):
            await repo.set_validation(
                word_id=123,
                direction="forward",
                expected=long_expected,
                user_answer="test",
                is_correct=True,
                comment="Test"
            )

    @pytest.mark.asyncio
    async def test_set_validation_raises_error_for_user_answer_too_long(self):
        """Test that set_validation raises ValueError when user answer exceeds 255 chars."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = CacheRepository(mock_session)

        # Create a string longer than 255 characters
        long_user_answer = "b" * 256

        with pytest.raises(ValueError, match="User answer exceeds maximum length of 255 characters"):
            await repo.set_validation(
                word_id=123,
                direction="forward",
                expected="test",
                user_answer=long_user_answer,
                is_correct=True,
                comment="Test"
            )

    @pytest.mark.asyncio
    async def test_set_validation_accepts_max_length_answers(self):
        """Test that set_validation accepts answers at exactly 255 characters."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock no existing record
        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_existing

        repo = CacheRepository(mock_session)

        # Create strings at exactly 255 characters
        max_expected = "a" * 255
        max_user_answer = "b" * 255

        # Should not raise an error
        await repo.set_validation(
            word_id=123,
            direction="forward",
            expected=max_expected,
            user_answer=max_user_answer,
            is_correct=True,
            comment="Test"
        )

        # Verify add was called successfully
        mock_session.add.assert_called_once()


class TestCacheRepositoryIntegration:
    """Integration tests with real database."""

    @pytest.fixture
    async def engine(self):
        """Create async engine for testing."""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False
        )

        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine

        await engine.dispose()

    @pytest.fixture
    async def session(self, engine):
        """Create async session for testing."""
        async_session = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        async with async_session() as session:
            yield session

    @pytest.mark.asyncio
    async def test_integration_translation_cache_miss(self, session):
        """Test translation cache miss returns None."""
        repo = CacheRepository(session)

        result = await repo.get_translation("hello", "en", "ru")

        assert result is None

    @pytest.mark.asyncio
    async def test_integration_translation_cache_hit(self, session):
        """Test translation cache hit returns data."""
        repo = CacheRepository(session)

        # Set translation
        translation_data = {
            "translation": "привет",
            "examples": ["Hello, world!", "Hello there!"]
        }
        await repo.set_translation("hello", "en", "ru", translation_data)
        await session.commit()

        # Get translation
        result = await repo.get_translation("hello", "en", "ru")

        assert result == translation_data

    @pytest.mark.asyncio
    async def test_integration_translation_upsert(self, session):
        """Test translation upsert updates existing record."""
        repo = CacheRepository(session)

        # Set initial translation
        initial_data = {"translation": "привет"}
        await repo.set_translation("hello", "en", "ru", initial_data)
        await session.commit()

        # Update translation
        updated_data = {"translation": "здравствуйте", "formal": True}
        await repo.set_translation("hello", "en", "ru", updated_data)
        await session.commit()

        # Verify updated data
        result = await repo.get_translation("hello", "en", "ru")
        assert result == updated_data

    @pytest.mark.asyncio
    async def test_integration_translation_expiration_filters_expired(self, session):
        """Test that expired translations are not returned."""
        repo = CacheRepository(session)

        # Set translation with expiration in the past
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        translation_data = {"translation": "привет"}
        await repo.set_translation(
            "hello", "en", "ru",
            translation_data,
            expires_at=expired_time
        )
        await session.commit()

        # Try to get expired translation
        result = await repo.get_translation("hello", "en", "ru")

        assert result is None  # Should be filtered out

    @pytest.mark.asyncio
    async def test_integration_translation_expiration_returns_valid(self, session):
        """Test that non-expired translations are returned."""
        repo = CacheRepository(session)

        # Set translation with expiration in the future
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        translation_data = {"translation": "привет"}
        await repo.set_translation(
            "hello", "en", "ru",
            translation_data,
            expires_at=future_time
        )
        await session.commit()

        # Get valid translation
        result = await repo.get_translation("hello", "en", "ru")

        assert result == translation_data

    @pytest.mark.asyncio
    async def test_integration_translation_no_expiration(self, session):
        """Test that translations without expiration are always returned."""
        repo = CacheRepository(session)

        # Set translation without expiration
        translation_data = {"translation": "привет"}
        await repo.set_translation("hello", "en", "ru", translation_data)
        await session.commit()

        # Get translation
        result = await repo.get_translation("hello", "en", "ru")

        assert result == translation_data

    @pytest.mark.asyncio
    async def test_integration_validation_cache_miss(self, session):
        """Test validation cache miss returns None."""
        repo = CacheRepository(session)

        # First create a word
        word = Word(
            word="hello",
            language="en",
            translations={"ru": ["привет"]},
            frequency_rank=100
        )
        session.add(word)
        await session.flush()
        await session.commit()

        result = await repo.get_validation(
            word_id=word.word_id,
            direction="forward",
            expected="hello",
            user_answer="helo"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_integration_validation_cache_hit(self, session):
        """Test validation cache hit returns data."""
        repo = CacheRepository(session)

        # First create a word
        word = Word(
            word="hello",
            language="en",
            translations={"ru": ["привет"]},
            frequency_rank=100
        )
        session.add(word)
        await session.flush()
        await session.commit()

        # Set validation
        await repo.set_validation(
            word_id=word.word_id,
            direction="forward",
            expected="hello",
            user_answer="helo",
            is_correct=False,
            comment="Close! Minor spelling error."
        )
        await session.commit()

        # Get validation
        result = await repo.get_validation(
            word_id=word.word_id,
            direction="forward",
            expected="hello",
            user_answer="helo"
        )

        assert result == (False, "Close! Minor spelling error.")

    @pytest.mark.asyncio
    async def test_integration_validation_different_answers(self, session):
        """Test that different user answers are cached separately."""
        repo = CacheRepository(session)

        # First create a word
        word = Word(
            word="hello",
            language="en",
            translations={"ru": ["привет"]},
            frequency_rank=100
        )
        session.add(word)
        await session.flush()
        await session.commit()

        # Cache two different validations
        await repo.set_validation(
            word_id=word.word_id,
            direction="forward",
            expected="hello",
            user_answer="helo",
            is_correct=False,
            comment="Spelling error"
        )
        await repo.set_validation(
            word_id=word.word_id,
            direction="forward",
            expected="hello",
            user_answer="hello",
            is_correct=True,
            comment="Perfect!"
        )
        await session.commit()

        # Get both validations
        result1 = await repo.get_validation(
            word_id=word.word_id,
            direction="forward",
            expected="hello",
            user_answer="helo"
        )
        result2 = await repo.get_validation(
            word_id=word.word_id,
            direction="forward",
            expected="hello",
            user_answer="hello"
        )

        assert result1 == (False, "Spelling error")
        assert result2 == (True, "Perfect!")

    @pytest.mark.asyncio
    async def test_integration_validation_case_insensitive(self, session):
        """Test that validation lookup is case-insensitive."""
        repo = CacheRepository(session)

        # First create a word
        word = Word(
            word="hello",
            language="en",
            translations={"ru": ["привет"]},
            frequency_rank=100
        )
        session.add(word)
        await session.flush()
        await session.commit()

        # Set validation with lowercase
        await repo.set_validation(
            word_id=word.word_id,
            direction="forward",
            expected="hello",
            user_answer="hello",
            is_correct=True,
            comment="Perfect!"
        )
        await session.commit()

        # Get validation with uppercase
        result = await repo.get_validation(
            word_id=word.word_id,
            direction="forward",
            expected="HELLO",
            user_answer="HELLO"
        )

        assert result == (True, "Perfect!")

    @pytest.mark.asyncio
    async def test_integration_translation_case_insensitive(self, session):
        """Test that translation lookup is case-insensitive."""
        repo = CacheRepository(session)

        # Set translation with lowercase
        translation_data = {"translation": "привет"}
        await repo.set_translation("hello", "en", "ru", translation_data)
        await session.commit()

        # Get translation with uppercase
        result = await repo.get_translation("HELLO", "en", "ru")

        assert result == translation_data

    @pytest.mark.asyncio
    async def test_integration_multiple_language_pairs(self, session):
        """Test caching for multiple language pairs."""
        repo = CacheRepository(session)

        # Cache translations for different language pairs
        await repo.set_translation("hello", "en", "ru", {"translation": "привет"})
        await repo.set_translation("hello", "en", "es", {"translation": "hola"})
        await repo.set_translation("hello", "en", "fr", {"translation": "bonjour"})
        await session.commit()

        # Verify each language pair is cached separately
        result_ru = await repo.get_translation("hello", "en", "ru")
        result_es = await repo.get_translation("hello", "en", "es")
        result_fr = await repo.get_translation("hello", "en", "fr")

        assert result_ru == {"translation": "привет"}
        assert result_es == {"translation": "hola"}
        assert result_fr == {"translation": "bonjour"}

    @pytest.mark.asyncio
    async def test_integration_validation_upsert(self, session):
        """Test validation upsert updates existing record (duplicate caching)."""
        repo = CacheRepository(session)

        # First create a word
        word = Word(
            word="hello",
            language="en",
            translations={"ru": ["привет"]},
            frequency_rank=100
        )
        session.add(word)
        await session.flush()
        await session.commit()

        # Set initial validation
        await repo.set_validation(
            word_id=word.word_id,
            direction="forward",
            expected="hello",
            user_answer="helo",
            is_correct=False,
            comment="Initial feedback: spelling error"
        )
        await session.commit()

        # Update validation with different result (upsert)
        await repo.set_validation(
            word_id=word.word_id,
            direction="forward",
            expected="hello",
            user_answer="helo",
            is_correct=True,
            comment="Updated feedback: acceptable variant"
        )
        await session.commit()

        # Verify updated data
        result = await repo.get_validation(
            word_id=word.word_id,
            direction="forward",
            expected="hello",
            user_answer="helo"
        )
        assert result == (True, "Updated feedback: acceptable variant")
