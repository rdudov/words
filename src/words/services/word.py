"""
Word service for word management and vocabulary operations.

This module provides the WordService class that orchestrates word management,
translation integration, and vocabulary statistics.

Key Features:
- Add words to user vocabulary with translation
- Get word translations and examples
- Track vocabulary statistics by learning status
- Word deduplication (prevents adding same word twice)
- Cache-first translation strategy via TranslationService
"""

from src.words.repositories.word import WordRepository, UserWordRepository
from src.words.services.translation import TranslationService
from src.words.models.word import Word, UserWord, WordStatusEnum
from src.words.utils.logger import logger


class WordService:
    """
    Business logic for word management.

    This service orchestrates word addition, translation, and vocabulary
    statistics. It integrates with TranslationService for LLM-based
    translations and implements word deduplication to prevent duplicate
    entries in user vocabulary.

    Attributes:
        word_repo: Repository for word database operations
        user_word_repo: Repository for user word operations
        translation_service: Service for word translations

    Example:
        >>> word_service = WordService(word_repo, user_word_repo, translation_service)
        >>> # Add word to user vocabulary
        >>> user_word = await word_service.add_word_for_user(
        ...     profile_id=1,
        ...     word_text="hello",
        ...     source_language="en",
        ...     target_language="ru"
        ... )
        >>> # Get vocabulary statistics
        >>> stats = await word_service.get_user_vocabulary_stats(profile_id=1)
        >>> print(stats)  # {"total": 150, "new": 10, "learning": 30, ...}
    """

    def __init__(
        self,
        word_repo: WordRepository,
        user_word_repo: UserWordRepository,
        translation_service: TranslationService
    ):
        """
        Initialize word service with dependencies.

        Args:
            word_repo: Repository for word database operations
            user_word_repo: Repository for user word operations
            translation_service: Service for word translations
        """
        self.word_repo = word_repo
        self.user_word_repo = user_word_repo
        self.translation_service = translation_service

    async def add_word_for_user(
        self,
        profile_id: int,
        word_text: str,
        source_language: str,
        target_language: str
    ) -> UserWord:
        """
        Add word to user vocabulary with translation.

        This method implements the complete word addition flow:
        1. Validate input parameters
        2. Check if word exists in database (fast, free)
        3. If word exists, check if user already has it (fast, free)
        4. If user has it, return early (no LLM call needed)
        5. Get translation from LLM only if word doesn't exist (slow, expensive)
        6. Create Word entity if needed (stored with source_language)
        7. Create UserWord with status=NEW
        8. Commit and log

        OPTIMIZATION NOTE: Database checks are done BEFORE LLM translation
        to avoid unnecessary API calls and costs.

        Args:
            profile_id: User's language profile ID
            word_text: Word text to add
            source_language: Source language (e.g., "en", "ru")
            target_language: Target language (e.g., "en", "ru")

        Returns:
            UserWord instance (either newly created or existing)

        Raises:
            ValueError: If input validation fails
            Exception: If database operations fail

        Example:
            >>> user_word = await word_service.add_word_for_user(
            ...     profile_id=1,
            ...     word_text="hello",
            ...     source_language="en",
            ...     target_language="ru"
            ... )
            >>> print(user_word.status)  # WordStatusEnum.NEW
            >>> print(user_word.word.word)  # "hello"
        """
        try:
            # ================================================================
            # STEP 1: Validate input parameters
            # ================================================================
            if not profile_id or profile_id <= 0:
                raise ValueError(f"Invalid profile_id: {profile_id}")

            if not word_text or not word_text.strip():
                raise ValueError(f"Invalid word_text: '{word_text}'")

            if not source_language or not source_language.strip():
                raise ValueError(f"Invalid source_language: '{source_language}'")

            if not target_language or not target_language.strip():
                raise ValueError(f"Invalid target_language: '{target_language}'")

            logger.info(
                "word_addition_started",
                profile_id=profile_id,
                word=word_text,
                source_language=source_language,
                target_language=target_language
            )

            # ================================================================
            # STEP 2: Check if word exists in database (FAST, FREE)
            # ================================================================
            word = await self.word_repo.find_by_text_and_language(
                word_text, source_language
            )

            # ================================================================
            # STEP 3: If word exists, check if user already has it (FAST, FREE)
            # ================================================================
            if word:
                logger.debug(
                    "word_exists_checking_user_vocabulary",
                    word_id=word.word_id,
                    word=word_text,
                    profile_id=profile_id
                )

                # Check if user already has this word (deduplication)
                user_word = await self.user_word_repo.get_user_word(
                    profile_id, word.word_id
                )

                if user_word:
                    # EARLY RETURN: User already has this word, no LLM call needed
                    logger.warning(
                        "word_already_in_user_vocabulary",
                        profile_id=profile_id,
                        word_id=word.word_id,
                        word=word_text
                    )
                    return user_word

                # Word exists but user doesn't have it - we'll add it below
                logger.debug(
                    "word_exists_adding_to_user_vocabulary",
                    word_id=word.word_id,
                    word=word_text,
                    profile_id=profile_id
                )

            # ================================================================
            # STEP 4: Get translation from LLM (SLOW, EXPENSIVE)
            # Only executed if word doesn't exist in database
            # ================================================================
            if not word:
                logger.debug(
                    "word_not_found_fetching_translation",
                    word=word_text,
                    source_language=source_language,
                    target_language=target_language
                )

                translation_data = await self.translation_service.translate_word(
                    word_text, source_language, target_language
                )

                # ================================================================
                # STEP 5: Create new Word entity with translation data
                # ================================================================
                # Transform translation list to dict: {"ru": ["привет", "здравствуй"]}
                translations_dict = {
                    target_language: translation_data.get("translations", [])
                }

                word = Word(
                    word=word_text.lower(),
                    language=source_language,  # Store with source language
                    translations=translations_dict,
                    examples=translation_data.get("examples", []),
                    word_forms=translation_data.get("word_forms", {})
                )
                word = await self.word_repo.add(word)
                await self.word_repo.commit()  # Commit Word separately

                logger.info(
                    "word_created",
                    word_id=word.word_id,
                    word=word_text,
                    language=source_language
                )

            # ================================================================
            # STEP 6: Create UserWord (we know user doesn't have it)
            # ================================================================
            user_word = UserWord(
                profile_id=profile_id,
                word_id=word.word_id,
                status=WordStatusEnum.NEW
            )

            user_word = await self.user_word_repo.add(user_word)
            await self.user_word_repo.commit()

            logger.info(
                "word_added_to_user_vocabulary",
                profile_id=profile_id,
                word=word_text,
                word_id=word.word_id,
                status=user_word.status.value
            )

            return user_word

        except ValueError as ve:
            logger.error(
                "word_addition_validation_failed",
                profile_id=profile_id,
                word=word_text,
                error=str(ve)
            )
            raise

        except Exception as e:
            logger.error(
                "word_addition_failed",
                profile_id=profile_id,
                word=word_text,
                source_language=source_language,
                target_language=target_language,
                error=str(e),
                error_type=type(e).__name__
            )
            # Rollback transaction on error
            await self.word_repo.rollback()
            await self.user_word_repo.rollback()
            raise

    async def get_word_with_translations(
        self,
        word_text: str,
        source_language: str,
        target_language: str
    ) -> dict:
        """
        Get word translations and examples.

        This method delegates to TranslationService.translate_word()
        which implements cache-first strategy.

        Args:
            word_text: Word to translate
            source_language: Source language (e.g., "en", "ru")
            target_language: Target language (e.g., "en", "ru")

        Returns:
            Dictionary containing:
                - word: Original word
                - translations: List of translations
                - examples: List of example sentences
                - word_forms: Dictionary of word forms

        Example:
            >>> result = await word_service.get_word_with_translations(
            ...     word_text="hello",
            ...     source_language="en",
            ...     target_language="ru"
            ... )
            >>> print(result["translations"])  # ["привет", "здравствуй"]
        """
        return await self.translation_service.translate_word(
            word_text, source_language, target_language
        )

    async def get_user_vocabulary_stats(
        self,
        profile_id: int
    ) -> dict:
        """
        Get vocabulary statistics for a user.

        Returns counts of words grouped by learning status (NEW, LEARNING,
        REVIEWING, MASTERED) plus total count.

        Args:
            profile_id: User's language profile ID

        Returns:
            Dictionary with keys:
                - total: Total word count
                - new: Count of NEW words
                - learning: Count of LEARNING words
                - reviewing: Count of REVIEWING words
                - mastered: Count of MASTERED words

        Example:
            >>> stats = await word_service.get_user_vocabulary_stats(profile_id=1)
            >>> print(stats)
            {
                "total": 150,
                "new": 10,
                "learning": 30,
                "reviewing": 50,
                "mastered": 60
            }
        """
        counts = await self.user_word_repo.count_by_status(profile_id)

        total = sum(counts.values())

        return {
            "total": total,
            "new": counts.get("new", 0),
            "learning": counts.get("learning", 0),
            "reviewing": counts.get("reviewing", 0),
            "mastered": counts.get("mastered", 0)
        }
