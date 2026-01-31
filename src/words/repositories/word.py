"""
Word and UserWord repository implementations for the Words application.

This module provides repositories for:
- WordRepository: CRUD operations for Word model
- UserWordRepository: User word management with statistics and relationships
"""

from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from .base import BaseRepository
from src.words.models.word import Word, UserWord, WordStatusEnum
from src.words.models.user import LanguageProfile


class WordRepository(BaseRepository[Word]):
    """Repository for Word database operations.

    Provides methods for finding words by text/language and retrieving
    frequency-based word lists for language learning.

    Example:
        >>> word_repo = WordRepository(session)
        >>> word = await word_repo.find_by_text_and_language("hello", "en")
        >>> frequent_words = await word_repo.get_frequency_words("en", "A1", limit=50)
    """

    def __init__(self, session):
        """Initialize WordRepository with session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__(session, Word)

    async def find_by_text_and_language(
        self,
        word: str,
        language: str
    ) -> Word | None:
        """Find word by text and language (case-insensitive).

        Normalization strategy: This method normalizes the search term to lowercase
        for case-insensitive lookup. The Word model uses a @validates decorator
        to ensure all words are stored in lowercase at the database level,
        providing data integrity and consistent case-insensitive behavior.

        Args:
            word: Word text to search for (will be normalized to lowercase)
            language: Language code (ISO 639-1, e.g., "en", "ru")

        Returns:
            Word instance or None if not found

        Example:
            >>> word = await repo.find_by_text_and_language("hello", "en")
            >>> if word:
            ...     print(f"Found: {word.word} ({word.language})")
        """
        # Early return for empty or whitespace-only strings
        if not word or not word.strip():
            return None

        result = await self.session.execute(
            select(Word).where(
                and_(
                    Word.word == word.lower(),
                    Word.language == language
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_frequency_words(
        self,
        language: str,
        level: str,
        limit: int = 50
    ) -> list[Word]:
        """Get most frequent words for a given language and level.

        Words are ordered by frequency rank (lower rank = more common).

        Args:
            language: Language code (ISO 639-1, e.g., "en", "ru")
            level: CEFR level (A1, A2, B1, B2, C1, C2)
            limit: Maximum number of words to return (default: 50)

        Returns:
            List of Word instances ordered by frequency rank

        Example:
            >>> words = await repo.get_frequency_words("en", "A1", limit=100)
            >>> for word in words[:10]:
            ...     print(f"{word.word}: rank {word.frequency_rank}")
        """
        result = await self.session.execute(
            select(Word).where(
                and_(
                    Word.language == language,
                    Word.level == level
                )
            ).order_by(Word.frequency_rank).limit(limit)
        )
        return list(result.scalars().all())


class UserWordRepository(BaseRepository[UserWord]):
    """Repository for UserWord operations with learning statistics.

    Manages user's vocabulary with eager loading of word and statistics
    relationships for efficient data access.

    Example:
        >>> user_word_repo = UserWordRepository(session)
        >>> user_word = await user_word_repo.get_user_word(profile_id=1, word_id=100)
        >>> vocab = await user_word_repo.get_user_vocabulary(profile_id=1)
        >>> stats = await user_word_repo.count_by_status(profile_id=1)
    """

    def __init__(self, session):
        """Initialize UserWordRepository with session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__(session, UserWord)

    async def get_user_word(
        self,
        profile_id: int,
        word_id: int
    ) -> UserWord | None:
        """Get user's word with eagerly loaded statistics and word details.

        Uses selectinload to efficiently load the word and statistics
        relationships in a single database roundtrip.

        Args:
            profile_id: User's language profile ID
            word_id: Word ID

        Returns:
            UserWord instance with loaded relationships, or None if not found

        Example:
            >>> user_word = await repo.get_user_word(profile_id=1, word_id=100)
            >>> if user_word:
            ...     print(f"Word: {user_word.word.word}")
            ...     print(f"Statistics: {len(user_word.statistics)}")
        """
        result = await self.session.execute(
            select(UserWord).where(
                and_(
                    UserWord.profile_id == profile_id,
                    UserWord.word_id == word_id
                )
            ).options(
                selectinload(UserWord.word),
                selectinload(UserWord.statistics)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_details(self, user_word_id: int) -> UserWord | None:
        """Get user word by id with word, statistics, and profile loaded."""
        result = await self.session.execute(
            select(UserWord).where(
                UserWord.user_word_id == user_word_id
            ).options(
                selectinload(UserWord.word),
                selectinload(UserWord.statistics),
                selectinload(UserWord.profile).selectinload(LanguageProfile.user)
            ).execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_user_words_for_lesson(
        self,
        profile_id: int,
        limit: int = 30
    ) -> list[UserWord]:
        """Get user words for lesson with all required relationships loaded."""
        result = await self.session.execute(
            select(UserWord).where(
                UserWord.profile_id == profile_id
            ).options(
                selectinload(UserWord.word),
                selectinload(UserWord.statistics),
                selectinload(UserWord.profile).selectinload(LanguageProfile.user)
            ).limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_vocabulary(
        self,
        profile_id: int,
        status: WordStatusEnum | None = None
    ) -> list[UserWord]:
        """Get user's vocabulary with optional status filtering.

        Eagerly loads word and statistics relationships for each UserWord.

        Args:
            profile_id: User's language profile ID
            status: Optional status filter (NEW, LEARNING, REVIEWING, MASTERED)

        Returns:
            List of UserWord instances with loaded relationships

        Example:
            >>> # Get all vocabulary
            >>> all_words = await repo.get_user_vocabulary(profile_id=1)
            >>>
            >>> # Get only words being learned
            >>> learning = await repo.get_user_vocabulary(
            ...     profile_id=1,
            ...     status=WordStatusEnum.LEARNING
            ... )
        """
        query = select(UserWord).where(
            UserWord.profile_id == profile_id
        )

        if status:
            query = query.where(UserWord.status == status)

        result = await self.session.execute(
            query.options(
                selectinload(UserWord.word),
                selectinload(UserWord.statistics)
            )
        )
        return list(result.scalars().all())

    async def count_by_status(
        self,
        profile_id: int
    ) -> dict[str, int]:
        """Count user's words grouped by learning status.

        Returns a dictionary mapping status values to counts.

        Args:
            profile_id: User's language profile ID

        Returns:
            Dictionary mapping status string values to counts

        Example:
            >>> counts = await repo.count_by_status(profile_id=1)
            >>> print(counts)
            {'new': 15, 'learning': 23, 'reviewing': 42, 'mastered': 120}
        """
        result = await self.session.execute(
            select(
                UserWord.status,
                func.count(UserWord.user_word_id)
            ).where(
                UserWord.profile_id == profile_id
            ).group_by(UserWord.status)
        )

        return {
            status.value: count
            for status, count in result.all()
        }
