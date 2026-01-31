"""
LLM Client infrastructure for the Words application.

This module provides OpenAI-based LLM clients for translation and validation
with comprehensive error handling, rate limiting, and circuit breaker protection.
"""

import json
import logging
from asyncio import Semaphore
from typing import Optional

import openai
from aiolimiter import AsyncLimiter
from circuitbreaker import circuit
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


# Pydantic models for response validation
class ExampleSentence(BaseModel):
    """Model for example sentence pair."""
    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)


class TranslationResponse(BaseModel):
    """Model for translation API response validation."""
    word: str = Field(..., min_length=1)
    translations: list[str] = Field(..., min_length=1)
    examples: list[ExampleSentence]
    # word_forms allows None values because not all forms apply to all words
    # (e.g., nouns don't have comparative, adjectives don't have plural)
    # Some providers return nested objects (e.g., verb_conjugations), so allow dict values.
    word_forms: dict[str, Optional[str] | dict]


class ValidationResponse(BaseModel):
    """Model for validation API response validation."""
    is_correct: bool
    comment: str = Field(..., min_length=1)


class LLMClient:
    """
    Base LLM client for OpenAI API integration.

    Provides translation and validation methods with automatic retry logic
    and comprehensive error handling.

    Features:
    - Async OpenAI client integration
    - Exponential backoff retry logic
    - JSON response parsing
    - Structured error handling
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize LLM client.

        Args:
            api_key: OpenAI API key
            model: OpenAI model to use (default: gpt-4o-mini)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        logger.info(f"LLMClient initialized with model: {model}")

    async def translate_word(
        self,
        word: str,
        source_lang: str,
        target_lang: str
    ) -> dict:
        """
        Get translations, examples, and word forms for a word.

        Args:
            word: Word to translate (max 100 characters)
            source_lang: Source language (e.g., "English", "Russian")
            target_lang: Target language (e.g., "English", "Russian")

        Returns:
            Dictionary containing:
                - word: Original word
                - translations: List of translations
                - examples: List of example sentences with translations
                - word_forms: Dictionary of word forms (plural, past, etc.)

        Raises:
            ValueError: If input validation fails
            openai.APIError: If OpenAI API call fails after retries
            json.JSONDecodeError: If response parsing fails
            ValidationError: If response doesn't match expected schema
        """
        # Input validation (before retry logic)
        if not word or not word.strip():
            raise ValueError("Word cannot be empty or whitespace")
        if len(word) > 100:
            raise ValueError(f"Word too long ({len(word)} chars). Maximum is 100 characters")
        if not source_lang or not source_lang.strip():
            raise ValueError("Source language cannot be empty")
        if not target_lang or not target_lang.strip():
            raise ValueError("Target language cannot be empty")

        return await self._translate_word_with_retry(word, source_lang, target_lang)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIError, json.JSONDecodeError))
    )
    async def _translate_word_with_retry(
        self,
        word: str,
        source_lang: str,
        target_lang: str
    ) -> dict:
        """
        Internal method with retry logic for translation.

        This is separated from translate_word so that input validation
        happens before retry logic is applied.
        Only retries on transient API/JSON errors, not on ValidationError.
        """
        prompt = self._build_translation_prompt(word, source_lang, target_lang)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a language learning assistant."},
                    {"role": "user", "content": prompt}
                ],
                # Temperature 0.3: Balance between consistency and creativity
                # Low enough for reliable translations, high enough for natural examples
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            response_content = response.choices[0].message.content
            result = json.loads(response_content)

            # Validate response structure with Pydantic
            validated = TranslationResponse(**result)

            logger.info(
                f"Translation successful for word: {word} "
                f"({source_lang} -> {target_lang})"
            )
            return validated.model_dump()

        except openai.APIError as e:
            logger.error(
                f"OpenAI API error during translation: {e}",
                extra={"word": word, "source_lang": source_lang, "target_lang": target_lang}
            )
            raise
        except json.JSONDecodeError as e:
            # Include first 500 chars of raw response for debugging
            raw_preview = response_content[:500] if response_content else "None"
            logger.error(
                f"Failed to parse LLM response as JSON: {e}",
                extra={
                    "word": word,
                    "raw_response_preview": raw_preview
                }
            )
            raise
        except ValidationError as e:
            # Log validation errors with response content
            raw_preview = response_content[:500] if response_content else "None"
            logger.error(
                f"LLM response failed validation: {e}",
                extra={
                    "word": word,
                    "raw_response_preview": raw_preview,
                    "validation_errors": e.errors()
                }
            )
            raise

    def _build_translation_prompt(
        self,
        word: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """
        Build prompt for translation request.

        Args:
            word: Word to translate
            source_lang: Source language
            target_lang: Target language

        Returns:
            Formatted prompt string
        """
        return f"""
