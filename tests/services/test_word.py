"""
Comprehensive tests for WordService.

Tests cover:
- WordService initialization
- add_word_for_user method with new words, existing words, and deduplication
- get_word_with_translations method
- get_user_vocabulary_stats method
- Error handling and edge cases
- Proper logging for all operations
- Integration tests with mocked dependencies
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.words.services.word import WordService
from src.words.repositories.word import WordRepository, UserWordRepository
from src.words.services.translation import TranslationService
from src.words.models.word import Word, UserWord, WordStatusEnum


class TestWordServiceInitialization:
    """Tests for WordService initialization."""

    @pytest.mark.asyncio
    async def test_word_service_initialization(self):
        """Test that WordService can be initialized with dependencies."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        assert service.word_repo is mock_word_repo
        assert service.user_word_repo is mock_user_word_repo
        assert service.translation_service is mock_translation_service

    @pytest.mark.asyncio
    async def test_word_service_stores_dependencies(self):
        """Test that WordService stores dependency references."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        assert hasattr(service, 'word_repo')
        assert hasattr(service, 'user_word_repo')
        assert hasattr(service, 'translation_service')


class TestAddWordForUser:
    """Tests for add_word_for_user method."""

    @pytest.mark.asyncio
    async def test_add_word_for_user_new_word(self):
        """Test adding a completely new word to user vocabulary."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock translation data (returns list of translations)
        translation_data = {
            "word": "hello",
            "translations": ["привет", "здравствуй"],
            "examples": [
                {"source": "Hello, world!", "target": "Привет, мир!"}
            ],
            "word_forms": {"plural": "hellos"}
        }
        mock_translation_service.translate_word.return_value = translation_data

        # Mock word not found (new word) - CHECKED FIRST in optimized flow
        mock_word_repo.find_by_text_and_language.return_value = None

        # Mock word creation
        created_word = Word(
            word="hello",
            language="en",  # Source language
            translations={"ru": translation_data["translations"]},  # Dict format
            examples=translation_data["examples"],
            word_forms=translation_data["word_forms"]
        )
        created_word.word_id = 1
        mock_word_repo.add.return_value = created_word

        # Mock user word creation
        created_user_word = UserWord(
            profile_id=1,
            word_id=1,
            status=WordStatusEnum.NEW
        )
        created_user_word.user_word_id = 10
        mock_user_word_repo.add.return_value = created_user_word

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with patch('src.words.services.word.logger') as mock_logger:
            result = await service.add_word_for_user(
                profile_id=1,
                word_text="hello",
                source_language="en",
                target_language="ru"
            )

            # OPTIMIZATION: Verify word lookup happens FIRST (before translation)
            mock_word_repo.find_by_text_and_language.assert_called_once_with(
                "hello", "en"
            )

            # Verify translation was fetched (only for new words)
            mock_translation_service.translate_word.assert_called_once_with(
                "hello", "en", "ru"
            )

            # Verify word was created
            mock_word_repo.add.assert_called_once()
            created_word_arg = mock_word_repo.add.call_args[0][0]
            assert created_word_arg.word == "hello"
            assert created_word_arg.language == "en"  # Source language
            # Verify translations dict format
            assert created_word_arg.translations == {"ru": ["привет", "здравствуй"]}

            # Verify word was committed separately
            assert mock_word_repo.commit.call_count == 1

            # OPTIMIZATION: get_user_word is NOT called for new words
            # (word doesn't exist, so we skip straight to creation)
            mock_user_word_repo.get_user_word.assert_not_called()

            # Verify user word was created
            mock_user_word_repo.add.assert_called_once()
            created_user_word_arg = mock_user_word_repo.add.call_args[0][0]
            assert created_user_word_arg.profile_id == 1
            assert created_user_word_arg.word_id == 1
            assert created_user_word_arg.status == WordStatusEnum.NEW

            # Verify user word commit was called
            mock_user_word_repo.commit.assert_called_once()

            # Verify logging calls
            assert mock_logger.info.call_count >= 2
            # Check for word_addition_started
            mock_logger.info.assert_any_call(
                "word_addition_started",
                profile_id=1,
                word="hello",
                source_language="en",
                target_language="ru"
            )

            # Verify result
            assert result.profile_id == 1
            assert result.word_id == 1
            assert result.status == WordStatusEnum.NEW

    @pytest.mark.asyncio
    async def test_add_word_for_user_existing_word(self):
        """Test adding an existing word (word exists in DB but not in user vocabulary)."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock word found (existing word) - stored with source language
        # OPTIMIZATION: Word is checked FIRST, before translation
        existing_word = Word(
            word="test",
            language="en",  # Source language
            translations={"ru": ["тест"]},  # Dict format
            examples=[],
            word_forms={}
        )
        existing_word.word_id = 5
        mock_word_repo.find_by_text_and_language.return_value = existing_word

        # Mock user word not found (not duplicate)
        mock_user_word_repo.get_user_word.return_value = None

        # Mock user word creation
        created_user_word = UserWord(
            profile_id=2,
            word_id=5,
            status=WordStatusEnum.NEW
        )
        created_user_word.user_word_id = 20
        mock_user_word_repo.add.return_value = created_user_word

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with patch('src.words.services.word.logger') as mock_logger:
            result = await service.add_word_for_user(
                profile_id=2,
                word_text="test",
                source_language="en",
                target_language="ru"
            )

            # OPTIMIZATION: Verify word lookup happens FIRST
            mock_word_repo.find_by_text_and_language.assert_called_once_with(
                "test", "en"
            )

            # OPTIMIZATION: Translation is NOT fetched for existing words
            mock_translation_service.translate_word.assert_not_called()

            # Verify word was NOT created (already exists)
            mock_word_repo.add.assert_not_called()

            # Verify user word check was performed
            mock_user_word_repo.get_user_word.assert_called_once_with(2, 5)

            # Verify user word was created
            mock_user_word_repo.add.assert_called_once()
            created_user_word_arg = mock_user_word_repo.add.call_args[0][0]
            assert created_user_word_arg.word_id == 5  # Existing word ID

            # Verify commit
            mock_user_word_repo.commit.assert_called_once()

            # Verify logging includes word_addition_started
            assert mock_logger.info.call_count >= 1
            mock_logger.info.assert_any_call(
                "word_addition_started",
                profile_id=2,
                word="test",
                source_language="en",
                target_language="ru"
            )

            assert result.word_id == 5

    @pytest.mark.asyncio
    async def test_add_word_for_user_duplicate(self):
        """Test adding a word that user already has (deduplication)."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock word found - stored with source language
        # OPTIMIZATION: Word is checked FIRST, before translation
        existing_word = Word(
            word="duplicate",
            language="en",  # Source language
            translations={"ru": ["дубликат"]},  # Dict format
            examples=[],
            word_forms={}
        )
        existing_word.word_id = 7
        mock_word_repo.find_by_text_and_language.return_value = existing_word

        # Mock user word found (duplicate!)
        existing_user_word = UserWord(
            profile_id=3,
            word_id=7,
            status=WordStatusEnum.LEARNING
        )
        existing_user_word.user_word_id = 30
        mock_user_word_repo.get_user_word.return_value = existing_user_word

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with patch('src.words.services.word.logger') as mock_logger:
            result = await service.add_word_for_user(
                profile_id=3,
                word_text="duplicate",
                source_language="en",
                target_language="ru"
            )

            # OPTIMIZATION: Verify word lookup happens FIRST
            mock_word_repo.find_by_text_and_language.assert_called_once_with(
                "duplicate", "en"
            )

            # OPTIMIZATION: Translation is NOT fetched for duplicates (early return)
            mock_translation_service.translate_word.assert_not_called()

            # Verify user word lookup was performed
            mock_user_word_repo.get_user_word.assert_called_once_with(3, 7)

            # Verify user word was NOT created (duplicate)
            mock_user_word_repo.add.assert_not_called()

            # Verify commit was NOT called
            mock_user_word_repo.commit.assert_not_called()

            # Verify warning logged
            mock_logger.warning.assert_called_once_with(
                "word_already_in_user_vocabulary",
                profile_id=3,
                word_id=7,
                word="duplicate"
            )

            # Verify info was called (word_addition_started)
            assert mock_logger.info.call_count >= 1

            # Verify result is the existing user word
            assert result.user_word_id == 30
            assert result.status == WordStatusEnum.LEARNING

    @pytest.mark.asyncio
    async def test_add_word_for_user_normalizes_word(self):
        """Test that word text is normalized to lowercase."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock translation data
        translation_data = {
            "word": "HELLO",
            "translations": ["привет"],
            "examples": [],
            "word_forms": {}
        }
        mock_translation_service.translate_word.return_value = translation_data

        # Mock word not found
        mock_word_repo.find_by_text_and_language.return_value = None

        # Mock word creation
        created_word = Word(
            word="hello",  # Normalized
            language="en",  # Source language
            translations={"ru": ["привет"]},  # Dict format
            examples=[],
            word_forms={}
        )
        created_word.word_id = 1
        mock_word_repo.add.return_value = created_word

        # Mock user word not found
        mock_user_word_repo.get_user_word.return_value = None

        # Mock user word creation
        created_user_word = UserWord(
            profile_id=1,
            word_id=1,
            status=WordStatusEnum.NEW
        )
        mock_user_word_repo.add.return_value = created_user_word

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with patch('src.words.services.word.logger'):
            await service.add_word_for_user(
                profile_id=1,
                word_text="HELLO",
                source_language="en",
                target_language="ru"
            )

        # Verify word was created with lowercase text
        created_word_arg = mock_word_repo.add.call_args[0][0]
        assert created_word_arg.word == "hello"

    @pytest.mark.asyncio
    async def test_add_word_for_user_with_empty_translations(self):
        """Test adding word when translation data has empty fields."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock translation data with missing fields
        translation_data = {
            "word": "test"
            # No translations, examples, or word_forms
        }
        mock_translation_service.translate_word.return_value = translation_data

        # Mock word not found
        mock_word_repo.find_by_text_and_language.return_value = None

        # Mock word creation
        created_word = Word(
            word="test",
            language="en",  # Source language
            translations={"ru": []},  # Dict format with empty list
            examples=[],
            word_forms={}
        )
        created_word.word_id = 1
        mock_word_repo.add.return_value = created_word

        # Mock user word not found
        mock_user_word_repo.get_user_word.return_value = None

        # Mock user word creation
        created_user_word = UserWord(
            profile_id=1,
            word_id=1,
            status=WordStatusEnum.NEW
        )
        mock_user_word_repo.add.return_value = created_user_word

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with patch('src.words.services.word.logger'):
            result = await service.add_word_for_user(
                profile_id=1,
                word_text="test",
                source_language="en",
                target_language="ru"
            )

        # Verify word was created with empty defaults
        created_word_arg = mock_word_repo.add.call_args[0][0]
        assert created_word_arg.translations == {"ru": []}
        assert created_word_arg.examples == []
        assert created_word_arg.word_forms == {}

        assert result is not None


