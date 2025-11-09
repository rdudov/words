"""
Comprehensive tests for LLM client infrastructure module.

Tests cover:
- LLMClient initialization and basic functionality
- Translation method with retry logic and validation
- Validation method with retry logic
- Error handling for API errors
- JSON response parsing and Pydantic validation
- RateLimitedLLMClient with rate limiting
- Circuit breaker functionality
- Concurrent request limiting
- E2E tests with real OpenAI API (marked with @pytest.mark.e2e)

E2E Tests:
- Real API tests are automatically skipped unless LLM_API_KEY is set to a real key
- Run with: pytest -m e2e (requires real API key)
- Skip with: pytest -m "not e2e"
- Set LLM_API_KEY="sk-..." to enable E2E tests
"""

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from circuitbreaker import CircuitBreakerError
from tenacity import RetryError
import openai

from src.words.infrastructure.llm_client import LLMClient, RateLimitedLLMClient


# ============================================================================
# E2E Test Helpers (for tests that use real OpenAI API)
# ============================================================================

def _has_real_api_key() -> bool:
    """
    Check if a real OpenAI API key is available for e2e testing.

    Returns True only if LLM_API_KEY is set to a real OpenAI key
    (starts with 'sk-'), not the test key from conftest.py.
    """
    env_key = os.getenv("LLM_API_KEY")
    return bool(
        env_key and
        env_key.strip() and
        env_key.startswith("sk-") and
        env_key != "test_api_key_12345"
    )


def _get_real_api_key() -> str:
    """
    Get the real API key for e2e testing.

    Raises:
        ValueError: If no real API key is available
    """
    env_key = os.getenv("LLM_API_KEY")
    if (env_key and env_key.strip() and
        env_key.startswith("sk-") and
        env_key != "test_api_key_12345"):
        return env_key

    raise ValueError(
        "No valid OpenAI API key available for e2e tests. "
        "Set LLM_API_KEY environment variable to a real API key (sk-...) to run e2e tests."
    )


# Skip condition for e2e tests
skip_if_no_real_api = pytest.mark.skipif(
    not _has_real_api_key(),
    reason="Real OpenAI API key not available. Set LLM_API_KEY to a real API key (sk-...) to run e2e tests."
)


@pytest.fixture
def mock_openai_client():
    """Fixture to create a mocked AsyncOpenAI client."""
    with patch('src.words.infrastructure.llm_client.AsyncOpenAI') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock, mock_instance


