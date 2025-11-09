"""
Comprehensive tests for TranslationService.

Tests cover:
- TranslationService initialization
- translate_word method with cache hits and misses
- validate_answer_with_llm method with cache hits and misses
- Error handling and fallback behavior
- Proper logging for all operations
- Integration tests with mocked dependencies
- Edge cases and error scenarios
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.words.services.translation import TranslationService
from src.words.infrastructure.llm_client import LLMClient
from src.words.repositories.cache import CacheRepository


class TestTranslationServiceInitialization:
    """Tests for TranslationService initialization."""

    @pytest.mark.asyncio
    async def test_translation_service_initialization(self):
        """Test that TranslationService can be initialized with dependencies."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        service = TranslationService(mock_llm_client, mock_cache_repo)

        assert service.llm_client is mock_llm_client
        assert service.cache_repo is mock_cache_repo

    @pytest.mark.asyncio
    async def test_translation_service_stores_dependencies(self):
        """Test that TranslationService stores dependency references."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        service = TranslationService(mock_llm_client, mock_cache_repo)

        assert hasattr(service, 'llm_client')
        assert hasattr(service, 'cache_repo')


class TestTranslateWord:
    """Tests for translate_word method."""

    @pytest.mark.asyncio
    async def test_translate_word_cache_hit(self):
        """Test that translate_word returns cached result when available."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        # Mock cache hit
        cached_result = {
            "word": "hello",
            "translations": ["привет", "здравствуй"],
            "examples": [
                {"source": "Hello, world!", "target": "Привет, мир!"}
            ],
            "word_forms": {"plural": "hellos"}
        }
        mock_cache_repo.get_translation.return_value = cached_result

        service = TranslationService(mock_llm_client, mock_cache_repo)

        with patch('src.words.services.translation.logger') as mock_logger:
            result = await service.translate_word(
                word="hello",
                source_lang="en",
                target_lang="ru"
            )

            # Verify cache was checked
            mock_cache_repo.get_translation.assert_called_once_with(
                "hello", "en", "ru"
            )

            # Verify LLM was NOT called
            mock_llm_client.translate_word.assert_not_called()

            # Verify logger recorded cache hit
            mock_logger.debug.assert_called_once_with(
                "translation_cache_hit",
                word="hello",
                source="en",
                target="ru"
            )

            # Verify result
            assert result == cached_result

    @pytest.mark.asyncio
    async def test_translate_word_cache_miss(self):
        """Test that translate_word calls LLM and caches result on cache miss."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        # Mock cache miss
        mock_cache_repo.get_translation.return_value = None

        # Mock LLM result
        llm_result = {
            "word": "hello",
            "translations": ["привет", "здравствуй"],
            "examples": [
                {"source": "Hello, world!", "target": "Привет, мир!"}
            ],
            "word_forms": {"plural": "hellos"}
        }
        mock_llm_client.translate_word.return_value = llm_result

        service = TranslationService(mock_llm_client, mock_cache_repo)

        with patch('src.words.services.translation.logger') as mock_logger:
            result = await service.translate_word(
                word="hello",
                source_lang="en",
                target_lang="ru"
            )

            # Verify cache was checked
            mock_cache_repo.get_translation.assert_called_once_with(
                "hello", "en", "ru"
            )

            # Verify LLM was called
            mock_llm_client.translate_word.assert_called_once_with(
                "hello", "en", "ru"
            )

            # Verify result was cached
            mock_cache_repo.set_translation.assert_called_once_with(
                "hello", "en", "ru", llm_result
            )

            # Verify logger recorded LLM call
            mock_logger.info.assert_called_once_with(
                "translation_llm_call",
                word="hello",
                source="en",
                target="ru"
            )

            # Verify result
            assert result == llm_result

    @pytest.mark.asyncio
    async def test_translate_word_llm_error(self):
        """Test that translate_word handles LLM errors and logs them."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        # Mock cache miss
        mock_cache_repo.get_translation.return_value = None

        # Mock LLM error
        mock_llm_client.translate_word.side_effect = Exception("API error")

        service = TranslationService(mock_llm_client, mock_cache_repo)

        with patch('src.words.services.translation.logger') as mock_logger:
            with pytest.raises(Exception, match="API error"):
                await service.translate_word(
                    word="hello",
                    source_lang="en",
                    target_lang="ru"
                )

            # Verify error was logged
            mock_logger.error.assert_called_once_with(
                "translation_failed",
                word="hello",
                error="API error"
            )

            # Verify result was NOT cached
            mock_cache_repo.set_translation.assert_not_called()

    @pytest.mark.asyncio
    async def test_translate_word_does_not_cache_on_error(self):
        """Test that translate_word does not cache results when LLM fails."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        # Mock cache miss
        mock_cache_repo.get_translation.return_value = None

        # Mock LLM error
        mock_llm_client.translate_word.side_effect = ValueError("Invalid word")

        service = TranslationService(mock_llm_client, mock_cache_repo)

        with pytest.raises(ValueError):
            await service.translate_word(
                word="",
                source_lang="en",
                target_lang="ru"
            )

        # Verify set_translation was NOT called
        mock_cache_repo.set_translation.assert_not_called()

    @pytest.mark.asyncio
    async def test_translate_word_with_different_languages(self):
        """Test translate_word with different language pairs."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        # Mock cache miss
        mock_cache_repo.get_translation.return_value = None

        # Mock LLM result
        llm_result = {
            "word": "привет",
            "translations": ["hello", "hi"],
            "examples": [
                {"source": "Привет, мир!", "target": "Hello, world!"}
            ],
            "word_forms": {}
        }
        mock_llm_client.translate_word.return_value = llm_result

        service = TranslationService(mock_llm_client, mock_cache_repo)

        result = await service.translate_word(
            word="привет",
            source_lang="ru",
            target_lang="en"
        )

        # Verify correct language pair was used
        mock_llm_client.translate_word.assert_called_once_with(
            "привет", "ru", "en"
        )
        mock_cache_repo.get_translation.assert_called_once_with(
            "привет", "ru", "en"
        )

        assert result == llm_result