class TestGetWordWithTranslations:
    """Tests for get_word_with_translations method."""

    @pytest.mark.asyncio
    async def test_get_word_with_translations(self):
        """Test that get_word_with_translations delegates to TranslationService."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock translation result
        translation_result = {
            "word": "hello",
            "translations": ["привет", "здравствуй"],
            "examples": [
                {"source": "Hello!", "target": "Привет!"}
            ],
            "word_forms": {"plural": "hellos"}
        }
        mock_translation_service.translate_word.return_value = translation_result

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        result = await service.get_word_with_translations(
            word_text="hello",
            source_language="en",
            target_language="ru"
        )

        # Verify translation service was called
        mock_translation_service.translate_word.assert_called_once_with(
            "hello", "en", "ru"
        )

        # Verify result
        assert result == translation_result

    @pytest.mark.asyncio
    async def test_get_word_with_translations_different_languages(self):
        """Test get_word_with_translations with different language pairs."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock translation result
        translation_result = {
            "word": "bonjour",
            "translations": ["hello", "hi"],
            "examples": [],
            "word_forms": {}
        }
        mock_translation_service.translate_word.return_value = translation_result

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        result = await service.get_word_with_translations(
            word_text="bonjour",
            source_language="fr",
            target_language="en"
        )

        # Verify correct language pair was used
        mock_translation_service.translate_word.assert_called_once_with(
            "bonjour", "fr", "en"
        )

        assert result == translation_result


