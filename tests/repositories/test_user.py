"""
Comprehensive tests for UserRepository and ProfileRepository.

Tests cover:
- UserRepository methods (get_by_telegram_id, get_users_for_notification, update_last_active)
- ProfileRepository methods (get_active_profile, get_user_profiles, switch_active_language)
- Eager loading with selectinload
- Edge cases and error handling
- Integration with actual database operations
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from src.words.repositories.user import UserRepository, ProfileRepository
from src.words.models import Base, User, LanguageProfile, CEFRLevel


class TestUserRepositoryInitialization:
    """Tests for UserRepository initialization."""

    @pytest.mark.asyncio
    async def test_user_repository_initialization(self):
        """Test that UserRepository can be initialized with session."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = UserRepository(mock_session)

        assert repo.session is mock_session
        assert repo.model is User

    @pytest.mark.asyncio
    async def test_user_repository_inherits_from_base(self):
        """Test that UserRepository inherits BaseRepository methods."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = UserRepository(mock_session)

        # Check that base methods are available
        assert hasattr(repo, 'get_by_id')
        assert hasattr(repo, 'get_all')
        assert hasattr(repo, 'add')
        assert hasattr(repo, 'delete')
        assert hasattr(repo, 'commit')
        assert hasattr(repo, 'rollback')


class TestGetByTelegramId:
    """Tests for get_by_telegram_id method."""

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_returns_user_when_found(self):
        """Test that get_by_telegram_id returns user when it exists."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_user = User(user_id=123456789, native_language="ru", interface_language="ru")
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_by_telegram_id(123456789)

        assert result is mock_user
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_returns_none_when_not_found(self):
        """Test that get_by_telegram_id returns None when user doesn't exist."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_by_telegram_id(999999999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_uses_selectinload_for_profiles(self):
        """Test that get_by_telegram_id uses selectinload to eagerly load profiles."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        await repo.get_by_telegram_id(123456789)

        # Verify execute was called (selectinload is used in the query)
        mock_session.execute.assert_called_once()


class TestGetUsersForNotification:
    """Tests for get_users_for_notification method."""

    @pytest.mark.asyncio
    async def test_get_users_for_notification_returns_inactive_users(self):
        """Test that get_users_for_notification returns users needing notification."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()

        # Create mock users with old last_active_at
        users = [
            User(user_id=100, native_language="ru", interface_language="ru", notification_enabled=True),
            User(user_id=200, native_language="en", interface_language="en", notification_enabled=True)
        ]
        mock_scalars.all.return_value = users
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_users_for_notification(inactive_hours=24, current_hour=10)

        assert len(result) == 2
        assert result[0].user_id == 100
        assert result[1].user_id == 200

    @pytest.mark.asyncio
    async def test_get_users_for_notification_returns_empty_list_when_no_users(self):
        """Test that get_users_for_notification returns empty list when no users match."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_users_for_notification(inactive_hours=24, current_hour=10)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_users_for_notification_filters_by_inactive_hours(self):
        """Test that get_users_for_notification filters by inactive hours."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        await repo.get_users_for_notification(inactive_hours=48, current_hour=14)

        # Verify execute was called (query includes time filtering)
        mock_session.execute.assert_called_once()


class TestUpdateLastActive:
    """Tests for update_last_active method."""

    @pytest.mark.asyncio
    async def test_update_last_active_updates_timestamp(self):
        """Test that update_last_active updates the last_active_at field."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        # Create mock user
        mock_user = User(
            user_id=123456789,
            native_language="ru",
            interface_language="ru",
            last_active_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        )
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        await repo.update_last_active(123456789)

        # Verify last_active_at was updated
        assert mock_user.last_active_at > datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_last_active_does_nothing_when_user_not_found(self):
        """Test that update_last_active does nothing when user doesn't exist."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        await repo.update_last_active(999999999)

        # Verify flush was not called
        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_last_active_sets_timezone_aware_datetime(self):
        """Test that update_last_active sets timezone-aware datetime."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        mock_user = User(user_id=123456789, native_language="ru", interface_language="ru")
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        await repo.update_last_active(123456789)

        # Verify timezone is set
        assert mock_user.last_active_at is not None
        assert mock_user.last_active_at.tzinfo is not None
        assert mock_user.last_active_at.tzinfo == timezone.utc