Translate the word "{word}" from {source_lang} to {target_lang}.

Provide the response in JSON format:
{{
    "word": "{word}",
    "translations": ["translation1", "translation2", ...],
    "examples": [
        {{"source": "example in {source_lang}", "target": "example in {target_lang}"}},
        ...
    ],
    "word_forms": {{
        "plural": "...",
        "past": "...",
        "comparative": "...",
        ...
    }}
}}

Include:
- All common translations/meanings
- 2-3 example sentences with translations
- Relevant word forms (plural, verb conjugations, etc.)
"""

    async def validate_answer(
        self,
        question: str,
        expected_answer: str,
        user_answer: str,
        source_lang: str,
        target_lang: str
    ) -> dict:
        """
        Validate user's answer using LLM with fuzzy matching.

        Args:
            question: Original question/word (max 100 characters)
            expected_answer: Expected correct answer (max 100 characters)
            user_answer: User's provided answer (max 100 characters)
            source_lang: Source language
            target_lang: Target language

        Returns:
            Dictionary containing:
                - is_correct: Boolean indicating if answer is correct
                - comment: Explanation for the user in source_lang

        Raises:
            ValueError: If input validation fails
            openai.APIError: If OpenAI API call fails after retries
            json.JSONDecodeError: If response parsing fails
            ValidationError: If response doesn't match expected schema
        """
        # Input validation (before retry logic)
        if not question or not question.strip():
            raise ValueError("Question cannot be empty or whitespace")
        if len(question) > 100:
            raise ValueError(f"Question too long ({len(question)} chars). Maximum is 100 characters")
        if not expected_answer or not expected_answer.strip():
            raise ValueError("Expected answer cannot be empty or whitespace")
        if len(expected_answer) > 100:
            raise ValueError(f"Expected answer too long ({len(expected_answer)} chars). Maximum is 100 characters")
        if not user_answer or not user_answer.strip():
            raise ValueError("User answer cannot be empty or whitespace")
        if len(user_answer) > 100:
            raise ValueError(f"User answer too long ({len(user_answer)} chars). Maximum is 100 characters")
        if not source_lang or not source_lang.strip():
            raise ValueError("Source language cannot be empty")
        if not target_lang or not target_lang.strip():
            raise ValueError("Target language cannot be empty")

        return await self._validate_answer_with_retry(
            question, expected_answer, user_answer, source_lang, target_lang
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIError, json.JSONDecodeError))
    )
    async def _validate_answer_with_retry(
        self,
        question: str,
        expected_answer: str,
        user_answer: str,
        source_lang: str,
        target_lang: str
    ) -> dict:
        """
        Internal method with retry logic for answer validation.

        This is separated from validate_answer so that input validation
        happens before retry logic is applied.
        Only retries on transient API/JSON errors, not on ValidationError.
        """
        prompt = self._build_validation_prompt(
            question, expected_answer, user_answer, source_lang, target_lang
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a language learning validator."},
                    {"role": "user", "content": prompt}
                ],
                # Temperature 0.1: Deterministic evaluation for consistency
                # Very low temperature ensures consistent validation decisions
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            response_content = response.choices[0].message.content
            result = json.loads(response_content)

            # Validate response structure with Pydantic
            validated = ValidationResponse(**result)

            logger.info(
                f"Validation complete for question: {question}, "
                f"result: {'correct' if validated.is_correct else 'incorrect'}"
            )
            return validated.model_dump()

        except openai.APIError as e:
            logger.error(
                f"OpenAI API error during validation: {e}",
                extra={
                    "question": question,
                    "expected": expected_answer,
                    "user_answer": user_answer
                }
            )
            raise
        except json.JSONDecodeError as e:
            # Include first 500 chars of raw response for debugging
            raw_preview = response_content[:500] if response_content else "None"
            logger.error(
                f"Failed to parse validation response as JSON: {e}",
                extra={
                    "question": question,
                    "raw_response_preview": raw_preview
                }
            )
            raise
        except ValidationError as e:
            # Log validation errors with response content
            raw_preview = response_content[:500] if response_content else "None"
            logger.error(
                f"Validation response failed schema validation: {e}",
                extra={
                    "question": question,
                    "raw_response_preview": raw_preview,
                    "validation_errors": e.errors()
                }
            )
            raise

    def _build_validation_prompt(
        self,
        question: str,
        expected: str,
        user: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """
        Build prompt for answer validation.

        Args:
            question: Original question/word
            expected: Expected correct answer
            user: User's provided answer
            source_lang: Source language
            target_lang: Target language

        Returns:
            Formatted prompt string
        """
        return f"""
Question: Translate "{question}" from {source_lang} to {target_lang}
Expected answer: {expected}
User's answer: {user}