class TestGetUserVocabularyStats:
    """Tests for get_user_vocabulary_stats method."""

    @pytest.mark.asyncio
    async def test_get_user_vocabulary_stats(self):
        """Test getting vocabulary statistics for a user."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock counts by status
        mock_counts = {
            "new": 10,
            "learning": 25,
            "reviewing": 40,
            "mastered": 75
        }
        mock_user_word_repo.count_by_status.return_value = mock_counts

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        result = await service.get_user_vocabulary_stats(profile_id=1)

        # Verify repository was called
        mock_user_word_repo.count_by_status.assert_called_once_with(1)

        # Verify result
        assert result["total"] == 150  # Sum of all counts
        assert result["new"] == 10
        assert result["learning"] == 25
        assert result["reviewing"] == 40
        assert result["mastered"] == 75

    @pytest.mark.asyncio
    async def test_get_user_vocabulary_stats_empty(self):
        """Test getting vocabulary statistics when user has no words."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock empty counts
        mock_counts = {}
        mock_user_word_repo.count_by_status.return_value = mock_counts

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        result = await service.get_user_vocabulary_stats(profile_id=2)

        # Verify result with all zeros
        assert result["total"] == 0
        assert result["new"] == 0
        assert result["learning"] == 0
        assert result["reviewing"] == 0
        assert result["mastered"] == 0

    @pytest.mark.asyncio
    async def test_get_user_vocabulary_stats_partial(self):
        """Test getting vocabulary statistics with some missing statuses."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock partial counts (only some statuses)
        mock_counts = {
            "new": 5,
            "learning": 15
            # No reviewing or mastered
        }
        mock_user_word_repo.count_by_status.return_value = mock_counts

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        result = await service.get_user_vocabulary_stats(profile_id=3)

        # Verify result with missing statuses defaulting to 0
        assert result["total"] == 20  # 5 + 15
        assert result["new"] == 5
        assert result["learning"] == 15
        assert result["reviewing"] == 0  # Missing, defaults to 0
        assert result["mastered"] == 0  # Missing, defaults to 0

    @pytest.mark.asyncio
    async def test_get_user_vocabulary_stats_calculates_total_correctly(self):
        """Test that total is calculated correctly as sum of all counts."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock various counts
        mock_counts = {
            "new": 1,
            "learning": 2,
            "reviewing": 3,
            "mastered": 4
        }
        mock_user_word_repo.count_by_status.return_value = mock_counts

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        result = await service.get_user_vocabulary_stats(profile_id=4)

        # Verify total calculation
        assert result["total"] == 10  # 1 + 2 + 3 + 4