class TestLLMClientInitialization:
    """Tests for LLMClient initialization."""

    def test_client_initialization(self, mock_openai_client):
        """Test that LLMClient initializes with required parameters."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key", model="gpt-4o-mini")

        assert client.model == "gpt-4o-mini"
        assert client.client is not None
        mock_openai.assert_called_once_with(api_key="test_key")

    def test_client_default_model(self, mock_openai_client):
        """Test that LLMClient uses default model when not specified."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        assert client.model == "gpt-4o-mini"

    def test_client_custom_model(self, mock_openai_client):
        """Test that LLMClient can use custom model."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key", model="gpt-4")

        assert client.model == "gpt-4"


class TestTranslateWord:
    """Tests for translate_word method."""

    @pytest.mark.asyncio
    async def test_translate_word_success(self, mock_openai_client):
        """Test successful word translation."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        # Mock response
        mock_response = {
            "word": "hello",
            "translations": ["привет", "здравствуй"],
            "examples": [
                {"source": "Hello, how are you?", "target": "Привет, как дела?"}
            ],
            "word_forms": {"plural": "hellos"}
        }

        # Mock OpenAI client
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        result = await client.translate_word("hello", "English", "Russian")

        assert result == mock_response
        assert result["word"] == "hello"
        assert "привет" in result["translations"]

    @pytest.mark.asyncio
    async def test_translate_word_api_call_parameters(self, mock_openai_client):
        """Test that translate_word calls OpenAI API with correct parameters."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key", model="gpt-4")

        mock_response = {"word": "test", "translations": ["тест"], "examples": [], "word_forms": {}}
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        await client.translate_word("test", "English", "Russian")

        # Verify API was called with correct parameters
        mock_instance.chat.completions.create.assert_called_once()
        call_kwargs = mock_instance.chat.completions.create.call_args.kwargs

        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert "language learning assistant" in call_kwargs["messages"][0]["content"]

    @pytest.mark.asyncio
    async def test_translate_word_builds_correct_prompt(self, mock_openai_client):
        """Test that translation prompt is built correctly."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        mock_response = {"word": "cat", "translations": ["кот"], "examples": [], "word_forms": {}}
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        await client.translate_word("cat", "English", "Russian")

        # Get the prompt that was sent
        call_kwargs = mock_instance.chat.completions.create.call_args.kwargs
        prompt = call_kwargs["messages"][1]["content"]

        assert "cat" in prompt
        assert "English" in prompt
        assert "Russian" in prompt
        assert "translations" in prompt
        assert "examples" in prompt
        assert "word_forms" in prompt

    @pytest.mark.asyncio
    async def test_translate_word_api_error_raises(self, mock_openai_client):
        """Test that API errors are raised after retries (wrapped in RetryError)."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        # Mock API error - create a proper openai.APIError with required arguments
        mock_request = MagicMock()
        api_error = openai.APIError("API error", request=mock_request, body=None)

        mock_instance.chat.completions.create = AsyncMock(
            side_effect=api_error
        )

        # After retries are exhausted, tenacity wraps the exception in RetryError
        with pytest.raises(RetryError):
            await client.translate_word("test", "English", "Russian")

    @pytest.mark.asyncio
    async def test_translate_word_json_decode_error_raises(self, mock_openai_client):
        """Test that JSON decode errors are raised (wrapped in RetryError)."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        # Mock invalid JSON response
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="invalid json"))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        # After retries are exhausted, tenacity wraps the exception in RetryError
        with pytest.raises(RetryError):
            await client.translate_word("test", "English", "Russian")

    @pytest.mark.asyncio
    async def test_translate_word_retries_on_failure(self, mock_openai_client):
        """Test that translate_word retries on transient failures."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        mock_response = {"word": "test", "translations": ["тест"], "examples": [], "word_forms": {}}
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]

        # Create proper APIError instances
        mock_request = MagicMock()
        api_error1 = openai.APIError("Temporary error", request=mock_request, body=None)
        api_error2 = openai.APIError("Temporary error", request=mock_request, body=None)

        # Fail twice, then succeed
        mock_instance.chat.completions.create = AsyncMock(
            side_effect=[
                api_error1,
                api_error2,
                mock_completion
            ]
        )

        result = await client.translate_word("test", "English", "Russian")

        # Should succeed after retries
        assert result == mock_response
        # Should have been called 3 times (2 failures + 1 success)
        assert mock_instance.chat.completions.create.call_count == 3


class TestValidateAnswer:
    """Tests for validate_answer method."""

    @pytest.mark.asyncio
    async def test_validate_answer_correct(self, mock_openai_client):
        """Test validation of correct answer."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        mock_response = {
            "is_correct": True,
            "comment": "Правильно!"
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        result = await client.validate_answer(
            "hello", "привет", "привет", "English", "Russian"
        )

        assert result["is_correct"] is True
        assert "comment" in result

    @pytest.mark.asyncio
    async def test_validate_answer_incorrect(self, mock_openai_client):
        """Test validation of incorrect answer."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        mock_response = {
            "is_correct": False,
            "comment": "Неправильно. Правильный ответ: привет"
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        result = await client.validate_answer(
            "hello", "привет", "хай", "English", "Russian"
        )

        assert result["is_correct"] is False
        assert "comment" in result

    @pytest.mark.asyncio
    async def test_validate_answer_api_call_parameters(self, mock_openai_client):
        """Test that validate_answer calls OpenAI API with correct parameters."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key", model="gpt-4")

        mock_response = {"is_correct": True, "comment": "Good"}
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        await client.validate_answer("hello", "привет", "привет", "English", "Russian")

        call_kwargs = mock_instance.chat.completions.create.call_args.kwargs

        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["temperature"] == 0.1  # Lower temperature for validation
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert "validator" in call_kwargs["messages"][0]["content"]

    @pytest.mark.asyncio
    async def test_validate_answer_builds_correct_prompt(self, mock_openai_client):
        """Test that validation prompt is built correctly."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        mock_response = {"is_correct": True, "comment": "Correct"}
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        await client.validate_answer("cat", "кот", "кошка", "English", "Russian")

        call_kwargs = mock_instance.chat.completions.create.call_args.kwargs
        prompt = call_kwargs["messages"][1]["content"]

        assert "cat" in prompt
        assert "кот" in prompt
        assert "кошка" in prompt
        assert "is_correct" in prompt
        assert "comment" in prompt

    @pytest.mark.asyncio
    async def test_validate_answer_api_error_raises(self, mock_openai_client):
        """Test that API errors are raised after retries (wrapped in RetryError)."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        # Create proper APIError instance
        mock_request = MagicMock()
        api_error = openai.APIError("API error", request=mock_request, body=None)

        mock_instance.chat.completions.create = AsyncMock(
            side_effect=api_error
        )

        # After retries are exhausted, tenacity wraps the exception in RetryError
        with pytest.raises(RetryError):
            await client.validate_answer("test", "тест", "тест", "English", "Russian")

    @pytest.mark.asyncio
    async def test_validate_answer_retries_on_failure(self, mock_openai_client):
        """Test that validate_answer retries on transient failures."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        mock_response = {"is_correct": True, "comment": "Good"}
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]

        # Create proper APIError instance
        mock_request = MagicMock()
        api_error = openai.APIError("Temporary error", request=mock_request, body=None)

        # Fail once, then succeed
        mock_instance.chat.completions.create = AsyncMock(
            side_effect=[
                api_error,
                mock_completion
            ]
        )

        result = await client.validate_answer("test", "тест", "тест", "English", "Russian")

        assert result == mock_response
        assert mock_instance.chat.completions.create.call_count == 2


class TestRateLimitedLLMClient:
    """Tests for RateLimitedLLMClient."""

    def test_rate_limited_client_initialization(self, mock_openai_client):
        """Test that RateLimitedLLMClient initializes correctly."""
        mock_openai, mock_instance = mock_openai_client
        client = RateLimitedLLMClient(
            api_key="test_key",
            max_concurrent=5,
            requests_per_minute=1000
        )

        assert client.model == "gpt-4o-mini"
        assert client.semaphore._value == 5
        assert client.rate_limiter.max_rate == 1000

    def test_rate_limited_client_default_limits(self, mock_openai_client):
        """Test that RateLimitedLLMClient uses default limits."""
        mock_openai, mock_instance = mock_openai_client
        client = RateLimitedLLMClient(api_key="test_key")

        assert client.semaphore._value == 10  # default max_concurrent
        assert client.rate_limiter.max_rate == 2500  # default requests_per_minute

    @pytest.mark.asyncio
    async def test_rate_limited_translate_with_rate_limiter(self, mock_openai_client):
        """Test that translate_word uses rate limiter."""
        mock_openai, mock_instance = mock_openai_client
        client = RateLimitedLLMClient(api_key="test_key", requests_per_minute=100)

        mock_response = {"word": "test", "translations": ["тест"], "examples": [], "word_forms": {}}
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        # Mock the rate limiter and semaphore
        rate_limiter_mock = AsyncMock()
        semaphore_mock = AsyncMock()

        with patch.object(client, 'rate_limiter', rate_limiter_mock), \
             patch.object(client, 'semaphore', semaphore_mock):

            await client.translate_word("test", "English", "Russian")

            # Verify rate limiter was used
            rate_limiter_mock.__aenter__.assert_called_once()
            rate_limiter_mock.__aexit__.assert_called_once()

            # Verify semaphore was used
            semaphore_mock.__aenter__.assert_called_once()
            semaphore_mock.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limited_validate_with_rate_limiter(self, mock_openai_client):
        """Test that validate_answer uses rate limiter."""
        mock_openai, mock_instance = mock_openai_client
        client = RateLimitedLLMClient(api_key="test_key", requests_per_minute=100)

        mock_response = {"is_correct": True, "comment": "Good"}
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        # Mock the rate limiter and semaphore
        rate_limiter_mock = AsyncMock()
        semaphore_mock = AsyncMock()

        with patch.object(client, 'rate_limiter', rate_limiter_mock), \
             patch.object(client, 'semaphore', semaphore_mock):

            await client.validate_answer("test", "тест", "тест", "English", "Russian")

            # Verify rate limiter was used
            rate_limiter_mock.__aenter__.assert_called_once()
            rate_limiter_mock.__aexit__.assert_called_once()

            # Verify semaphore was used
            semaphore_mock.__aenter__.assert_called_once()
            semaphore_mock.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_requests_limited(self, mock_openai_client):
        """Test that concurrent requests are limited by semaphore."""
        mock_openai, mock_instance = mock_openai_client
        client = RateLimitedLLMClient(api_key="test_key", max_concurrent=2)

        mock_response = {"word": "test", "translations": ["тест"], "examples": [], "word_forms": {}}
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        # Initial semaphore value should be 2
        assert client.semaphore._value == 2

        # After acquiring once, should be 1
        async with client.semaphore:
            assert client.semaphore._value == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_on_api_error(self, mock_openai_client):
        """Test that circuit breaker works on API errors."""
        mock_openai, mock_instance = mock_openai_client
        client = RateLimitedLLMClient(api_key="test_key")

        # Create proper APIError instance
        mock_request = MagicMock()
        api_error = openai.APIError("API error", request=mock_request, body=None)

        # Mock API error
        mock_instance.chat.completions.create = AsyncMock(
            side_effect=api_error
        )

        # The circuit breaker should allow the error to propagate (wrapped in RetryError after retries)
        with pytest.raises(RetryError):
            await client.translate_word("test", "English", "Russian")


class TestPromptBuilding:
    """Tests for prompt building methods."""

    def test_build_translation_prompt_structure(self, mock_openai_client):
        """Test that translation prompt has correct structure."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        prompt = client._build_translation_prompt("hello", "English", "Russian")

        assert "hello" in prompt
        assert "English" in prompt
        assert "Russian" in prompt
        assert "translations" in prompt.lower()
        assert "examples" in prompt.lower()
        assert "word_forms" in prompt.lower()
        assert "JSON" in prompt or "json" in prompt

    def test_build_validation_prompt_structure(self, mock_openai_client):
        """Test that validation prompt has correct structure."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        prompt = client._build_validation_prompt(
            "hello", "привет", "хай", "English", "Russian"
        )

        assert "hello" in prompt
        assert "привет" in prompt
        assert "хай" in prompt
        assert "is_correct" in prompt
        assert "comment" in prompt
        assert "JSON" in prompt or "json" in prompt


class TestInputValidation:
    """Tests for input validation edge cases."""

    @pytest.mark.asyncio
    async def test_translate_word_empty_word(self, mock_openai_client):
        """Test that translate_word raises ValueError for empty word."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        with pytest.raises(ValueError, match="Word cannot be empty"):
            await client.translate_word("", "English", "Russian")

    @pytest.mark.asyncio
    async def test_translate_word_whitespace_word(self, mock_openai_client):
        """Test that translate_word raises ValueError for whitespace-only word."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        with pytest.raises(ValueError, match="Word cannot be empty"):
            await client.translate_word("   ", "English", "Russian")

    @pytest.mark.asyncio
    async def test_translate_word_too_long(self, mock_openai_client):
        """Test that translate_word raises ValueError for word exceeding 100 chars."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        long_word = "a" * 101

        with pytest.raises(ValueError, match="Word too long.*Maximum is 100 characters"):
            await client.translate_word(long_word, "English", "Russian")

    @pytest.mark.asyncio
    async def test_translate_word_empty_source_lang(self, mock_openai_client):
        """Test that translate_word raises ValueError for empty source language."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        with pytest.raises(ValueError, match="Source language cannot be empty"):
            await client.translate_word("hello", "", "Russian")

    @pytest.mark.asyncio
    async def test_translate_word_empty_target_lang(self, mock_openai_client):
        """Test that translate_word raises ValueError for empty target language."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        with pytest.raises(ValueError, match="Target language cannot be empty"):
            await client.translate_word("hello", "English", "")

    @pytest.mark.asyncio
    async def test_validate_answer_empty_question(self, mock_openai_client):
        """Test that validate_answer raises ValueError for empty question."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        with pytest.raises(ValueError, match="Question cannot be empty"):
            await client.validate_answer("", "привет", "привет", "English", "Russian")

    @pytest.mark.asyncio
    async def test_validate_answer_empty_expected(self, mock_openai_client):
        """Test that validate_answer raises ValueError for empty expected answer."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        with pytest.raises(ValueError, match="Expected answer cannot be empty"):
            await client.validate_answer("hello", "", "привет", "English", "Russian")

    @pytest.mark.asyncio
    async def test_validate_answer_empty_user_answer(self, mock_openai_client):
        """Test that validate_answer raises ValueError for empty user answer."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        with pytest.raises(ValueError, match="User answer cannot be empty"):
            await client.validate_answer("hello", "привет", "", "English", "Russian")

    @pytest.mark.asyncio
    async def test_validate_answer_too_long(self, mock_openai_client):
        """Test that validate_answer raises ValueError for inputs exceeding 100 chars."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        long_text = "a" * 101

        with pytest.raises(ValueError, match="Question too long.*Maximum is 100 characters"):
            await client.validate_answer(long_text, "test", "test", "English", "Russian")

        with pytest.raises(ValueError, match="Expected answer too long.*Maximum is 100 characters"):
            await client.validate_answer("test", long_text, "test", "English", "Russian")

        with pytest.raises(ValueError, match="User answer too long.*Maximum is 100 characters"):
            await client.validate_answer("test", "test", long_text, "English", "Russian")