class TestValidateAnswerWithLLM:
    """Tests for validate_answer_with_llm method."""

    @pytest.mark.asyncio
    async def test_validate_answer_cache_hit(self):
        """Test that validate_answer returns cached result when available."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        # Mock cache hit
        cached_result = (True, "Правильно!")
        mock_cache_repo.get_validation.return_value = cached_result

        service = TranslationService(mock_llm_client, mock_cache_repo)

        with patch('src.words.services.translation.logger') as mock_logger:
            is_correct, comment = await service.validate_answer_with_llm(
                question="hello",
                expected="привет",
                user_answer="привет",
                source_lang="en",
                target_lang="ru",
                word_id=123,
                direction="forward"
            )

            # Verify cache was checked
            mock_cache_repo.get_validation.assert_called_once_with(
                123, "forward", "привет", "привет"
            )

            # Verify LLM was NOT called
            mock_llm_client.validate_answer.assert_not_called()

            # Verify logger recorded cache hit
            mock_logger.debug.assert_called_once_with(
                "validation_cache_hit",
                word_id=123,
                user_answer="привет"
            )

            # Verify result
            assert is_correct is True
            assert comment == "Правильно!"

    @pytest.mark.asyncio
    async def test_validate_answer_cache_miss(self):
        """Test that validate_answer calls LLM and caches result on cache miss."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        # Mock cache miss
        mock_cache_repo.get_validation.return_value = None

        # Mock LLM result
        llm_result = {
            "is_correct": False,
            "comment": "Неправильно. Правильный ответ: привет"
        }
        mock_llm_client.validate_answer.return_value = llm_result

        service = TranslationService(mock_llm_client, mock_cache_repo)

        with patch('src.words.services.translation.logger') as mock_logger:
            is_correct, comment = await service.validate_answer_with_llm(
                question="hello",
                expected="привет",
                user_answer="превет",
                source_lang="en",
                target_lang="ru",
                word_id=123,
                direction="forward"
            )

            # Verify cache was checked
            mock_cache_repo.get_validation.assert_called_once_with(
                123, "forward", "привет", "превет"
            )

            # Verify LLM was called
            mock_llm_client.validate_answer.assert_called_once_with(
                "hello", "привет", "превет", "en", "ru"
            )

            # Verify result was cached
            mock_cache_repo.set_validation.assert_called_once_with(
                123, "forward", "привет", "превет", False,
                "Неправильно. Правильный ответ: привет"
            )

            # Verify logger recorded LLM call
            mock_logger.info.assert_called_once_with(
                "validation_llm_call",
                word_id=123,
                expected="привет",
                user_answer="превет"
            )

            # Verify result
            assert is_correct is False
            assert comment == "Неправильно. Правильный ответ: привет"

    @pytest.mark.asyncio
    async def test_validate_answer_llm_error_fallback(self):
        """Test that validate_answer falls back gracefully on LLM error."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        # Mock cache miss
        mock_cache_repo.get_validation.return_value = None

        # Mock LLM error
        mock_llm_client.validate_answer.side_effect = Exception("API error")

        service = TranslationService(mock_llm_client, mock_cache_repo)

        with patch('src.words.services.translation.logger') as mock_logger:
            is_correct, comment = await service.validate_answer_with_llm(
                question="hello",
                expected="привет",
                user_answer="превет",
                source_lang="en",
                target_lang="ru",
                word_id=123,
                direction="forward"
            )

            # Verify error was logged
            mock_logger.error.assert_called_once_with(
                "validation_failed",
                word_id=123,
                error="API error"
            )

            # Verify fallback behavior: (False, error message)
            assert is_correct is False
            assert comment == "Validation service unavailable. Please try again."

            # Verify result was NOT cached
            mock_cache_repo.set_validation.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_answer_does_not_cache_on_error(self):
        """Test that validate_answer does not cache results when LLM fails."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        # Mock cache miss
        mock_cache_repo.get_validation.return_value = None

        # Mock LLM error
        mock_llm_client.validate_answer.side_effect = ValueError("Invalid answer")

        service = TranslationService(mock_llm_client, mock_cache_repo)

        is_correct, comment = await service.validate_answer_with_llm(
            question="hello",
            expected="привет",
            user_answer="превет",
            source_lang="en",
            target_lang="ru",
            word_id=123,
            direction="forward"
        )

        # Verify set_validation was NOT called
        mock_cache_repo.set_validation.assert_not_called()

        # Verify fallback
        assert is_correct is False
        assert "unavailable" in comment.lower()

    @pytest.mark.asyncio
    async def test_validate_answer_with_correct_answer(self):
        """Test validate_answer with a correct answer."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        # Mock cache miss
        mock_cache_repo.get_validation.return_value = None

        # Mock LLM result for correct answer
        llm_result = {
            "is_correct": True,
            "comment": "Правильно! Отличная работа!"
        }
        mock_llm_client.validate_answer.return_value = llm_result

        service = TranslationService(mock_llm_client, mock_cache_repo)

        is_correct, comment = await service.validate_answer_with_llm(
            question="hello",
            expected="привет",
            user_answer="привет",
            source_lang="en",
            target_lang="ru",
            word_id=123,
            direction="forward"
        )

        # Verify result
        assert is_correct is True
        assert "Правильно" in comment

    @pytest.mark.asyncio
    async def test_validate_answer_with_different_direction(self):
        """Test validate_answer with backward direction."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        # Mock cache miss
        mock_cache_repo.get_validation.return_value = None

        # Mock LLM result
        llm_result = {
            "is_correct": True,
            "comment": "Correct!"
        }
        mock_llm_client.validate_answer.return_value = llm_result

        service = TranslationService(mock_llm_client, mock_cache_repo)

        is_correct, comment = await service.validate_answer_with_llm(
            question="привет",
            expected="hello",
            user_answer="hello",
            source_lang="ru",
            target_lang="en",
            word_id=456,
            direction="backward"
        )

        # Verify correct direction was used
        mock_cache_repo.get_validation.assert_called_once_with(
            456, "backward", "hello", "hello"
        )

        # Verify result was cached with correct direction
        mock_cache_repo.set_validation.assert_called_once()
        call_args = mock_cache_repo.set_validation.call_args[0]
        assert call_args[0] == 456  # word_id
        assert call_args[1] == "backward"  # direction

        assert is_correct is True