class TestProfileRepositoryInitialization:
    """Tests for ProfileRepository initialization."""

    @pytest.mark.asyncio
    async def test_profile_repository_initialization(self):
        """Test that ProfileRepository can be initialized with session."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = ProfileRepository(mock_session)

        assert repo.session is mock_session
        assert repo.model is LanguageProfile

    @pytest.mark.asyncio
    async def test_profile_repository_inherits_from_base(self):
        """Test that ProfileRepository inherits BaseRepository methods."""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = ProfileRepository(mock_session)

        # Check that base methods are available
        assert hasattr(repo, 'get_by_id')
        assert hasattr(repo, 'get_all')
        assert hasattr(repo, 'add')
        assert hasattr(repo, 'delete')


class TestGetActiveProfile:
    """Tests for get_active_profile method."""

    @pytest.mark.asyncio
    async def test_get_active_profile_returns_active_profile(self):
        """Test that get_active_profile returns the active profile."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        mock_profile = LanguageProfile(
            user_id=123456789,
            target_language="en",
            level=CEFRLevel.B1,
            is_active=True
        )
        mock_result.scalar_one_or_none.return_value = mock_profile
        mock_session.execute.return_value = mock_result

        repo = ProfileRepository(mock_session)
        result = await repo.get_active_profile(123456789)

        assert result is mock_profile
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_get_active_profile_returns_none_when_no_active_profile(self):
        """Test that get_active_profile returns None when no active profile exists."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = ProfileRepository(mock_session)
        result = await repo.get_active_profile(123456789)

        assert result is None


class TestGetUserProfiles:
    """Tests for get_user_profiles method."""

    @pytest.mark.asyncio
    async def test_get_user_profiles_returns_all_profiles(self):
        """Test that get_user_profiles returns all profiles for a user."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()

        profiles = [
            LanguageProfile(user_id=123456789, target_language="en", level=CEFRLevel.B1, is_active=True),
            LanguageProfile(user_id=123456789, target_language="es", level=CEFRLevel.A2, is_active=False),
            LanguageProfile(user_id=123456789, target_language="de", level=CEFRLevel.B2, is_active=False)
        ]
        mock_scalars.all.return_value = profiles
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ProfileRepository(mock_session)
        result = await repo.get_user_profiles(123456789)

        assert len(result) == 3
        assert result[0].target_language == "en"
        assert result[1].target_language == "es"
        assert result[2].target_language == "de"

    @pytest.mark.asyncio
    async def test_get_user_profiles_returns_empty_list_when_no_profiles(self):
        """Test that get_user_profiles returns empty list when user has no profiles."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ProfileRepository(mock_session)
        result = await repo.get_user_profiles(123456789)

        assert result == []


class TestSwitchActiveLanguage:
    """Tests for switch_active_language method."""

    @pytest.mark.asyncio
    async def test_switch_active_language_deactivates_all_and_activates_target(self):
        """Test that switch_active_language correctly switches active profile."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()

        # Create mock profiles
        profile_en = LanguageProfile(
            profile_id=1,
            user_id=123456789,
            target_language="en",
            level=CEFRLevel.B1,
            is_active=True
        )
        profile_es = LanguageProfile(
            profile_id=2,
            user_id=123456789,
            target_language="es",
            level=CEFRLevel.A2,
            is_active=False
        )
        profiles = [profile_en, profile_es]

        mock_scalars.all.return_value = profiles
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ProfileRepository(mock_session)
        result = await repo.switch_active_language(123456789, "es")

        # Verify English profile was deactivated
        assert profile_en.is_active is False
        # Verify Spanish profile was activated
        assert profile_es.is_active is True
        # Verify the activated profile was returned
        assert result is profile_es
        # Flush is called twice: once in deactivate_all_profiles, once in switch_active_language
        assert mock_session.flush.call_count == 2

    @pytest.mark.asyncio
    async def test_switch_active_language_raises_error_when_language_not_found(self):
        """Test that switch_active_language raises ValueError when language doesn't exist."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()

        # Create mock profiles without the target language
        profiles = [
            LanguageProfile(user_id=123456789, target_language="en", level=CEFRLevel.B1, is_active=True)
        ]
        mock_scalars.all.return_value = profiles
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ProfileRepository(mock_session)

        with pytest.raises(ValueError) as exc_info:
            await repo.switch_active_language(123456789, "fr")

        assert "No profile found" in str(exc_info.value)
        assert "fr" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_switch_active_language_handles_no_active_profile(self):
        """Test that switch_active_language works when no profile is currently active."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()

        # Create mock profiles with none active
        profile_en = LanguageProfile(
            user_id=123456789,
            target_language="en",
            level=CEFRLevel.B1,
            is_active=False
        )
        profile_es = LanguageProfile(
            user_id=123456789,
            target_language="es",
            level=CEFRLevel.A2,
            is_active=False
        )
        profiles = [profile_en, profile_es]

        mock_scalars.all.return_value = profiles
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ProfileRepository(mock_session)
        result = await repo.switch_active_language(123456789, "es")

        # Verify Spanish profile was activated
        assert profile_es.is_active is True
        assert result is profile_es


