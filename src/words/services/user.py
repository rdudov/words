"""
User and LanguageProfile service implementations for the Words application.

This module provides service classes for:
- UserService: Business logic for user management, registration, and activity tracking
"""

import logging
from datetime import datetime, timezone
from src.words.repositories.user import UserRepository, ProfileRepository
from src.words.models.user import User, LanguageProfile, CEFRLevel

logger = logging.getLogger(__name__)


class UserService:
    """Business logic for user management.

    This service provides high-level operations for user registration,
    language profile management, and activity tracking. It orchestrates
    multiple repository operations and implements business rules.

    Attributes:
        user_repo: Repository for user database operations
        profile_repo: Repository for language profile operations

    Example:
        >>> user_service = UserService(user_repo, profile_repo)
        >>> user = await user_service.register_user(
        ...     user_id=123456789,
        ...     native_language="ru",
        ...     interface_language="ru"
        ... )
        >>> profile = await user_service.create_language_profile(
        ...     user_id=123456789,
        ...     target_language="en",
        ...     level="A1"
        ... )
    """

    def __init__(
        self,
        user_repo: UserRepository,
        profile_repo: ProfileRepository
    ):
        """Initialize service with repositories.

        Args:
            user_repo: UserRepository instance for user operations
            profile_repo: ProfileRepository instance for profile operations
        """
        self.user_repo = user_repo
        self.profile_repo = profile_repo

    async def register_user(
        self,
        user_id: int,
        native_language: str,
        interface_language: str
    ) -> User:
        """Register new user in the system.

        Creates a new user with specified language preferences and sets
        the last_active_at timestamp to current time.

        Args:
            user_id: Telegram user ID
            native_language: User's native language (ISO 639-1 code)
            interface_language: Bot interface language (ISO 639-1 code)

        Returns:
            Newly created User instance

        Example:
            >>> user = await user_service.register_user(
            ...     user_id=123456789,
            ...     native_language="ru",
            ...     interface_language="en"
            ... )
            >>> print(f"User {user.user_id} registered")
        """
        user = User(
            user_id=user_id,
            native_language=native_language,
            interface_language=interface_language,
            last_active_at=datetime.now(timezone.utc)
        )

        user = await self.user_repo.add(user)
        await self.user_repo.commit()

        logger.info(
            "User registered: user_id=%d, native_language=%s",
            user_id,
            native_language
        )

        return user

    async def create_language_profile(
        self,
        user_id: int,
        target_language: str,
        level: str
    ) -> LanguageProfile:
        """Create new language learning profile for a user.

        Creates a new language profile and sets it as active.
        Deactivates all other profiles for the user to ensure
        only one profile is active at a time.

        Args:
            user_id: Telegram user ID
            target_language: Target language to learn (ISO 639-1 code)
            level: CEFR level as string (A1, A2, B1, B2, C1, C2)

        Returns:
            Newly created LanguageProfile instance

        Example:
            >>> profile = await user_service.create_language_profile(
            ...     user_id=123456789,
            ...     target_language="es",
            ...     level="B1"
            ... )
            >>> print(f"Profile created: {profile.target_language} at {profile.level.value}")
        """
        # Deactivate other profiles using repository method
        await self.profile_repo.deactivate_all_profiles(user_id)

        # Create new profile
        profile = LanguageProfile(
            user_id=user_id,
            target_language=target_language,
            level=CEFRLevel[level],
            is_active=True
        )

        profile = await self.profile_repo.add(profile)
        await self.profile_repo.commit()

        logger.info(
            "Language profile created: user_id=%d, language=%s, level=%s",
            user_id,
            target_language,
            level
        )

        return profile

    async def get_user(self, user_id: int) -> User | None:
        """Get existing user or return None if not registered.

        This method retrieves a user by their Telegram ID. If the user
        doesn't exist, it returns None. Use this to check if a user
        is already registered.

        Args:
            user_id: Telegram user ID

        Returns:
            User instance if found, None otherwise

        Example:
            >>> user = await user_service.get_user(123456789)
            >>> if user is None:
            ...     print("User not registered, please register first")
            >>> else:
            ...     print(f"Welcome back, user {user.user_id}!")
        """
        return await self.user_repo.get_by_telegram_id(user_id)

    async def switch_active_language(
        self,
        user_id: int,
        target_language: str
    ) -> LanguageProfile:
        """Switch to a different active language profile.

        Changes the currently active language profile to the specified
        target language. The target language profile must already exist.

        Args:
            user_id: Telegram user ID
            target_language: Target language to switch to (ISO 639-1 code)

        Returns:
            The newly activated LanguageProfile

        Raises:
            ValueError: If the target language profile doesn't exist

        Example:
            >>> profile = await user_service.switch_active_language(
            ...     user_id=123456789,
            ...     target_language="fr"
            ... )
            >>> print(f"Switched to {profile.target_language}")
        """
        profile = await self.profile_repo.switch_active_language(
            user_id,
            target_language
        )
        await self.profile_repo.commit()

        logger.info(
            "Language switched: user_id=%d, language=%s",
            user_id,
            target_language
        )

        return profile

    async def update_last_active(self, user_id: int) -> None:
        """Update user's last activity timestamp.

        Updates the last_active_at field to the current time to track
        when the user last interacted with the bot. This is used for
        notification scheduling and activity monitoring.

        Args:
            user_id: Telegram user ID

        Example:
            >>> await user_service.update_last_active(123456789)
        """
        await self.user_repo.update_last_active(user_id)
        await self.user_repo.commit()