class TestResponseValidation:
    """Tests for response validation with Pydantic models."""

    @pytest.mark.asyncio
    async def test_translate_word_missing_required_field(self, mock_openai_client):
        """Test that translate_word raises ValidationError when response is missing required fields."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        # Response missing 'translations' field
        mock_response = {
            "word": "hello",
            "examples": [],
            "word_forms": {}
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        # Import ValidationError from pydantic
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            await client.translate_word("hello", "English", "Russian")

    @pytest.mark.asyncio
    async def test_translate_word_empty_translations_list(self, mock_openai_client):
        """Test that translate_word raises ValidationError when translations list is empty."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        # Response with empty translations list (should have at least 1)
        mock_response = {
            "word": "hello",
            "translations": [],  # Empty list not allowed
            "examples": [],
            "word_forms": {}
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            await client.translate_word("hello", "English", "Russian")

    @pytest.mark.asyncio
    async def test_validate_answer_missing_is_correct(self, mock_openai_client):
        """Test that validate_answer raises ValidationError when response is missing is_correct."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        # Response missing 'is_correct' field
        mock_response = {
            "comment": "Good answer"
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            await client.validate_answer("hello", "привет", "привет", "English", "Russian")

    @pytest.mark.asyncio
    async def test_validate_answer_empty_comment(self, mock_openai_client):
        """Test that validate_answer raises ValidationError when comment is empty."""
        mock_openai, mock_instance = mock_openai_client
        client = LLMClient(api_key="test_key")

        # Response with empty comment (should have at least 1 char)
        mock_response = {
            "is_correct": True,
            "comment": ""  # Empty comment not allowed
        }

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            await client.validate_answer("hello", "привет", "привет", "English", "Russian")


class TestModuleExports:
    """Tests for module-level exports."""

    def test_module_exports_llm_client(self):
        """Test that module exports LLMClient."""
        from src.words.infrastructure import LLMClient
        assert LLMClient is not None

    def test_module_exports_rate_limited_llm_client(self):
        """Test that module exports RateLimitedLLMClient."""
        from src.words.infrastructure import RateLimitedLLMClient
        assert RateLimitedLLMClient is not None


class TestLLMClientRealAPI:
    """
    End-to-end tests using real OpenAI API.

    IMPORTANT:
    - These tests make actual API calls which cost money
    - Tests are automatically skipped if no real API key is available
    - Set LLM_API_KEY to a real OpenAI API key (sk-...) to run these tests
    - Run with: pytest -m e2e
    - Skip with: pytest -m "not e2e"

    Test Philosophy:
    - Keep tests minimal (2-4 tests max)
    - Test only critical integration points that mocks can't verify
    - Focus on response structure and basic functionality
    - Use simple, common words to ensure reliability
    """

    @skip_if_no_real_api
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_translate_word_english_to_russian_real_api(self):
        """
        E2E test: Verify translate_word works with real OpenAI API for English to Russian.

        This test validates:
        - Real API connection works
        - Response structure matches expected schema
        - Translation returns proper data types
        - All required fields are present
        - Translation quality is reasonable (basic sanity check)
        """
        # Use real API key and client
        api_key = _get_real_api_key()
        client = LLMClient(api_key=api_key, model="gpt-4o-mini")

        # Translate a simple, common word
        result = await client.translate_word(
            word="hello",
            source_lang="English",
            target_lang="Russian"
        )

        # Verify response structure
        assert isinstance(result, dict), "Result should be a dictionary"

        # Verify all required fields are present
        assert "word" in result, "Response must contain 'word' field"
        assert "translations" in result, "Response must contain 'translations' field"
        assert "examples" in result, "Response must contain 'examples' field"
        assert "word_forms" in result, "Response must contain 'word_forms' field"

        # Verify field types
        assert isinstance(result["word"], str), "'word' must be a string"
        assert isinstance(result["translations"], list), "'translations' must be a list"
        assert isinstance(result["examples"], list), "'examples' must be a list"
        assert isinstance(result["word_forms"], dict), "'word_forms' must be a dict"

        # Verify data quality
        assert result["word"] == "hello", "Word should match input"
        assert len(result["translations"]) > 0, "Should have at least one translation"
        assert "привет" in result["translations"] or "здравствуй" in result["translations"], \
            "Should contain common Russian translation for 'hello'"

        # Verify examples structure if present
        if result["examples"]:
            example = result["examples"][0]
            assert isinstance(example, dict), "Example must be a dict"
            assert "source" in example, "Example must have 'source' field"
            assert "target" in example, "Example must have 'target' field"
            assert isinstance(example["source"], str), "Example source must be string"
            assert isinstance(example["target"], str), "Example target must be string"
            assert len(example["source"]) > 0, "Example source must not be empty"
            assert len(example["target"]) > 0, "Example target must not be empty"

        print(f"\n✓ E2E Test passed: translate_word(hello, EN→RU)")
        print(f"  Translations: {result['translations'][:3]}")
        print(f"  Examples: {len(result['examples'])} provided")
        print(f"  Word forms: {len(result['word_forms'])} forms")

    @skip_if_no_real_api
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_translate_word_russian_to_english_real_api(self):
        """
        E2E test: Verify translate_word works with real OpenAI API for Russian to English.

        This test validates:
        - Bidirectional translation works
        - Cyrillic characters are handled correctly
        - Response structure is consistent across language pairs
        """
        api_key = _get_real_api_key()
        client = LLMClient(api_key=api_key, model="gpt-4o-mini")

        # Translate a simple Russian word
        result = await client.translate_word(
            word="дом",
            source_lang="Russian",
            target_lang="English"
        )

        # Verify response structure (same as English→Russian)
        assert isinstance(result, dict)
        assert "word" in result
        assert "translations" in result
        assert "examples" in result
        assert "word_forms" in result

        # Verify field types
        assert isinstance(result["word"], str)
        assert isinstance(result["translations"], list)
        assert isinstance(result["examples"], list)
        assert isinstance(result["word_forms"], dict)

        # Verify data quality
        assert result["word"] == "дом", "Word should match input (Cyrillic)"
        assert len(result["translations"]) > 0, "Should have at least one translation"
        assert "house" in result["translations"] or "home" in result["translations"], \
            "Should contain common English translation for 'дом'"

        print(f"\n✓ E2E Test passed: translate_word(дом, RU→EN)")
        print(f"  Translations: {result['translations'][:3]}")
        print(f"  Examples: {len(result['examples'])} provided")

    @skip_if_no_real_api
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_translate_word_retry_logic_works_with_real_api(self):
        """
        E2E test: Verify that retry logic works with real API.

        This test validates that the client can successfully complete
        a request even if configured with retry capabilities. We can't
        easily trigger a real retry without intentionally causing errors,
        but we can verify the retry-enabled code path works.
        """
        api_key = _get_real_api_key()
        client = LLMClient(api_key=api_key, model="gpt-4o-mini")

        # Make a call that should succeed on first try
        # The retry logic is in place but won't be triggered
        result = await client.translate_word(
            word="cat",
            source_lang="English",
            target_lang="Russian"
        )

        # Verify basic structure
        assert isinstance(result, dict)
        assert result["word"] == "cat"
        assert len(result["translations"]) > 0

        # Verify at least one common translation is present
        translations_lower = [t.lower() for t in result["translations"]]
        assert any("кот" in t or "кошка" in t for t in translations_lower), \
            "Should contain common Russian translation for 'cat'"

        print(f"\n✓ E2E Test passed: translate_word with retry logic (cat, EN→RU)")
        print(f"  Translations: {result['translations'][:3]}")
