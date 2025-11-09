"""
User and LanguageProfile repository implementations for the Words application.

This module provides repository classes for:
- UserRepository: User-specific database operations including notification queries
- ProfileRepository: Language profile management and active profile switching
"""

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone
from .base import BaseRepository
from src.words.models.user import User, LanguageProfile


class UserRepository(BaseRepository[User]):
    """User-specific database operations.

    Provides methods for:
    - Getting users by Telegram ID with eager-loaded profiles
    - Querying users who need notifications
    - Updating last active timestamps

    Attributes:
        session: AsyncSession for database operations
        model: The User model class

    Example:
        >>> user_repo = UserRepository(session)
        >>> user = await user_repo.get_by_telegram_id(123456789)
        >>> if user:
        ...     print(f"User has {len(user.profiles)} language profiles")
    """

    def __init__(self, session):
        """Initialize UserRepository with session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__(session, User)

    async def get_by_telegram_id(self, user_id: int) -> User | None:
        """Get user by Telegram ID with profiles eagerly loaded.

        Uses selectinload to efficiently load all language profiles
        in a single query to avoid N+1 issues.

        Args:
            user_id: Telegram user ID

        Returns:
            User instance with profiles loaded, or None if not found

        Example:
            >>> user = await user_repo.get_by_telegram_id(123456789)
            >>> if user:
            ...     for profile in user.profiles:
            ...         print(f"Learning {profile.target_language}")
        """
        result = await self.session.execute(
            select(User)
            .where(User.user_id == user_id)
            .options(selectinload(User.profiles))
        )
        return result.scalar_one_or_none()

    async def get_users_for_notification(
        self,
        inactive_hours: int,
        current_hour: int
    ) -> list[User]:
        """Get users who need notifications based on inactivity.

        Finds users who:
        - Have notifications enabled
        - Haven't been active for the specified number of hours

        Args:
            inactive_hours: Number of hours of inactivity threshold
            current_hour: Current hour (0-23) for timezone filtering

        Returns:
            List of users needing notifications

        Example:
            >>> # Get users inactive for 24+ hours
            >>> users = await user_repo.get_users_for_notification(24, 10)
            >>> for user in users:
            ...     print(f"Send notification to {user.user_id}")
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=inactive_hours)

        result = await self.session.execute(
            select(User).where(
                and_(
                    User.notification_enabled == True,
                    User.last_active_at < cutoff_time
                )
            )
        )
        return list(result.scalars().all())

    async def update_last_active(self, user_id: int) -> None:
        """Update user's last active timestamp to current time.

        Updates the last_active_at field to track user activity.
        If user doesn't exist, does nothing.

        Args:
            user_id: Telegram user ID

        Example:
            >>> await user_repo.update_last_active(123456789)
            >>> await user_repo.commit()
        """
        user = await self.get_by_telegram_id(user_id)
        if user:
            user.last_active_at = datetime.now(timezone.utc)
            await self.session.flush()


class ProfileRepository(BaseRepository[LanguageProfile]):
    """Language profile operations.

    Provides methods for:
    - Getting active language profiles
    - Managing profile activation/deactivation
    - Switching between language profiles

    Attributes:
        session: AsyncSession for database operations
        model: The LanguageProfile model class

    Example:
        >>> profile_repo = ProfileRepository(session)
        >>> active = await profile_repo.get_active_profile(123456789)
        >>> if active:
        ...     print(f"Currently learning {active.target_language}")
    """

    def __init__(self, session):
        """Initialize ProfileRepository with session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__(session, LanguageProfile)

    async def get_active_profile(self, user_id: int) -> LanguageProfile | None:
        """Get user's currently active language profile.

        Each user should have at most one active profile at a time.

        Args:
            user_id: Telegram user ID

        Returns:
            Active LanguageProfile or None if no active profile exists

        Example:
            >>> profile = await profile_repo.get_active_profile(123456789)
            >>> if profile:
            ...     print(f"Level: {profile.level.value}")
        """
        result = await self.session.execute(
            select(LanguageProfile)
            .where(
                and_(
                    LanguageProfile.user_id == user_id,
                    LanguageProfile.is_active == True
                )
            )
            .options(selectinload(LanguageProfile.user))
        )
        return result.scalar_one_or_none()

    async def get_user_profiles(self, user_id: int) -> list[LanguageProfile]:
        """Get all language profiles for a user.

        Returns all profiles regardless of active status.

        Args:
            user_id: Telegram user ID

        Returns:
            List of all LanguageProfile instances for the user

        Example:
            >>> profiles = await profile_repo.get_user_profiles(123456789)
            >>> for p in profiles:
            ...     status = "active" if p.is_active else "inactive"
            ...     print(f"{p.target_language}: {status}")
        """
        result = await self.session.execute(
            select(LanguageProfile).where(
                LanguageProfile.user_id == user_id
            )
        )
        return list(result.scalars().all())

    async def deactivate_all_profiles(self, user_id: int) -> None:
        """Deactivate all language profiles for a user.

        Sets is_active=False for all profiles belonging to the user.
        This is used before activating a new profile to ensure only
        one profile is active at a time.

        Args:
            user_id: Telegram user ID

        Example:
            >>> await profile_repo.deactivate_all_profiles(123456789)
            >>> await profile_repo.commit()
        """
        profiles = await self.get_user_profiles(user_id)
        for profile in profiles:
            profile.is_active = False
        await self.session.flush()

    async def switch_active_language(
        self,
        user_id: int,
        target_language: str
    ) -> LanguageProfile:
        """Switch active language profile for a user.

        Deactivates all profiles for the user, then activates the
        profile for the specified target language.

        Args:
            user_id: Telegram user ID
            target_language: ISO 639-1 language code to activate

        Returns:
            The newly activated LanguageProfile

        Raises:
            ValueError: If the target language profile doesn't exist

        Example:
            >>> profile = await profile_repo.switch_active_language(
            ...     123456789, "es"
            ... )
            >>> await profile_repo.commit()
            >>> print(f"Switched to {profile.target_language}")
        """
        # Deactivate all profiles
        await self.deactivate_all_profiles(user_id)

        # Get all profiles to find the target
        profiles = await self.get_user_profiles(user_id)

        # Find and activate target profile
        target = next(
            (p for p in profiles if p.target_language == target_language),
            None
        )

        if target is None:
            raise ValueError(
                f"No profile found for user {user_id} "
                f"with target language '{target_language}'"
            )

        target.is_active = True
        await self.session.flush()

        return target