Evaluate if the user's answer is correct. Consider:
- Synonyms
- Alternative word forms
- Common variations
- Context appropriateness

Respond in JSON:
{{
    "is_correct": true/false,
    "comment": "Explanation for the user in {source_lang}"
}}

Comment examples:
- If correct: "Правильно! Также можно сказать '{expected}'."
- If synonym: "Ответ засчитывается, но обычно используется '{expected}'."
- If wrong: "Неправильно. '{user}' означает '...', а правильный ответ: '{expected}'."
"""


class RateLimitedLLMClient(LLMClient):
    """
    LLM Client with comprehensive rate limiting and circuit breaker protection.

    Features:
    - Token bucket rate limiting (prevents API quota exhaustion)
    - Semaphore for concurrent request limiting
    - Circuit breaker for fault tolerance
    - Automatic recovery after failures

    The circuit breaker opens after 5 consecutive failures and tries to recover
    after 60 seconds. Rate limiting uses a token bucket algorithm to ensure
    we stay within OpenAI's API limits (default: 2500 requests/minute for safety).
    """

    def __init__(
        self,
        *args,
        max_concurrent: int = 10,
        requests_per_minute: int = 2500,  # Safety margin: 3000 - 500
        **kwargs
    ):
        """
        Initialize rate-limited LLM client.

        Args:
            *args: Positional arguments passed to LLMClient
            max_concurrent: Maximum concurrent requests (default: 10)
            requests_per_minute: Maximum requests per minute (default: 2500)
                OpenAI gpt-4o-mini: 3000 req/min, we use 2500 for safety margin
            **kwargs: Keyword arguments passed to LLMClient
        """
        super().__init__(*args, **kwargs)

        # Concurrent request limiter
        self.semaphore = Semaphore(max_concurrent)

        # Token bucket rate limiter
        # OpenAI gpt-4o-mini: 3000 req/min, use 2500 for safety margin
        self.rate_limiter = AsyncLimiter(
            max_rate=requests_per_minute,
            time_period=60
        )

        logger.info(
            f"RateLimitedLLMClient initialized: "
            f"max_concurrent={max_concurrent}, "
            f"requests_per_minute={requests_per_minute}"
        )

    @circuit(
        failure_threshold=5,      # Open circuit after 5 consecutive failures
        recovery_timeout=60,      # Try to close circuit after 60 seconds
        expected_exception=openai.APIError
    )
    async def _call_with_circuit_breaker(self, func, *args, **kwargs):
        """
        Execute LLM call with circuit breaker protection.

        Args:
            func: Function to call (translate_word or validate_answer)
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result from the function call

        Raises:
            openai.APIError: If the API call fails
            CircuitBreakerError: If circuit is open
        """
        return await func(*args, **kwargs)

    async def translate_word(self, *args, **kwargs):
        """
        Translate word with rate limiting and circuit breaker.

        Flow:
        1. Wait for rate limiter slot
        2. Acquire semaphore (max concurrent)
        3. Execute with circuit breaker protection
        4. Return result or raise exception

        Args:
            *args: Positional arguments passed to LLMClient.translate_word
            **kwargs: Keyword arguments passed to LLMClient.translate_word

        Returns:
            Translation result dictionary

        Raises:
            openai.APIError: If API call fails after retries
            CircuitBreakerError: If circuit breaker is open
        """
        async with self.rate_limiter:
            async with self.semaphore:
                try:
                    return await self._call_with_circuit_breaker(
                        super().translate_word, *args, **kwargs
                    )
                except openai.APIError as e:
                    logger.error(
                        "LLM API error during translation",
                        extra={
                            "operation": "translate",
                            "error": str(e)
                        }
                    )
                    raise

    async def validate_answer(self, *args, **kwargs):
        """
        Validate answer with rate limiting and circuit breaker.

        Higher priority than translation (validation is user-facing).

        Flow:
        1. Wait for rate limiter slot
        2. Acquire semaphore (max concurrent)
        3. Execute with circuit breaker protection
        4. Return result or raise exception

        Args:
            *args: Positional arguments passed to LLMClient.validate_answer
            **kwargs: Keyword arguments passed to LLMClient.validate_answer

        Returns:
            Validation result dictionary

        Raises:
            openai.APIError: If API call fails after retries
            CircuitBreakerError: If circuit breaker is open
        """
        async with self.rate_limiter:
            async with self.semaphore:
                try:
                    return await self._call_with_circuit_breaker(
                        super().validate_answer, *args, **kwargs
                    )
                except openai.APIError as e:
                    logger.error(
                        "LLM API error during validation",
                        extra={
                            "operation": "validate",
                            "error": str(e)
                        }
                    )
                    raise