class TestTranslationServiceIntegration:
    """Integration tests for TranslationService with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_full_translation_workflow(self):
        """Test complete translation workflow from cache miss to cache hit."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        # First call: cache miss
        mock_cache_repo.get_translation.return_value = None

        # Mock LLM result
        llm_result = {
            "word": "test",
            "translations": ["тест"],
            "examples": [
                {"source": "This is a test.", "target": "Это тест."}
            ],
            "word_forms": {"plural": "tests"}
        }
        mock_llm_client.translate_word.return_value = llm_result

        service = TranslationService(mock_llm_client, mock_cache_repo)

        # First call - should hit LLM
        result1 = await service.translate_word(
            word="test",
            source_lang="en",
            target_lang="ru"
        )

        assert result1 == llm_result
        assert mock_llm_client.translate_word.call_count == 1
        assert mock_cache_repo.set_translation.call_count == 1

        # Second call: cache hit
        mock_cache_repo.get_translation.return_value = llm_result

        result2 = await service.translate_word(
            word="test",
            source_lang="en",
            target_lang="ru"
        )

        assert result2 == llm_result
        # LLM should not be called again
        assert mock_llm_client.translate_word.call_count == 1

    @pytest.mark.asyncio
    async def test_full_validation_workflow(self):
        """Test complete validation workflow from cache miss to cache hit."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        # First call: cache miss
        mock_cache_repo.get_validation.return_value = None

        # Mock LLM result
        llm_result = {
            "is_correct": True,
            "comment": "Perfect!"
        }
        mock_llm_client.validate_answer.return_value = llm_result

        service = TranslationService(mock_llm_client, mock_cache_repo)

        # First call - should hit LLM
        is_correct1, comment1 = await service.validate_answer_with_llm(
            question="test",
            expected="тест",
            user_answer="тест",
            source_lang="en",
            target_lang="ru",
            word_id=789,
            direction="forward"
        )

        assert is_correct1 is True
        assert comment1 == "Perfect!"
        assert mock_llm_client.validate_answer.call_count == 1
        assert mock_cache_repo.set_validation.call_count == 1

        # Second call: cache hit
        mock_cache_repo.get_validation.return_value = (True, "Perfect!")

        is_correct2, comment2 = await service.validate_answer_with_llm(
            question="test",
            expected="тест",
            user_answer="тест",
            source_lang="en",
            target_lang="ru",
            word_id=789,
            direction="forward"
        )

        assert is_correct2 is True
        assert comment2 == "Perfect!"
        # LLM should not be called again
        assert mock_llm_client.validate_answer.call_count == 1

    @pytest.mark.asyncio
    async def test_multiple_validation_attempts_same_word(self):
        """Test multiple validation attempts for the same word with different answers."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        service = TranslationService(mock_llm_client, mock_cache_repo)

        # First attempt: wrong answer
        mock_cache_repo.get_validation.return_value = None
        mock_llm_client.validate_answer.return_value = {
            "is_correct": False,
            "comment": "Wrong!"
        }

        is_correct1, comment1 = await service.validate_answer_with_llm(
            question="test",
            expected="тест",
            user_answer="тэст",
            source_lang="en",
            target_lang="ru",
            word_id=789,
            direction="forward"
        )

        assert is_correct1 is False

        # Second attempt: correct answer (different answer, so cache miss)
        mock_cache_repo.get_validation.return_value = None
        mock_llm_client.validate_answer.return_value = {
            "is_correct": True,
            "comment": "Correct!"
        }

        is_correct2, comment2 = await service.validate_answer_with_llm(
            question="test",
            expected="тест",
            user_answer="тест",
            source_lang="en",
            target_lang="ru",
            word_id=789,
            direction="forward"
        )

        assert is_correct2 is True

        # Verify both attempts were cached separately
        assert mock_cache_repo.set_validation.call_count == 2


