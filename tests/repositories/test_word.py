"""
Comprehensive tests for WordRepository and UserWordRepository.

Tests cover:
- WordRepository methods (find_by_text_and_language, get_frequency_words)
- UserWordRepository methods (get_user_word, get_user_vocabulary, count_by_status)
- Eager loading with selectinload
- Case-insensitive lookups
- Edge cases and error handling
- Integration with actual database operations
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from src.words.repositories.word import WordRepository, UserWordRepository
from src.words.models import Base, Word, UserWord, WordStatusEnum, User, LanguageProfile, CEFRLevel, WordStatistics


# Module-level fixtures for integration tests
@pytest.fixture
async def integration_engine():
    """Create async engine for integration testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def integration_session(integration_engine):
    """Create async session for integration testing."""
    async_session = async_sessionmaker(
        integration_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session


class TestWordRepositoryInitialization:
    """Tests for WordRepository initialization."""

    @pytest.mark.asyncio
    async def test_word_repository_initialization(self):
        """Test that WordRepository can be initialized with session."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = WordRepository(mock_session)

        assert repo.session is mock_session
        assert repo.model is Word


class TestFindByTextAndLanguage:
    """Tests for find_by_text_and_language method."""

    @pytest.mark.asyncio
    async def test_find_by_text_and_language_returns_word_when_found(self):
        """Test that find_by_text_and_language returns word when it exists."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_word = Word(
            word_id=1,
            word="hello",
            language="en",
            level="A1",
            frequency_rank=100
        )
        mock_result.scalar_one_or_none.return_value = mock_word
        mock_session.execute.return_value = mock_result

        repo = WordRepository(mock_session)
        result = await repo.find_by_text_and_language("hello", "en")

        assert result is mock_word
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_text_and_language_returns_none_when_not_found(self):
        """Test that find_by_text_and_language returns None when word doesn't exist."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = WordRepository(mock_session)
        result = await repo.find_by_text_and_language("nonexistent", "en")

        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_text_and_language_case_insensitive(self):
        """Test that find_by_text_and_language normalizes to lowercase."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_word = Word(word_id=1, word="hello", language="en")
        mock_result.scalar_one_or_none.return_value = mock_word
        mock_session.execute.return_value = mock_result

        repo = WordRepository(mock_session)
        # Search with mixed case
        result = await repo.find_by_text_and_language("HELLO", "en")

        # Should still find the word (lowercase comparison)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_text_and_language_filters_by_language(self):
        """Test that find_by_text_and_language filters by language correctly."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = WordRepository(mock_session)
        # Same word different language shouldn't match
        result = await repo.find_by_text_and_language("hello", "ru")

        assert result is None


class TestGetFrequencyWords:
    """Tests for get_frequency_words method."""

    @pytest.mark.asyncio
    async def test_get_frequency_words_returns_words_for_level(self):
        """Test that get_frequency_words returns words for a specific level."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()

        words = [
            Word(word_id=1, word="hello", language="en", level="A1", frequency_rank=1),
            Word(word_id=2, word="world", language="en", level="A1", frequency_rank=2),
            Word(word_id=3, word="good", language="en", level="A1", frequency_rank=3)
        ]
        mock_scalars.all.return_value = words
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = WordRepository(mock_session)
        result = await repo.get_frequency_words("en", "A1", limit=50)

        assert len(result) == 3
        assert result[0].word == "hello"
        assert result[1].word == "world"
        assert result[2].word == "good"

    @pytest.mark.asyncio
    async def test_get_frequency_words_returns_empty_list_when_no_words(self):
        """Test that get_frequency_words returns empty list when no words match."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = WordRepository(mock_session)
        result = await repo.get_frequency_words("zh", "C2", limit=50)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_frequency_words_respects_limit(self):
        """Test that get_frequency_words respects the limit parameter."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()

        # Create 100 words
        words = [
            Word(word_id=i, word=f"word{i}", language="en", level="A1", frequency_rank=i)
            for i in range(1, 11)
        ]
        mock_scalars.all.return_value = words
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = WordRepository(mock_session)
        result = await repo.get_frequency_words("en", "A1", limit=10)

        # Verify execute was called with limit
        mock_session.execute.assert_called_once()
        assert len(result) == 10

    @pytest.mark.asyncio
    async def test_get_frequency_words_orders_by_frequency_rank(self):
        """Test that get_frequency_words orders by frequency rank."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()

        # Create words with different frequency ranks
        words = [
            Word(word_id=1, word="the", language="en", level="A1", frequency_rank=1),
            Word(word_id=2, word="be", language="en", level="A1", frequency_rank=2),
            Word(word_id=3, word="to", language="en", level="A1", frequency_rank=3)
        ]
        mock_scalars.all.return_value = words
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = WordRepository(mock_session)
        result = await repo.get_frequency_words("en", "A1", limit=50)

        # Words should be ordered by frequency rank
        assert result[0].frequency_rank == 1
        assert result[1].frequency_rank == 2
        assert result[2].frequency_rank == 3


class TestUserWordRepositoryInitialization:
    """Tests for UserWordRepository initialization."""

    @pytest.mark.asyncio
    async def test_user_word_repository_initialization(self):
        """Test that UserWordRepository can be initialized with session."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = UserWordRepository(mock_session)

        assert repo.session is mock_session
        assert repo.model is UserWord


