"""
Cache repository for managing LLM result caching.

This module provides the CacheRepository class for:
- Caching translation API responses to reduce external API calls
- Caching LLM validation results to speed up repeated answers
- Handling cache expiration and upsert logic
"""

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from src.words.models.cache import CachedTranslation, CachedValidation


class CacheRepository:
    """
    Cache management repository for LLM results.

    Provides methods for caching and retrieving:
    - Translation results from external APIs
    - Validation results from LLM API calls

    This reduces API costs and improves response times by caching
    frequently requested data.

    Attributes:
        session: AsyncSession for database operations

    Example:
        >>> cache_repo = CacheRepository(session)
        >>> # Cache a translation
        >>> await cache_repo.set_translation(
        ...     word="hello",
        ...     source_lang="en",
        ...     target_lang="ru",
        ...     data={"translation": "привет", "examples": [...]}
        ... )
        >>> # Retrieve cached translation
        >>> result = await cache_repo.get_translation("hello", "en", "ru")
        >>> if result:
        ...     print(result["translation"])  # "привет"
    """

    def __init__(self, session: AsyncSession):
        """Initialize cache repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def get_translation(
        self,
        word: str,
        source_lang: str,
        target_lang: str
    ) -> dict | None:
        """
        Get cached translation if available and not expired.

        Looks up a cached translation by word and language pair.
        Automatically filters out expired cache entries.

        Args:
            word: The word to translate (will be normalized to lowercase)
            source_lang: Source language code (e.g., "en")
            target_lang: Target language code (e.g., "ru")

        Returns:
            Translation data dict if found and not expired, None otherwise.
            The dict structure depends on the translation API format.

        Example:
            >>> result = await cache_repo.get_translation("hello", "en", "ru")
            >>> if result:
            ...     print(f"Cached translation: {result['translation']}")
            ... else:
            ...     print("Cache miss - need to fetch from API")
        """
        result = await self.session.execute(
            select(CachedTranslation).where(
                and_(
                    CachedTranslation.word == word.lower(),
                    CachedTranslation.source_language == source_lang,
                    CachedTranslation.target_language == target_lang,
                    # Check expiration: cache is valid if expires_at is NULL or in the future
                    (CachedTranslation.expires_at.is_(None)) |
                    (CachedTranslation.expires_at > datetime.now(timezone.utc))
                )
            )
        )

        cached = result.scalar_one_or_none()
        return cached.translation_data if cached else None

    async def set_translation(
        self,
        word: str,
        source_lang: str,
        target_lang: str,
        data: dict,
        expires_at: datetime | None = None
    ) -> None:
        """
        Cache a translation result with upsert logic.

        Updates existing cache entry if found, otherwise creates new one.
        This ensures we don't create duplicate cache entries.
        Handles race conditions gracefully with retry logic.

        Args:
            word: The word to translate (will be normalized to lowercase)
            source_lang: Source language code (e.g., "en")
            target_lang: Target language code (e.g., "ru")
            data: Translation data dict to cache
            expires_at: Optional expiration timestamp (timezone-aware).
                       If None, cache never expires.

        Example:
            >>> from datetime import timedelta
            >>> expires = datetime.now(timezone.utc) + timedelta(days=7)
            >>> await cache_repo.set_translation(
            ...     word="hello",
            ...     source_lang="en",
            ...     target_lang="ru",
            ...     data={
            ...         "translation": "привет",
            ...         "examples": ["Hello, world!", "Hello there!"]
            ...     },
            ...     expires_at=expires
            ... )
        """
        try:
            # Check if entry already exists
            existing = await self.session.execute(
                select(CachedTranslation).where(
                    and_(
                        CachedTranslation.word == word.lower(),
                        CachedTranslation.source_language == source_lang,
                        CachedTranslation.target_language == target_lang
                    )
                )
            )

            if existing_record := existing.scalar_one_or_none():
                # Update existing record
                existing_record.translation_data = data
                existing_record.cached_at = datetime.now(timezone.utc)
                existing_record.expires_at = expires_at
            else:
                # Create new record
                cached = CachedTranslation(
                    word=word.lower(),
                    source_language=source_lang,
                    target_language=target_lang,
                    translation_data=data,
                    expires_at=expires_at
                )
                self.session.add(cached)

            await self.session.flush()
        except IntegrityError:
            # Handle race condition: another transaction inserted the same record
            # Roll back and retry by updating the existing record
            await self.session.rollback()

            # Re-fetch the record that was created by the other transaction
            existing = await self.session.execute(
                select(CachedTranslation).where(
                    and_(
                        CachedTranslation.word == word.lower(),
                        CachedTranslation.source_language == source_lang,
                        CachedTranslation.target_language == target_lang
                    )
                )
            )

            existing_record = existing.scalar_one_or_none()
            if existing_record:
                # Update the existing record
                existing_record.translation_data = data
                existing_record.cached_at = datetime.now(timezone.utc)
                existing_record.expires_at = expires_at
                await self.session.flush()
            else:
                # This shouldn't happen, but re-raise if it does
                raise

    async def get_validation(
        self,
        word_id: int,
        direction: str,
        expected: str,
        user_answer: str
    ) -> tuple[bool, str] | None:
        """
        Get cached validation result if available.

        Looks up a cached validation by word, direction, and answer pair.
        This allows us to avoid repeated LLM API calls for identical answers.

        Args:
            word_id: ID of the word being validated
            direction: Validation direction ("forward" or "backward")
            expected: The expected/correct answer (will be normalized to lowercase)
            user_answer: The user's submitted answer (will be normalized to lowercase)

        Returns:
            Tuple of (is_correct, llm_comment) if found, None otherwise.
            - is_correct: Boolean indicating if answer was correct
            - llm_comment: LLM's feedback/explanation text

        Example:
            >>> result = await cache_repo.get_validation(
            ...     word_id=123,
            ...     direction="forward",
            ...     expected="hello",
            ...     user_answer="helo"
            ... )
            >>> if result:
            ...     is_correct, comment = result
            ...     print(f"Cached result: {'✓' if is_correct else '✗'}")
            ...     print(f"LLM comment: {comment}")
            ... else:
            ...     print("Cache miss - need to validate with LLM")
        """
        result = await self.session.execute(
            select(CachedValidation).where(
                and_(
                    CachedValidation.word_id == word_id,
                    CachedValidation.direction == direction,
                    CachedValidation.expected_answer == expected.lower(),
                    CachedValidation.user_answer == user_answer.lower()
                )
            )
        )

        cached = result.scalar_one_or_none()
        if cached:
            return (cached.is_correct, cached.llm_comment)
        return None

    async def set_validation(
        self,
        word_id: int,
        direction: str,
        expected: str,
        user_answer: str,
        is_correct: bool,
        comment: str
    ) -> None:
        """
        Cache a validation result with upsert logic.

        Updates existing cache entry if found, otherwise creates new one.
        This ensures we don't create duplicate cache entries.

        Args:
            word_id: ID of the word being validated
            direction: Validation direction ("forward" or "backward")
            expected: The expected/correct answer (will be normalized to lowercase)
            user_answer: The user's submitted answer (will be normalized to lowercase,
                        max 255 characters)
            is_correct: Whether the answer was validated as correct
            comment: LLM's feedback/explanation as text

        Raises:
            ValueError: If expected or user_answer exceed 255 characters

        Example:
            >>> await cache_repo.set_validation(
            ...     word_id=123,
            ...     direction="forward",
            ...     expected="hello",
            ...     user_answer="helo",
            ...     is_correct=False,
            ...     comment="Close! You have a minor spelling error. "
            ...             "The correct spelling is 'hello' with two 'l's."
            ... )
        """
        # Validate input length constraints
        if len(expected) > 255:
            raise ValueError(
                f"Expected answer exceeds maximum length of 255 characters: {len(expected)} characters"
            )
        if len(user_answer) > 255:
            raise ValueError(
                f"User answer exceeds maximum length of 255 characters: {len(user_answer)} characters"
            )

        # Normalize to lowercase
        expected_lower = expected.lower()
        user_answer_lower = user_answer.lower()

        try:
            # Check if entry already exists
            existing = await self.session.execute(
                select(CachedValidation).where(
                    and_(
                        CachedValidation.word_id == word_id,
                        CachedValidation.direction == direction,
                        CachedValidation.expected_answer == expected_lower,
                        CachedValidation.user_answer == user_answer_lower
                    )
                )
            )

            if existing_record := existing.scalar_one_or_none():
                # Update existing record
                existing_record.is_correct = is_correct
                existing_record.llm_comment = comment
                existing_record.cached_at = datetime.now(timezone.utc)
            else:
                # Create new record
                cached = CachedValidation(
                    word_id=word_id,
                    direction=direction,
                    expected_answer=expected_lower,
                    user_answer=user_answer_lower,
                    is_correct=is_correct,
                    llm_comment=comment
                )
                self.session.add(cached)

            await self.session.flush()
        except IntegrityError:
            # Handle race condition: another transaction inserted the same record
            # Roll back and retry by updating the existing record
            await self.session.rollback()

            # Re-fetch the record that was created by the other transaction
            existing = await self.session.execute(
                select(CachedValidation).where(
                    and_(
                        CachedValidation.word_id == word_id,
                        CachedValidation.direction == direction,
                        CachedValidation.expected_answer == expected_lower,
                        CachedValidation.user_answer == user_answer_lower
                    )
                )
            )

            existing_record = existing.scalar_one_or_none()
            if existing_record:
                # Update the existing record
                existing_record.is_correct = is_correct
                existing_record.llm_comment = comment
                existing_record.cached_at = datetime.now(timezone.utc)
                await self.session.flush()
            else:
                # This shouldn't happen, but re-raise if it does
                raise