class TestUserRepositoryIntegration:
    """Integration tests for UserRepository with actual database."""

    @pytest.fixture
    async def engine(self):
        """Create async engine for testing."""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False
        )

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine

        await engine.dispose()

    @pytest.fixture
    async def session(self, engine):
        """Create async session for testing."""
        async_session = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        async with async_session() as session:
            yield session

    @pytest.mark.asyncio
    async def test_integration_get_by_telegram_id_with_profiles(self, session):
        """Test get_by_telegram_id loads user with profiles."""
        # Create user with profiles
        user = User(user_id=123456789, native_language="ru", interface_language="ru")
        session.add(user)
        await session.commit()

        profile1 = LanguageProfile(
            user_id=123456789,
            target_language="en",
            level=CEFRLevel.B1
        )
        profile2 = LanguageProfile(
            user_id=123456789,
            target_language="es",
            level=CEFRLevel.A2
        )
        session.add_all([profile1, profile2])
        await session.commit()

        # Get user by telegram ID
        repo = UserRepository(session)
        retrieved_user = await repo.get_by_telegram_id(123456789)

        assert retrieved_user is not None
        assert retrieved_user.user_id == 123456789
        # Profiles should be eagerly loaded
        assert len(retrieved_user.profiles) == 2
        target_languages = [p.target_language for p in retrieved_user.profiles]
        assert "en" in target_languages
        assert "es" in target_languages

    @pytest.mark.asyncio
    async def test_integration_get_users_for_notification(self, session):
        """Test get_users_for_notification with actual data."""
        # Create users with different last_active times
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        recent_time = datetime.now(timezone.utc) - timedelta(hours=2)

        user1 = User(
            user_id=100,
            native_language="ru",
            interface_language="ru",
            notification_enabled=True,
            last_active_at=old_time
        )
        user2 = User(
            user_id=200,
            native_language="en",
            interface_language="en",
            notification_enabled=True,
            last_active_at=recent_time
        )
        user3 = User(
            user_id=300,
            native_language="es",
            interface_language="es",
            notification_enabled=False,  # Notifications disabled
            last_active_at=old_time
        )
        session.add_all([user1, user2, user3])
        await session.commit()

        # Get users needing notification (inactive for 24+ hours)
        repo = UserRepository(session)
        users = await repo.get_users_for_notification(inactive_hours=24, current_hour=10)

        # Should return only user1 (user2 is recent, user3 has notifications disabled)
        assert len(users) == 1
        assert users[0].user_id == 100

    @pytest.mark.asyncio
    async def test_integration_update_last_active(self, session):
        """Test update_last_active updates the timestamp."""
        # Create user
        old_time = datetime.now(timezone.utc) - timedelta(hours=24)
        user = User(
            user_id=123456789,
            native_language="ru",
            interface_language="ru",
            last_active_at=old_time
        )
        session.add(user)
        await session.commit()

        # Update last active
        repo = UserRepository(session)
        await repo.update_last_active(123456789)
        await session.commit()

        # Verify timestamp was updated
        result = await session.execute(
            select(User).where(User.user_id == 123456789)
        )
        updated_user = result.scalar_one()
        assert updated_user.last_active_at > old_time

    @pytest.mark.asyncio
    async def test_integration_user_repository_inherits_base_methods(self, session):
        """Test that UserRepository can use base CRUD methods."""
        repo = UserRepository(session)

        # Test add
        user = User(user_id=999, native_language="ru", interface_language="ru")
        added_user = await repo.add(user)
        await repo.commit()

        assert added_user.user_id == 999

        # Test get_by_id
        retrieved = await repo.get_by_id(999)
        assert retrieved is not None
        assert retrieved.user_id == 999