class TestWordServiceIntegration:
    """Integration tests for WordService with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_full_word_addition_workflow(self):
        """Test complete word addition workflow from translation to commit."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock translation
        translation_data = {
            "word": "world",
            "translations": ["мир"],
            "examples": [{"source": "Hello, world!", "target": "Привет, мир!"}],
            "word_forms": {"plural": "worlds"}
        }
        mock_translation_service.translate_word.return_value = translation_data

        # Mock word not found
        mock_word_repo.find_by_text_and_language.return_value = None

        # Mock word creation
        created_word = Word(
            word="world",
            language="en",  # Source language
            translations={"ru": translation_data["translations"]},  # Dict format
            examples=translation_data["examples"],
            word_forms=translation_data["word_forms"]
        )
        created_word.word_id = 100
        mock_word_repo.add.return_value = created_word

        # Mock user word not found
        mock_user_word_repo.get_user_word.return_value = None

        # Mock user word creation
        created_user_word = UserWord(
            profile_id=5,
            word_id=100,
            status=WordStatusEnum.NEW
        )
        created_user_word.user_word_id = 500
        mock_user_word_repo.add.return_value = created_user_word

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with patch('src.words.services.word.logger'):
            result = await service.add_word_for_user(
                profile_id=5,
                word_text="world",
                source_language="en",
                target_language="ru"
            )

            # OPTIMIZATION: Verify steps executed in optimized order
            # 1. Check word exists (before translation)
            assert mock_word_repo.find_by_text_and_language.called
            # 2. Get translation (only for new words)
            assert mock_translation_service.translate_word.called
            # 3. Create word
            assert mock_word_repo.add.called
            assert mock_word_repo.commit.called  # Word committed separately
            # 4. get_user_word NOT called for new words (optimization)
            assert not mock_user_word_repo.get_user_word.called
            # 5. Create user_word
            assert mock_user_word_repo.add.called
            assert mock_user_word_repo.commit.called

            # Verify final result
            assert result.profile_id == 5
            assert result.word_id == 100
            assert result.status == WordStatusEnum.NEW

    @pytest.mark.asyncio
    async def test_multiple_users_adding_same_word(self):
        """Test multiple users adding the same word (word reuse)."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock translation
        translation_data = {
            "word": "common",
            "translations": ["общий"],
            "examples": [],
            "word_forms": {}
        }
        mock_translation_service.translate_word.return_value = translation_data

        # Mock existing word (stored with source language)
        existing_word = Word(
            word="common",
            language="en",  # Source language
            translations={"ru": ["общий"]},  # Dict format
            examples=[],
            word_forms={}
        )
        existing_word.word_id = 999
        mock_word_repo.find_by_text_and_language.return_value = existing_word

        # Mock user word not found for both users
        mock_user_word_repo.get_user_word.return_value = None

        # Mock user word creation
        def create_user_word(user_word):
            user_word.user_word_id = 1000
            return user_word

        mock_user_word_repo.add.side_effect = create_user_word

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with patch('src.words.services.word.logger'):
            # User 1 adds word
            result1 = await service.add_word_for_user(
                profile_id=10,
                word_text="common",
                source_language="en",
                target_language="ru"
            )

            # User 2 adds same word
            result2 = await service.add_word_for_user(
                profile_id=20,
                word_text="common",
                source_language="en",
                target_language="ru"
            )

            # Both users should have same word_id (word reuse)
            assert result1.word_id == 999
            assert result2.word_id == 999

            # But different profile_ids
            assert result1.profile_id == 10
            assert result2.profile_id == 20

            # Word should only be created once
            assert mock_word_repo.add.call_count == 0  # Word already existed


class TestWordServiceEdgeCases:
    """Tests for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_add_word_preserves_translation_data(self):
        """Test that translation data is correctly preserved when creating word."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock rich translation data
        translation_data = {
            "word": "complex",
            "translations": ["сложный", "комплексный"],
            "examples": [
                {"source": "Complex task", "target": "Сложная задача"},
                {"source": "Complex system", "target": "Комплексная система"}
            ],
            "word_forms": {
                "plural": "complexes",
                "comparative": "more complex",
                "superlative": "most complex"
            }
        }
        mock_translation_service.translate_word.return_value = translation_data

        # Mock word not found
        mock_word_repo.find_by_text_and_language.return_value = None

        # Mock word creation
        created_word = None

        def capture_word(word):
            nonlocal created_word
            created_word = word
            word.word_id = 1
            return word

        mock_word_repo.add.side_effect = capture_word

        # Mock user word not found
        mock_user_word_repo.get_user_word.return_value = None

        # Mock user word creation
        created_user_word = UserWord(
            profile_id=1,
            word_id=1,
            status=WordStatusEnum.NEW
        )
        mock_user_word_repo.add.return_value = created_user_word

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with patch('src.words.services.word.logger'):
            await service.add_word_for_user(
                profile_id=1,
                word_text="complex",
                source_language="en",
                target_language="ru"
            )

            # Verify all translation data was preserved in dict format
            assert created_word.translations == {"ru": translation_data["translations"]}
            assert created_word.examples == translation_data["examples"]
            assert created_word.word_forms == translation_data["word_forms"]

    @pytest.mark.asyncio
    async def test_stats_with_large_numbers(self):
        """Test vocabulary statistics with large numbers."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock large counts
        mock_counts = {
            "new": 1000,
            "learning": 2500,
            "reviewing": 5000,
            "mastered": 10000
        }
        mock_user_word_repo.count_by_status.return_value = mock_counts

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        result = await service.get_user_vocabulary_stats(profile_id=99)

        # Verify large total is calculated correctly
        assert result["total"] == 18500
        assert result["new"] == 1000
        assert result["learning"] == 2500
        assert result["reviewing"] == 5000
        assert result["mastered"] == 10000