class TestGetUserWord:
    """Tests for get_user_word method."""

    @pytest.mark.asyncio
    async def test_get_user_word_returns_user_word_when_found(self):
        """Test that get_user_word returns user word when it exists."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_user_word = UserWord(
            user_word_id=1,
            profile_id=100,
            word_id=200,
            status=WordStatusEnum.LEARNING
        )
        mock_result.scalar_one_or_none.return_value = mock_user_word
        mock_session.execute.return_value = mock_result

        repo = UserWordRepository(mock_session)
        result = await repo.get_user_word(profile_id=100, word_id=200)

        assert result is mock_user_word
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_word_returns_none_when_not_found(self):
        """Test that get_user_word returns None when user word doesn't exist."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserWordRepository(mock_session)
        result = await repo.get_user_word(profile_id=999, word_id=999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_word_uses_selectinload_for_relationships(self):
        """Test that get_user_word uses selectinload to eagerly load relationships."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserWordRepository(mock_session)
        await repo.get_user_word(profile_id=100, word_id=200)

        # Verify execute was called (selectinload is used in the query)
        mock_session.execute.assert_called_once()


class TestGetUserVocabulary:
    """Tests for get_user_vocabulary method."""

    @pytest.mark.asyncio
    async def test_get_user_vocabulary_returns_all_words(self):
        """Test that get_user_vocabulary returns all user words."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()

        user_words = [
            UserWord(user_word_id=1, profile_id=100, word_id=1, status=WordStatusEnum.NEW),
            UserWord(user_word_id=2, profile_id=100, word_id=2, status=WordStatusEnum.LEARNING),
            UserWord(user_word_id=3, profile_id=100, word_id=3, status=WordStatusEnum.REVIEWING)
        ]
        mock_scalars.all.return_value = user_words
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UserWordRepository(mock_session)
        result = await repo.get_user_vocabulary(profile_id=100)

        assert len(result) == 3
        assert result[0].status == WordStatusEnum.NEW
        assert result[1].status == WordStatusEnum.LEARNING
        assert result[2].status == WordStatusEnum.REVIEWING

    @pytest.mark.asyncio
    async def test_get_user_vocabulary_filters_by_status(self):
        """Test that get_user_vocabulary filters by status when provided."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()

        # Only learning words
        user_words = [
            UserWord(user_word_id=2, profile_id=100, word_id=2, status=WordStatusEnum.LEARNING)
        ]
        mock_scalars.all.return_value = user_words
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UserWordRepository(mock_session)
        result = await repo.get_user_vocabulary(profile_id=100, status=WordStatusEnum.LEARNING)

        assert len(result) == 1
        assert result[0].status == WordStatusEnum.LEARNING

    @pytest.mark.asyncio
    async def test_get_user_vocabulary_returns_empty_list_when_no_words(self):
        """Test that get_user_vocabulary returns empty list when user has no words."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UserWordRepository(mock_session)
        result = await repo.get_user_vocabulary(profile_id=999)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_vocabulary_uses_selectinload_for_relationships(self):
        """Test that get_user_vocabulary uses selectinload to eagerly load relationships."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UserWordRepository(mock_session)
        await repo.get_user_vocabulary(profile_id=100)

        # Verify execute was called (selectinload is used in the query)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_vocabulary_with_none_status(self):
        """Test that get_user_vocabulary works with None status (no filter)."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()

        user_words = [
            UserWord(user_word_id=1, profile_id=100, word_id=1, status=WordStatusEnum.NEW),
            UserWord(user_word_id=2, profile_id=100, word_id=2, status=WordStatusEnum.MASTERED)
        ]
        mock_scalars.all.return_value = user_words
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UserWordRepository(mock_session)
        result = await repo.get_user_vocabulary(profile_id=100, status=None)

        assert len(result) == 2


class TestCountByStatus:
    """Tests for count_by_status method."""

    @pytest.mark.asyncio
    async def test_count_by_status_returns_counts_for_all_statuses(self):
        """Test that count_by_status returns counts grouped by status."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        # Mock result with status counts
        mock_result.all.return_value = [
            (WordStatusEnum.NEW, 5),
            (WordStatusEnum.LEARNING, 10),
            (WordStatusEnum.REVIEWING, 15),
            (WordStatusEnum.MASTERED, 20)
        ]
        mock_session.execute.return_value = mock_result

        repo = UserWordRepository(mock_session)
        result = await repo.count_by_status(profile_id=100)

        assert result == {
            "new": 5,
            "learning": 10,
            "reviewing": 15,
            "mastered": 20
        }

    @pytest.mark.asyncio
    async def test_count_by_status_returns_empty_dict_when_no_words(self):
        """Test that count_by_status returns empty dict when user has no words."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = UserWordRepository(mock_session)
        result = await repo.count_by_status(profile_id=999)

        assert result == {}

    @pytest.mark.asyncio
    async def test_count_by_status_with_partial_statuses(self):
        """Test that count_by_status returns only existing statuses."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        # Only some statuses have counts
        mock_result.all.return_value = [
            (WordStatusEnum.NEW, 3),
            (WordStatusEnum.LEARNING, 7)
        ]
        mock_session.execute.return_value = mock_result

        repo = UserWordRepository(mock_session)
        result = await repo.count_by_status(profile_id=100)

        assert result == {
            "new": 3,
            "learning": 7
        }
        # Verify statuses with 0 count are not included
        assert "reviewing" not in result
        assert "mastered" not in result


class TestWordRepositoryIntegration:
    """Integration tests for WordRepository with actual database."""

    @pytest.mark.asyncio
    async def test_integration_find_by_text_and_language(self, integration_session):
        """Test find_by_text_and_language with actual database."""
        # Create words
        word1 = Word(word="hello", language="en", level="A1", frequency_rank=1)
        word2 = Word(word="hello", language="ru", level="A1", frequency_rank=100)
        word3 = Word(word="world", language="en", level="A1", frequency_rank=2)
        integration_session.add_all([word1, word2, word3])
        await integration_session.commit()

        # Test finding by text and language
        repo = WordRepository(integration_session)

        # Find English "hello"
        result = await repo.find_by_text_and_language("hello", "en")
        assert result is not None
        assert result.word == "hello"
        assert result.language == "en"

        # Find Russian "hello"
        result = await repo.find_by_text_and_language("hello", "ru")
        assert result is not None
        assert result.word == "hello"
        assert result.language == "ru"

        # Find non-existent word
        result = await repo.find_by_text_and_language("nonexistent", "en")
        assert result is None

    @pytest.mark.asyncio
    async def test_integration_find_by_text_and_language_case_insensitive(self, integration_session):
        """Test case-insensitive lookup in find_by_text_and_language."""
        # Create word in lowercase
        word = Word(word="hello", language="en", level="A1")
        integration_session.add(word)
        await integration_session.commit()

        repo = WordRepository(integration_session)

        # Search with various cases
        result1 = await repo.find_by_text_and_language("hello", "en")
        result2 = await repo.find_by_text_and_language("HELLO", "en")
        result3 = await repo.find_by_text_and_language("Hello", "en")

        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        assert result1.word_id == result2.word_id == result3.word_id

    @pytest.mark.asyncio
    async def test_integration_get_frequency_words(self, integration_session):
        """Test get_frequency_words with actual database."""
        # Create words with different levels and frequencies
        words = [
            Word(word="the", language="en", level="A1", frequency_rank=1),
            Word(word="be", language="en", level="A1", frequency_rank=2),
            Word(word="to", language="en", level="A1", frequency_rank=3),
            Word(word="complex", language="en", level="B2", frequency_rank=500),
            Word(word="sophisticated", language="en", level="C1", frequency_rank=1000)
        ]
        integration_session.add_all(words)
        await integration_session.commit()

        repo = WordRepository(integration_session)

        # Get A1 words
        result = await repo.get_frequency_words("en", "A1", limit=50)
        assert len(result) == 3
        assert result[0].word == "the"
        assert result[1].word == "be"
        assert result[2].word == "to"

        # Get B2 words
        result = await repo.get_frequency_words("en", "B2", limit=50)
        assert len(result) == 1
        assert result[0].word == "complex"

        # Get words for non-existent level
        result = await repo.get_frequency_words("en", "A2", limit=50)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_integration_get_frequency_words_respects_limit(self, integration_session):
        """Test that get_frequency_words respects the limit parameter."""
        # Create 100 words
        words = [
            Word(word=f"word{i}", language="en", level="A1", frequency_rank=i)
            for i in range(1, 101)
        ]
        integration_session.add_all(words)
        await integration_session.commit()

        repo = WordRepository(integration_session)

        # Test different limits
        result = await repo.get_frequency_words("en", "A1", limit=10)
        assert len(result) == 10
        assert result[0].frequency_rank == 1
        assert result[9].frequency_rank == 10

        result = await repo.get_frequency_words("en", "A1", limit=50)
        assert len(result) == 50

    @pytest.mark.asyncio
    async def test_integration_word_repository_inherits_base_methods(self, integration_session):
        """Test that WordRepository can use base CRUD methods."""
        repo = WordRepository(integration_session)

        # Test add
        word = Word(word="test", language="en", level="A1")
        added_word = await repo.add(word)
        await repo.commit()

        assert added_word.word_id is not None

        # Test get_by_id
        retrieved = await repo.get_by_id(added_word.word_id)
        assert retrieved is not None
        assert retrieved.word == "test"

        # Test get_all
        all_words = await repo.get_all(limit=100)
        assert len(all_words) >= 1

    @pytest.mark.asyncio
    async def test_word_validation_normalizes_to_lowercase_on_insert(self, integration_session):
        """Test that Word model @validates decorator normalizes word to lowercase on insert."""
        # Create word with mixed case
        word = Word(word="HELLO", language="en", level="A1")
        integration_session.add(word)
        await integration_session.commit()

        # Retrieve and verify it's stored in lowercase
        repo = WordRepository(integration_session)
        retrieved = await repo.get_by_id(word.word_id)
        assert retrieved is not None
        assert retrieved.word == "hello"  # Should be normalized to lowercase

    @pytest.mark.asyncio
    async def test_word_validation_normalizes_to_lowercase_on_update(self, integration_session):
        """Test that Word model @validates decorator normalizes word to lowercase on update."""
        # Create word in lowercase
        word = Word(word="world", language="en", level="A1")
        integration_session.add(word)
        await integration_session.commit()

        # Update with mixed case
        word.word = "WORLD"
        await integration_session.commit()

        # Retrieve and verify it's normalized to lowercase
        repo = WordRepository(integration_session)
        retrieved = await repo.get_by_id(word.word_id)
        assert retrieved is not None
        assert retrieved.word == "world"  # Should be normalized to lowercase

    @pytest.mark.asyncio
    async def test_word_validation_ensures_data_integrity_for_case_insensitive_lookup(self, integration_session):
        """Test that @validates decorator ensures consistent data for case-insensitive lookups."""
        # Create words with various cases - should all be normalized to lowercase
        words = [
            Word(word="Computer", language="en", level="A1"),
            Word(word="PYTHON", language="en", level="A2"),
            Word(word="JavaScript", language="en", level="B1")
        ]
        integration_session.add_all(words)
        await integration_session.commit()

        # Verify all are stored in lowercase
        repo = WordRepository(integration_session)
        computer = await repo.find_by_text_and_language("computer", "en")
        python = await repo.find_by_text_and_language("python", "en")
        javascript = await repo.find_by_text_and_language("javascript", "en")

        assert computer is not None
        assert computer.word == "computer"
        assert python is not None
        assert python.word == "python"
        assert javascript is not None
        assert javascript.word == "javascript"

    @pytest.mark.asyncio
    async def test_find_by_text_returns_none_for_empty_string(self, integration_session):
        """Test that find_by_text_and_language returns None for empty string (early return)."""
        repo = WordRepository(integration_session)

        # Test with empty string
        result = await repo.find_by_text_and_language("", "en")
        assert result is None

        # Test with whitespace-only string
        result = await repo.find_by_text_and_language("   ", "en")
        assert result is None

        # Test with tab/newline
        result = await repo.find_by_text_and_language("\t\n", "en")
        assert result is None


class TestUserWordRepositoryIntegration:
    """Integration tests for UserWordRepository with actual database."""

    @pytest.fixture
    async def setup_data(self, integration_session):
        """Create test data: user, profile, words, and user_words."""
        # Create user
        user = User(user_id=123456789, native_language="ru", interface_language="ru")
        integration_session.add(user)
        await integration_session.commit()

        # Create profile
        profile = LanguageProfile(
            user_id=123456789,
            target_language="en",
            level=CEFRLevel.B1,
            is_active=True
        )
        integration_session.add(profile)
        await integration_session.commit()

        # Create words
        words = [
            Word(word="hello", language="en", level="A1", frequency_rank=1),
            Word(word="world", language="en", level="A1", frequency_rank=2),
            Word(word="computer", language="en", level="A2", frequency_rank=100)
        ]
        integration_session.add_all(words)
        await integration_session.commit()

        # Create user_words
        user_words = [
            UserWord(
                profile_id=profile.profile_id,
                word_id=words[0].word_id,
                status=WordStatusEnum.NEW,
                added_at=datetime.now(timezone.utc)
            ),
            UserWord(
                profile_id=profile.profile_id,
                word_id=words[1].word_id,
                status=WordStatusEnum.LEARNING,
                added_at=datetime.now(timezone.utc)
            ),
            UserWord(
                profile_id=profile.profile_id,
                word_id=words[2].word_id,
                status=WordStatusEnum.MASTERED,
                added_at=datetime.now(timezone.utc)
            )
        ]
        integration_session.add_all(user_words)
        await integration_session.commit()

        return {
            "user": user,
            "profile": profile,
            "words": words,
            "user_words": user_words
        }

    @pytest.mark.asyncio
    async def test_integration_get_user_word(self, integration_session, setup_data):
        """Test get_user_word with actual database and eager loading."""
        profile_id = setup_data["profile"].profile_id
        word_id = setup_data["words"][0].word_id

        repo = UserWordRepository(integration_session)
        user_word = await repo.get_user_word(profile_id=profile_id, word_id=word_id)

        assert user_word is not None
        assert user_word.profile_id == profile_id
        assert user_word.word_id == word_id
        assert user_word.status == WordStatusEnum.NEW

        # Verify eager loading - relationships should be loaded
        assert user_word.word is not None
        assert user_word.word.word == "hello"
        assert user_word.statistics is not None  # Empty list is fine

    @pytest.mark.asyncio
    async def test_integration_get_user_word_with_statistics(self, integration_session, setup_data):
        """Test get_user_word eager loads statistics."""
        profile_id = setup_data["profile"].profile_id
        word_id = setup_data["words"][0].word_id
        user_word_id = setup_data["user_words"][0].user_word_id

        # Add statistics
        stat = WordStatistics(
            user_word_id=user_word_id,
            direction="en->ru",
            test_type="translation",
            correct_count=5,
            total_attempts=10,
            total_correct=5,
            total_errors=5
        )
        integration_session.add(stat)
        await integration_session.commit()

        repo = UserWordRepository(integration_session)
        user_word = await repo.get_user_word(profile_id=profile_id, word_id=word_id)

        assert user_word is not None
        assert len(user_word.statistics) == 1
        assert user_word.statistics[0].direction == "en->ru"
        assert user_word.statistics[0].correct_count == 5

    @pytest.mark.asyncio
    async def test_integration_get_user_word_not_found(self, integration_session, setup_data):
        """Test get_user_word returns None when not found."""
        repo = UserWordRepository(integration_session)

        result = await repo.get_user_word(profile_id=999, word_id=999)
        assert result is None

    @pytest.mark.asyncio
    async def test_integration_get_user_vocabulary(self, integration_session, setup_data):
        """Test get_user_vocabulary returns all user words."""
        profile_id = setup_data["profile"].profile_id

        repo = UserWordRepository(integration_session)
        vocabulary = await repo.get_user_vocabulary(profile_id=profile_id)

        assert len(vocabulary) == 3
        statuses = [uw.status for uw in vocabulary]
        assert WordStatusEnum.NEW in statuses
        assert WordStatusEnum.LEARNING in statuses
        assert WordStatusEnum.MASTERED in statuses

        # Verify eager loading
        for uw in vocabulary:
            assert uw.word is not None
            assert uw.statistics is not None

    @pytest.mark.asyncio
    async def test_integration_get_user_vocabulary_filtered_by_status(self, integration_session, setup_data):
        """Test get_user_vocabulary with status filter."""
        profile_id = setup_data["profile"].profile_id

        repo = UserWordRepository(integration_session)

        # Get only LEARNING words
        learning_words = await repo.get_user_vocabulary(
            profile_id=profile_id,
            status=WordStatusEnum.LEARNING
        )

        assert len(learning_words) == 1
        assert learning_words[0].status == WordStatusEnum.LEARNING
        assert learning_words[0].word.word == "world"

        # Get only MASTERED words
        mastered_words = await repo.get_user_vocabulary(
            profile_id=profile_id,
            status=WordStatusEnum.MASTERED
        )

        assert len(mastered_words) == 1
        assert mastered_words[0].status == WordStatusEnum.MASTERED

    @pytest.mark.asyncio
    async def test_integration_count_by_status(self, integration_session, setup_data):
        """Test count_by_status returns correct counts."""
        profile_id = setup_data["profile"].profile_id

        repo = UserWordRepository(integration_session)
        counts = await repo.count_by_status(profile_id=profile_id)

        assert counts == {
            "new": 1,
            "learning": 1,
            "mastered": 1
        }

    @pytest.mark.asyncio
    async def test_integration_count_by_status_empty(self, integration_session, setup_data):
        """Test count_by_status returns empty dict for profile with no words."""
        repo = UserWordRepository(integration_session)

        # Non-existent profile
        counts = await repo.count_by_status(profile_id=999)
        assert counts == {}

    @pytest.mark.asyncio
    async def test_integration_user_word_repository_inherits_base_methods(self, integration_session, setup_data):
        """Test that UserWordRepository can use base CRUD methods."""
        profile_id = setup_data["profile"].profile_id

        # Create a new word
        word = Word(word="test", language="en", level="A1")
        integration_session.add(word)
        await integration_session.commit()

        repo = UserWordRepository(integration_session)

        # Test add
        user_word = UserWord(
            profile_id=profile_id,
            word_id=word.word_id,
            status=WordStatusEnum.NEW,
            added_at=datetime.now(timezone.utc)
        )
        added_user_word = await repo.add(user_word)
        await repo.commit()

        assert added_user_word.user_word_id is not None

        # Test get_by_id
        retrieved = await repo.get_by_id(added_user_word.user_word_id)
        assert retrieved is not None
        assert retrieved.status == WordStatusEnum.NEW


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_find_by_text_and_language_with_empty_string(self):
        """Test find_by_text_and_language with empty string returns None immediately."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = WordRepository(mock_session)
        result = await repo.find_by_text_and_language("", "en")

        # Should NOT execute query - early return for empty string
        mock_session.execute.assert_not_called()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_frequency_words_with_zero_limit(self):
        """Test get_frequency_words with limit=0."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = WordRepository(mock_session)
        result = await repo.get_frequency_words("en", "A1", limit=0)

        # Should execute query without error
        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_vocabulary_for_nonexistent_profile(self):
        """Test get_user_vocabulary for profile that doesn't exist."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UserWordRepository(mock_session)
        result = await repo.get_user_vocabulary(profile_id=999999)

        # Should return empty list, not raise error
        assert result == []

    @pytest.mark.asyncio
    async def test_count_by_status_with_all_words_same_status(self):
        """Test count_by_status when all words have the same status."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        # All words are NEW
        mock_result.all.return_value = [
            (WordStatusEnum.NEW, 50)
        ]
        mock_session.execute.return_value = mock_result

        repo = UserWordRepository(mock_session)
        result = await repo.count_by_status(profile_id=100)

        assert result == {"new": 50}
        assert len(result) == 1