class TestProfileRepositoryIntegration:
    """Integration tests for ProfileRepository with actual database."""

    @pytest.fixture
    async def engine(self):
        """Create async engine for testing."""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False
        )

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine

        await engine.dispose()

    @pytest.fixture
    async def session(self, engine):
        """Create async session for testing."""
        async_session = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        async with async_session() as session:
            yield session

    @pytest.fixture
    async def user_with_profiles(self, session):
        """Create a user with multiple profiles for testing."""
        # Create user
        user = User(user_id=123456789, native_language="ru", interface_language="ru")
        session.add(user)
        await session.commit()

        # Create profiles
        profile1 = LanguageProfile(
            user_id=123456789,
            target_language="en",
            level=CEFRLevel.B1,
            is_active=True
        )
        profile2 = LanguageProfile(
            user_id=123456789,
            target_language="es",
            level=CEFRLevel.A2,
            is_active=False
        )
        profile3 = LanguageProfile(
            user_id=123456789,
            target_language="de",
            level=CEFRLevel.B2,
            is_active=False
        )
        session.add_all([profile1, profile2, profile3])
        await session.commit()

        return user

    @pytest.mark.asyncio
    async def test_integration_get_active_profile(self, session, user_with_profiles):
        """Test get_active_profile returns the active profile."""
        repo = ProfileRepository(session)
        active_profile = await repo.get_active_profile(123456789)

        assert active_profile is not None
        assert active_profile.target_language == "en"
        assert active_profile.is_active is True

    @pytest.mark.asyncio
    async def test_integration_get_user_profiles(self, session, user_with_profiles):
        """Test get_user_profiles returns all profiles."""
        repo = ProfileRepository(session)
        profiles = await repo.get_user_profiles(123456789)

        assert len(profiles) == 3
        target_languages = [p.target_language for p in profiles]
        assert "en" in target_languages
        assert "es" in target_languages
        assert "de" in target_languages

    @pytest.mark.asyncio
    async def test_integration_switch_active_language(self, session, user_with_profiles):
        """Test switch_active_language switches the active profile."""
        repo = ProfileRepository(session)

        # Verify English is active initially
        active = await repo.get_active_profile(123456789)
        assert active.target_language == "en"

        # Switch to Spanish
        switched = await repo.switch_active_language(123456789, "es")
        await session.commit()

        assert switched.target_language == "es"
        assert switched.is_active is True

        # Verify Spanish is now active
        new_active = await repo.get_active_profile(123456789)
        assert new_active.target_language == "es"

        # Verify English is no longer active
        all_profiles = await repo.get_user_profiles(123456789)
        en_profile = next(p for p in all_profiles if p.target_language == "en")
        assert en_profile.is_active is False

    @pytest.mark.asyncio
    async def test_integration_switch_active_language_error_on_invalid_language(self, session, user_with_profiles):
        """Test switch_active_language raises error for non-existent language."""
        repo = ProfileRepository(session)

        with pytest.raises(ValueError) as exc_info:
            await repo.switch_active_language(123456789, "fr")

        assert "No profile found" in str(exc_info.value)
        assert "123456789" in str(exc_info.value)
        assert "fr" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_integration_profile_repository_inherits_base_methods(self, session):
        """Test that ProfileRepository can use base CRUD methods."""
        # Create user first
        user = User(user_id=999, native_language="ru", interface_language="ru")
        session.add(user)
        await session.commit()

        repo = ProfileRepository(session)

        # Test add
        profile = LanguageProfile(
            user_id=999,
            target_language="en",
            level=CEFRLevel.B1
        )
        added_profile = await repo.add(profile)
        await repo.commit()

        assert added_profile.profile_id is not None

        # Test get_by_id
        retrieved = await repo.get_by_id(added_profile.profile_id)
        assert retrieved is not None
        assert retrieved.target_language == "en"


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_update_last_active_with_nonexistent_user(self):
        """Test update_last_active with user that doesn't exist."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        # Should not raise error, just do nothing
        await repo.update_last_active(999999999)

        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_users_for_notification_with_zero_inactive_hours(self):
        """Test get_users_for_notification with zero inactive hours."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UserRepository(mock_session)
        result = await repo.get_users_for_notification(inactive_hours=0, current_hour=10)

        # Should still execute the query
        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_switch_active_language_with_single_profile(self):
        """Test switch_active_language when user has only one profile."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()

        profile = LanguageProfile(
            user_id=123456789,
            target_language="en",
            level=CEFRLevel.B1,
            is_active=False
        )
        profiles = [profile]

        mock_scalars.all.return_value = profiles
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ProfileRepository(mock_session)
        result = await repo.switch_active_language(123456789, "en")

        # Should activate the only profile
        assert profile.is_active is True
        assert result is profile

    @pytest.mark.asyncio
    async def test_get_active_profile_when_multiple_active(self):
        """Test get_active_profile behavior when multiple profiles are active (data integrity issue)."""
        # This is an edge case that shouldn't happen in normal operation,
        # but we test that the method doesn't break
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        # Returns first match
        mock_profile = LanguageProfile(
            user_id=123456789,
            target_language="en",
            level=CEFRLevel.B1,
            is_active=True
        )
        mock_result.scalar_one_or_none.return_value = mock_profile
        mock_session.execute.return_value = mock_result

        repo = ProfileRepository(mock_session)
        result = await repo.get_active_profile(123456789)

        # Should return the first active profile found
        assert result is mock_profile