class TestWordServiceInputValidation:
    """Tests for input validation in WordService."""

    @pytest.mark.asyncio
    async def test_add_word_invalid_profile_id_none(self):
        """Test that adding word with None profile_id raises ValueError."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with pytest.raises(ValueError, match="Invalid profile_id"):
            await service.add_word_for_user(
                profile_id=None,
                word_text="hello",
                source_language="en",
                target_language="ru"
            )

    @pytest.mark.asyncio
    async def test_add_word_invalid_profile_id_zero(self):
        """Test that adding word with zero profile_id raises ValueError."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with pytest.raises(ValueError, match="Invalid profile_id"):
            await service.add_word_for_user(
                profile_id=0,
                word_text="hello",
                source_language="en",
                target_language="ru"
            )

    @pytest.mark.asyncio
    async def test_add_word_invalid_profile_id_negative(self):
        """Test that adding word with negative profile_id raises ValueError."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with pytest.raises(ValueError, match="Invalid profile_id"):
            await service.add_word_for_user(
                profile_id=-1,
                word_text="hello",
                source_language="en",
                target_language="ru"
            )

    @pytest.mark.asyncio
    async def test_add_word_empty_word_text(self):
        """Test that adding word with empty word_text raises ValueError."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with pytest.raises(ValueError, match="Invalid word_text"):
            await service.add_word_for_user(
                profile_id=1,
                word_text="",
                source_language="en",
                target_language="ru"
            )

    @pytest.mark.asyncio
    async def test_add_word_whitespace_only_word_text(self):
        """Test that adding word with whitespace-only word_text raises ValueError."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with pytest.raises(ValueError, match="Invalid word_text"):
            await service.add_word_for_user(
                profile_id=1,
                word_text="   ",
                source_language="en",
                target_language="ru"
            )

    @pytest.mark.asyncio
    async def test_add_word_empty_source_language(self):
        """Test that adding word with empty source_language raises ValueError."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with pytest.raises(ValueError, match="Invalid source_language"):
            await service.add_word_for_user(
                profile_id=1,
                word_text="hello",
                source_language="",
                target_language="ru"
            )

    @pytest.mark.asyncio
    async def test_add_word_empty_target_language(self):
        """Test that adding word with empty target_language raises ValueError."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with pytest.raises(ValueError, match="Invalid target_language"):
            await service.add_word_for_user(
                profile_id=1,
                word_text="hello",
                source_language="en",
                target_language=""
            )


class TestWordServiceErrorHandling:
    """Tests for error handling in WordService."""

    @pytest.mark.asyncio
    async def test_add_word_translation_service_error(self):
        """Test that translation service errors are properly handled and logged."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # OPTIMIZATION: Mock word not found (so translation is called)
        mock_word_repo.find_by_text_and_language.return_value = None

        # Mock translation service to raise exception
        mock_translation_service.translate_word.side_effect = Exception("Translation API error")

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with patch('src.words.services.word.logger') as mock_logger:
            with pytest.raises(Exception, match="Translation API error"):
                await service.add_word_for_user(
                    profile_id=1,
                    word_text="hello",
                    source_language="en",
                    target_language="ru"
                )

            # Verify error was logged
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            assert error_call[0][0] == "word_addition_failed"
            assert "Translation API error" in str(error_call[1]["error"])

            # Verify rollback was called
            mock_word_repo.rollback.assert_called_once()
            mock_user_word_repo.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_word_database_error(self):
        """Test that database errors are properly handled and logged."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        # Mock translation
        translation_data = {
            "word": "hello",
            "translations": ["привет"],
            "examples": [],
            "word_forms": {}
        }
        mock_translation_service.translate_word.return_value = translation_data

        # Mock word lookup to raise database error
        mock_word_repo.find_by_text_and_language.side_effect = Exception("Database connection lost")

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with patch('src.words.services.word.logger') as mock_logger:
            with pytest.raises(Exception, match="Database connection lost"):
                await service.add_word_for_user(
                    profile_id=1,
                    word_text="hello",
                    source_language="en",
                    target_language="ru"
                )

            # Verify error was logged
            assert mock_logger.error.call_count >= 1
            error_call = mock_logger.error.call_args
            assert error_call[0][0] == "word_addition_failed"

            # Verify rollback was called
            mock_word_repo.rollback.assert_called_once()
            mock_user_word_repo.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_word_validation_error_logging(self):
        """Test that validation errors are properly logged."""
        mock_word_repo = AsyncMock(spec=WordRepository)
        mock_user_word_repo = AsyncMock(spec=UserWordRepository)
        mock_translation_service = AsyncMock(spec=TranslationService)

        service = WordService(
            mock_word_repo,
            mock_user_word_repo,
            mock_translation_service
        )

        with patch('src.words.services.word.logger') as mock_logger:
            try:
                await service.add_word_for_user(
                    profile_id=0,
                    word_text="hello",
                    source_language="en",
                    target_language="ru"
                )
                assert False, "Should have raised ValueError"
            except ValueError as e:
                # Verify ValueError was raised
                assert "Invalid profile_id" in str(e)

                # Verify validation error was logged
                mock_logger.error.assert_called_once()
                error_call = mock_logger.error.call_args
                assert error_call[0][0] == "word_addition_validation_failed"
                assert "profile_id" in str(error_call[1]["error"])