class TestTranslationServiceEdgeCases:
    """Tests for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_translate_word_with_empty_cache_repo_response(self):
        """Test translate_word when cache returns None explicitly."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        mock_cache_repo.get_translation.return_value = None
        mock_llm_client.translate_word.return_value = {
            "word": "hello",
            "translations": ["привет"],
            "examples": [],
            "word_forms": {}
        }

        service = TranslationService(mock_llm_client, mock_cache_repo)

        result = await service.translate_word("hello", "en", "ru")

        # Should call LLM when cache returns None
        mock_llm_client.translate_word.assert_called_once()
        assert result["word"] == "hello"

    @pytest.mark.asyncio
    async def test_validate_answer_with_empty_cache_repo_response(self):
        """Test validate_answer when cache returns None explicitly."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        mock_cache_repo.get_validation.return_value = None
        mock_llm_client.validate_answer.return_value = {
            "is_correct": True,
            "comment": "Good!"
        }

        service = TranslationService(mock_llm_client, mock_cache_repo)

        is_correct, comment = await service.validate_answer_with_llm(
            question="hello",
            expected="привет",
            user_answer="привет",
            source_lang="en",
            target_lang="ru",
            word_id=123,
            direction="forward"
        )

        # Should call LLM when cache returns None
        mock_llm_client.validate_answer.assert_called_once()
        assert is_correct is True

    @pytest.mark.asyncio
    async def test_validate_answer_fallback_message_format(self):
        """Test that validation fallback message is user-friendly."""
        mock_llm_client = AsyncMock(spec=LLMClient)
        mock_cache_repo = AsyncMock(spec=CacheRepository)

        mock_cache_repo.get_validation.return_value = None
        mock_llm_client.validate_answer.side_effect = Exception("Network error")

        service = TranslationService(mock_llm_client, mock_cache_repo)

        is_correct, comment = await service.validate_answer_with_llm(
            question="hello",
            expected="привет",
            user_answer="превет",
            source_lang="en",
            target_lang="ru",
            word_id=123,
            direction="forward"
        )

        # Verify fallback message
        assert is_correct is False
        assert "Validation service unavailable" in comment
        assert "try again" in comment.lower()
