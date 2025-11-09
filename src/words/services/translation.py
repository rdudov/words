"""
Translation service for word translations and answer validation.

This module provides the TranslationService class that orchestrates
LLM-based translation and validation with caching for optimal performance.

The service implements a cache-first strategy to minimize API calls and
improve response times. All LLM interactions are logged for monitoring
and debugging purposes.

Key Features:
- Word translation with examples and word forms
- Answer validation with fuzzy matching
- Cache-first strategy to reduce API costs
- Comprehensive error handling and logging
- Graceful degradation on failures
"""

import logging
from src.words.infrastructure.llm_client import LLMClient
from src.words.repositories.cache import CacheRepository

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Service for word translations and answer validation using LLM.

    This service combines LLM client and cache repository to provide
    efficient translation and validation capabilities with caching.

    Attributes:
        llm_client: LLM client for API calls
        cache_repo: Repository for caching LLM results

    Example:
        >>> translation_service = TranslationService(llm_client, cache_repo)
        >>> # Translate a word
        >>> result = await translation_service.translate_word(
        ...     word="hello",
        ...     source_lang="en",
        ...     target_lang="ru"
        ... )
        >>> print(result["translations"])  # ["привет", "здравствуй"]
        >>> # Validate an answer
        >>> is_correct, comment = await translation_service.validate_answer_with_llm(
        ...     question="hello",
        ...     expected="привет",
        ...     user_answer="превет",
        ...     source_lang="en",
        ...     target_lang="ru",
        ...     word_id=123,
        ...     direction="forward"
        ... )
    """

    def __init__(
        self,
        llm_client: LLMClient,
        cache_repo: CacheRepository
    ):
        """
        Initialize translation service.

        Args:
            llm_client: LLM client for translation and validation
            cache_repo: Repository for caching LLM results
        """
        self.llm_client = llm_client
        self.cache_repo = cache_repo

    async def translate_word(
        self,
        word: str,
        source_lang: str,
        target_lang: str
    ) -> dict:
        """
        Get word translation with caching.

        Uses cache-first strategy: checks cache before calling LLM.
        Cache entries never expire for translations.

        Args:
            word: Word to translate
            source_lang: Source language (e.g., "en", "ru")
            target_lang: Target language (e.g., "en", "ru")

        Returns:
            Dictionary containing:
                - word: Original word
                - translations: List of translations
                - examples: List of example sentences with translations
                - word_forms: Dictionary of word forms (plural, past, etc.)

        Raises:
            Exception: If LLM call fails after retries

        Example:
            >>> result = await translation_service.translate_word(
            ...     word="hello",
            ...     source_lang="en",
            ...     target_lang="ru"
            ... )
            >>> print(result)
            {
                "word": "hello",
                "translations": ["привет", "здравствуй"],
                "examples": [
                    {"source": "Hello, world!", "target": "Привет, мир!"}
                ],
                "word_forms": {"plural": "hellos"}
            }
        """
        # Check cache first
        cached = await self.cache_repo.get_translation(
            word, source_lang, target_lang
        )

        if cached:
            logger.debug(
                "Translation cache hit: word='%s', source=%s, target=%s",
                word,
                source_lang,
                target_lang
            )
            return cached

        # Call LLM
        logger.info(
            "Translation LLM call: word='%s', source=%s, target=%s",
            word,
            source_lang,
            target_lang
        )

        try:
            result = await self.llm_client.translate_word(
                word, source_lang, target_lang
            )

            # Cache result (never expires)
            await self.cache_repo.set_translation(
                word, source_lang, target_lang, result
            )

            return result

        except Exception as e:
            logger.error(
                "Translation failed: word='%s', error=%s",
                word,
                str(e)
            )
            raise

    async def validate_answer_with_llm(
        self,
        question: str,
        expected: str,
        user_answer: str,
        source_lang: str,
        target_lang: str,
        word_id: int,
        direction: str
    ) -> tuple[bool, str]:
        """
        Validate answer using LLM with caching.

        Uses cache-first strategy: checks cache before calling LLM.
        Provides graceful degradation on errors.

        Args:
            question: Original question/word
            expected: Expected correct answer
            user_answer: User's provided answer
            source_lang: Source language (e.g., "en", "ru")
            target_lang: Target language (e.g., "en", "ru")
            word_id: ID of the word being validated
            direction: Validation direction ("forward" or "backward")

        Returns:
            Tuple of (is_correct, comment):
                - is_correct: Boolean indicating if answer is correct
                - comment: Explanation for the user

        Example:
            >>> is_correct, comment = await translation_service.validate_answer_with_llm(
            ...     question="hello",
            ...     expected="привет",
            ...     user_answer="превет",
            ...     source_lang="en",
            ...     target_lang="ru",
            ...     word_id=123,
            ...     direction="forward"
            ... )
            >>> print(f"Correct: {is_correct}")  # False
            >>> print(comment)  # "Неправильно. Правильный ответ: привет"
        """
        # Check cache first
        cached = await self.cache_repo.get_validation(
            word_id, direction, expected, user_answer
        )

        if cached:
            logger.debug(
                "Validation cache hit: word_id=%d, user_answer='%s'",
                word_id,
                user_answer
            )
            return cached

        # Call LLM
        logger.info(
            "Validation LLM call: word_id=%d, expected='%s', user_answer='%s'",
            word_id,
            expected,
            user_answer
        )

        try:
            result = await self.llm_client.validate_answer(
                question, expected, user_answer, source_lang, target_lang
            )

            is_correct = result["is_correct"]
            comment = result["comment"]

            # Cache result
            await self.cache_repo.set_validation(
                word_id, direction, expected, user_answer, is_correct, comment
            )

            return (is_correct, comment)

        except Exception as e:
            logger.error(
                "Validation failed: word_id=%d, error=%s",
                word_id,
                str(e)
            )
            # Fallback: reject answer
            return (False, "Validation service unavailable. Please try again.")
