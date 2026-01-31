"""
Comprehensive tests for UserService.

Tests cover:
- UserService initialization
- User registration
- Language profile creation
- Getting users
- Switching active languages
- Updating last active timestamp
- Integration tests with actual database
- Edge cases and error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.words.services.user import UserService
from src.words.repositories.user import UserRepository, ProfileRepository
from src.words.models import Base, User, LanguageProfile, CEFRLevel


class TestUserServiceInitialization:
    """Tests for UserService initialization."""

    @pytest.mark.asyncio
    async def test_user_service_initialization(self):
        """Test that UserService can be initialized with repositories."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        service = UserService(mock_user_repo, mock_profile_repo)

        assert service.user_repo is mock_user_repo
        assert service.profile_repo is mock_profile_repo


class TestRegisterUser:
    """Tests for register_user method."""

    @pytest.mark.asyncio
    async def test_register_user_creates_user_with_correct_attributes(self):
        """Test that register_user creates user with correct attributes."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        # Mock the add method to return the user
        mock_user = User(
            user_id=123456789,
            native_language="ru",
            interface_language="en",
            last_active_at=datetime.now(timezone.utc)
        )
        mock_user_repo.add.return_value = mock_user
        mock_user_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        with patch('src.words.services.user.logger') as mock_logger:
            result = await service.register_user(
                user_id=123456789,
                native_language="ru",
                interface_language="en"
            )

            # Verify user was added
            mock_user_repo.add.assert_called_once()
            mock_user_repo.commit.assert_called_once()

            # Verify logger was called
            mock_logger.info.assert_called_once_with(
                "user_registered",
                user_id=123456789,
                native_language="ru"
            )

            # Verify result
            assert result.user_id == 123456789
            assert result.native_language == "ru"
            assert result.interface_language == "en"

    @pytest.mark.asyncio
    async def test_register_user_sets_timezone_aware_last_active(self):
        """Test that register_user sets timezone-aware last_active_at."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        captured_user = None

        async def capture_user(user):
            nonlocal captured_user
            captured_user = user
            return user

        mock_user_repo.add.side_effect = capture_user
        mock_user_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        with patch('src.words.services.user.logger'):
            await service.register_user(
                user_id=123456789,
                native_language="ru",
                interface_language="ru"
            )

            # Verify last_active_at is timezone-aware
            assert captured_user.last_active_at is not None
            assert captured_user.last_active_at.tzinfo is not None
            assert captured_user.last_active_at.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_register_user_commits_transaction(self):
        """Test that register_user commits the transaction."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_user = User(user_id=123456789, native_language="ru", interface_language="ru")
        mock_user_repo.add.return_value = mock_user
        mock_user_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        with patch('src.words.services.user.logger'):
            await service.register_user(123456789, "ru", "ru")

            mock_user_repo.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_logs_registration(self):
        """Test that register_user logs the registration event."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_user = User(user_id=123456789, native_language="ru", interface_language="en")
        mock_user_repo.add.return_value = mock_user
        mock_user_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        with patch('src.words.services.user.logger') as mock_logger:
            await service.register_user(123456789, "ru", "en")

            mock_logger.info.assert_called_once_with(
                "user_registered",
                user_id=123456789,
                native_language="ru"
            )


class TestCreateLanguageProfile:
    """Tests for create_language_profile method."""

    @pytest.mark.asyncio
    async def test_create_language_profile_creates_profile_with_correct_attributes(self):
        """Test that create_language_profile creates profile with correct attributes."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        # Mock existing profiles
        mock_profile_repo.get_user_profiles.return_value = []

        # Mock add method
        mock_profile = LanguageProfile(
            user_id=123456789,
            target_language="en",
            level=CEFRLevel.B1,
            is_active=True
        )
        mock_profile_repo.add.return_value = mock_profile
        mock_profile_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        with patch('src.words.services.user.logger') as mock_logger:
            result = await service.create_language_profile(
                user_id=123456789,
                target_language="en",
                level="B1"
            )

            # Verify profile was added
            mock_profile_repo.add.assert_called_once()
            mock_profile_repo.commit.assert_called_once()

            # Verify logger was called
            mock_logger.info.assert_called_once_with(
                "profile_created",
                user_id=123456789,
                language="en",
                level="B1"
            )

            # Verify result
            assert result.user_id == 123456789
            assert result.target_language == "en"
            assert result.level == CEFRLevel.B1
            assert result.is_active is True

    @pytest.mark.asyncio
    async def test_create_language_profile_deactivates_existing_profiles(self):
        """Test that create_language_profile deactivates existing profiles."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        # Mock deactivate_all_profiles method
        mock_profile_repo.deactivate_all_profiles.return_value = None

        # Mock add method
        new_profile = LanguageProfile(
            user_id=123456789,
            target_language="en",
            level=CEFRLevel.B1,
            is_active=True
        )
        mock_profile_repo.add.return_value = new_profile
        mock_profile_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        with patch('src.words.services.user.logger'):
            await service.create_language_profile(123456789, "en", "B1")

            # Verify deactivate_all_profiles was called
            mock_profile_repo.deactivate_all_profiles.assert_called_once_with(123456789)

    @pytest.mark.asyncio
    async def test_create_language_profile_parses_level_string(self):
        """Test that create_language_profile correctly parses level string to enum."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_profile_repo.get_user_profiles.return_value = []

        captured_profile = None

        async def capture_profile(profile):
            nonlocal captured_profile
            captured_profile = profile
            return profile

        mock_profile_repo.add.side_effect = capture_profile
        mock_profile_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        with patch('src.words.services.user.logger'):
            await service.create_language_profile(123456789, "en", "A1")

            # Verify level was converted to enum
            assert captured_profile.level == CEFRLevel.A1
            assert isinstance(captured_profile.level, CEFRLevel)

    @pytest.mark.asyncio
    async def test_create_language_profile_logs_creation(self):
        """Test that create_language_profile logs the creation event."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_profile_repo.get_user_profiles.return_value = []
        mock_profile = LanguageProfile(
            user_id=123456789,
            target_language="es",
            level=CEFRLevel.C1,
            is_active=True
        )
        mock_profile_repo.add.return_value = mock_profile
        mock_profile_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        with patch('src.words.services.user.logger') as mock_logger:
            await service.create_language_profile(123456789, "es", "C1")

            mock_logger.info.assert_called_once_with(
                "profile_created",
                user_id=123456789,
                language="es",
                level="C1"
            )


class TestGetUser:
    """Tests for get_user method."""

    @pytest.mark.asyncio
    async def test_get_user_returns_existing_user(self):
        """Test that get_user returns existing user."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_user = User(user_id=123456789, native_language="ru", interface_language="ru")
        mock_user_repo.get_by_telegram_id.return_value = mock_user

        service = UserService(mock_user_repo, mock_profile_repo)

        result = await service.get_user(123456789)

        assert result is mock_user
        mock_user_repo.get_by_telegram_id.assert_called_once_with(123456789)

    @pytest.mark.asyncio
    async def test_get_user_returns_none_when_user_not_found(self):
        """Test that get_user returns None when user doesn't exist."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_user_repo.get_by_telegram_id.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        result = await service.get_user(999999999)

        assert result is None
        mock_user_repo.get_by_telegram_id.assert_called_once_with(999999999)

    @pytest.mark.asyncio
    async def test_get_user_does_not_create_new_user(self):
        """Test that get_user doesn't create a new user when not found."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_user_repo.get_by_telegram_id.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        await service.get_user(999999999)

        # Verify add and commit were not called
        mock_user_repo.add.assert_not_called()
        mock_user_repo.commit.assert_not_called()


class TestSwitchActiveLanguage:
    """Tests for switch_active_language method."""

    @pytest.mark.asyncio
    async def test_switch_active_language_switches_profile(self):
        """Test that switch_active_language switches the active profile."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_profile = LanguageProfile(
            user_id=123456789,
            target_language="es",
            level=CEFRLevel.B1,
            is_active=True
        )
        mock_profile_repo.switch_active_language.return_value = mock_profile
        mock_profile_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        with patch('src.words.services.user.logger') as mock_logger:
            result = await service.switch_active_language(123456789, "es")

            # Verify repository method was called
            mock_profile_repo.switch_active_language.assert_called_once_with(123456789, "es")
            mock_profile_repo.commit.assert_called_once()

            # Verify logger was called
            mock_logger.info.assert_called_once_with(
                "language_switched",
                user_id=123456789,
                language="es"
            )

            # Verify result
            assert result is mock_profile

    @pytest.mark.asyncio
    async def test_switch_active_language_commits_transaction(self):
        """Test that switch_active_language commits the transaction."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_profile = LanguageProfile(
            user_id=123456789,
            target_language="fr",
            level=CEFRLevel.A2,
            is_active=True
        )
        mock_profile_repo.switch_active_language.return_value = mock_profile
        mock_profile_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        with patch('src.words.services.user.logger'):
            await service.switch_active_language(123456789, "fr")

            mock_profile_repo.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_active_language_logs_switch(self):
        """Test that switch_active_language logs the switch event."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_profile = LanguageProfile(
            user_id=123456789,
            target_language="de",
            level=CEFRLevel.B2,
            is_active=True
        )
        mock_profile_repo.switch_active_language.return_value = mock_profile
        mock_profile_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        with patch('src.words.services.user.logger') as mock_logger:
            await service.switch_active_language(123456789, "de")

            mock_logger.info.assert_called_once_with(
                "language_switched",
                user_id=123456789,
                language="de"
            )

    @pytest.mark.asyncio
    async def test_switch_active_language_propagates_error(self):
        """Test that switch_active_language propagates ValueError from repository."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        # Mock repository to raise ValueError
        mock_profile_repo.switch_active_language.side_effect = ValueError(
            "No profile found for user 123456789 with target language 'invalid'"
        )

        service = UserService(mock_user_repo, mock_profile_repo)

        with pytest.raises(ValueError) as exc_info:
            await service.switch_active_language(123456789, "invalid")

        assert "No profile found" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)


class TestUpdateLastActive:
    """Tests for update_last_active method."""

    @pytest.mark.asyncio
    async def test_update_last_active_calls_repository(self):
        """Test that update_last_active calls repository method."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_user_repo.update_last_active.return_value = None
        mock_user_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        await service.update_last_active(123456789)

        mock_user_repo.update_last_active.assert_called_once_with(123456789)
        mock_user_repo.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_last_active_commits_transaction(self):
        """Test that update_last_active commits the transaction."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_user_repo.update_last_active.return_value = None
        mock_user_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        await service.update_last_active(123456789)

        mock_user_repo.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_last_active_handles_nonexistent_user(self):
        """Test that update_last_active handles nonexistent user gracefully."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        # Repository method should handle this gracefully (as per Task 2.2)
        mock_user_repo.update_last_active.return_value = None
        mock_user_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        # Should not raise error
        await service.update_last_active(999999999)

        mock_user_repo.update_last_active.assert_called_once_with(999999999)


class TestUserServiceIntegration:
    """Integration tests for UserService with actual database."""

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
    async def service(self, session):
        """Create UserService with real repositories."""
        user_repo = UserRepository(session)
        profile_repo = ProfileRepository(session)
        return UserService(user_repo, profile_repo)

    @pytest.mark.asyncio
    async def test_integration_register_user_and_retrieve(self, service):
        """Test registering a user and retrieving it."""
        with patch('src.words.services.user.logger'):
            # Register user
            user = await service.register_user(
                user_id=123456789,
                native_language="ru",
                interface_language="en"
            )

            assert user.user_id == 123456789
            assert user.native_language == "ru"
            assert user.interface_language == "en"
            assert user.last_active_at is not None

            # Retrieve user
            retrieved = await service.get_user(123456789)
            assert retrieved is not None
            assert retrieved.user_id == 123456789

    @pytest.mark.asyncio
    async def test_integration_create_language_profile(self, service, session):
        """Test creating a language profile."""
        with patch('src.words.services.user.logger'):
            # First create a user
            await service.register_user(123456789, "ru", "ru")

            # Create language profile
            profile = await service.create_language_profile(
                user_id=123456789,
                target_language="en",
                level="B1"
            )

            assert profile.user_id == 123456789
            assert profile.target_language == "en"
            assert profile.level == CEFRLevel.B1
            assert profile.is_active is True

    @pytest.mark.asyncio
    async def test_integration_create_multiple_profiles_only_one_active(self, service):
        """Test creating multiple profiles ensures only one is active."""
        with patch('src.words.services.user.logger'):
            # Create user
            await service.register_user(123456789, "ru", "ru")

            # Create first profile
            profile1 = await service.create_language_profile(123456789, "en", "B1")
            assert profile1.is_active is True

            # Create second profile
            profile2 = await service.create_language_profile(123456789, "es", "A2")
            assert profile2.is_active is True

            # First profile should now be inactive
            # Need to refresh from database to see the change
            user = await service.get_user(123456789)
            en_profile = next(p for p in user.profiles if p.target_language == "en")
            es_profile = next(p for p in user.profiles if p.target_language == "es")

            assert en_profile.is_active is False
            assert es_profile.is_active is True

    @pytest.mark.asyncio
    async def test_integration_switch_active_language(self, service):
        """Test switching active language between profiles."""
        with patch('src.words.services.user.logger'):
            # Create user and two profiles
            await service.register_user(123456789, "ru", "ru")
            await service.create_language_profile(123456789, "en", "B1")
            await service.create_language_profile(123456789, "es", "A2")

            # Switch back to English
            switched = await service.switch_active_language(123456789, "en")

            assert switched.target_language == "en"
            assert switched.is_active is True

            # Verify Spanish is inactive
            user = await service.get_user(123456789)
            es_profile = next(p for p in user.profiles if p.target_language == "es")
            assert es_profile.is_active is False

    @pytest.mark.asyncio
    async def test_integration_update_last_active(self, service, session):
        """Test updating last active timestamp."""
        with patch('src.words.services.user.logger'):
            # Create user
            user = await service.register_user(123456789, "ru", "ru")
            original_time = user.last_active_at

            # Wait a tiny bit to ensure time difference
            import asyncio
            await asyncio.sleep(0.01)

            # Update last active
            await service.update_last_active(123456789)

            # Retrieve updated user
            updated_user = await service.get_user(123456789)
            assert updated_user.last_active_at > original_time

    @pytest.mark.asyncio
    async def test_integration_complete_user_workflow(self, service):
        """Test complete user workflow: register, create profiles, switch languages."""
        with patch('src.words.services.user.logger'):
            # Step 1: Register user
            user = await service.register_user(
                user_id=123456789,
                native_language="ru",
                interface_language="ru"
            )
            assert user.user_id == 123456789

            # Step 2: Create first language profile
            profile_en = await service.create_language_profile(123456789, "en", "B1")
            assert profile_en.is_active is True

            # Step 3: Create second language profile
            profile_es = await service.create_language_profile(123456789, "es", "A2")
            assert profile_es.is_active is True

            # Step 4: Create third language profile
            profile_de = await service.create_language_profile(123456789, "de", "B2")
            assert profile_de.is_active is True

            # Step 5: Switch back to English
            switched = await service.switch_active_language(123456789, "en")
            assert switched.target_language == "en"
            assert switched.is_active is True

            # Step 6: Update last active
            await service.update_last_active(123456789)

            # Step 7: Verify final state
            final_user = await service.get_user(123456789)
            assert final_user is not None
            assert len(final_user.profiles) == 3

            # Verify only English is active
            active_profiles = [p for p in final_user.profiles if p.is_active]
            assert len(active_profiles) == 1
            assert active_profiles[0].target_language == "en"


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_create_language_profile_with_invalid_level(self):
        """Test that create_language_profile raises error with invalid level."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_profile_repo.get_user_profiles.return_value = []

        service = UserService(mock_user_repo, mock_profile_repo)

        with pytest.raises(KeyError):
            await service.create_language_profile(123456789, "en", "INVALID")

    @pytest.mark.asyncio
    async def test_switch_active_language_with_nonexistent_language(self):
        """Test that switch_active_language raises error for nonexistent language."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_profile_repo.switch_active_language.side_effect = ValueError(
            "No profile found for user 123456789 with target language 'fr'"
        )

        service = UserService(mock_user_repo, mock_profile_repo)

        with pytest.raises(ValueError) as exc_info:
            await service.switch_active_language(123456789, "fr")

        assert "No profile found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_with_negative_user_id(self):
        """Test get_user with negative user ID."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_user_repo.get_by_telegram_id.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        result = await service.get_user(-123456789)

        # Should still call repository method
        mock_user_repo.get_by_telegram_id.assert_called_once_with(-123456789)
        assert result is None

    @pytest.mark.asyncio
    async def test_register_user_with_different_interface_and_native_languages(self):
        """Test registering user with different interface and native languages."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_user = User(user_id=123456789, native_language="ru", interface_language="en")
        mock_user_repo.add.return_value = mock_user
        mock_user_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        with patch('src.words.services.user.logger'):
            result = await service.register_user(123456789, "ru", "en")

            assert result.native_language == "ru"
            assert result.interface_language == "en"

    @pytest.mark.asyncio
    async def test_create_language_profile_when_no_existing_profiles(self):
        """Test creating language profile when user has no existing profiles."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        # No existing profiles
        mock_profile_repo.get_user_profiles.return_value = []

        mock_profile = LanguageProfile(
            user_id=123456789,
            target_language="en",
            level=CEFRLevel.A1,
            is_active=True
        )
        mock_profile_repo.add.return_value = mock_profile
        mock_profile_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        with patch('src.words.services.user.logger'):
            result = await service.create_language_profile(123456789, "en", "A1")

            # Should succeed without errors
            assert result.is_active is True
            assert result.target_language == "en"

    @pytest.mark.asyncio
    async def test_all_cefr_levels_supported(self):
        """Test that all CEFR levels can be used in create_language_profile."""
        mock_user_repo = AsyncMock(spec=UserRepository)
        mock_profile_repo = AsyncMock(spec=ProfileRepository)

        mock_profile_repo.get_user_profiles.return_value = []
        mock_profile_repo.commit.return_value = None

        service = UserService(mock_user_repo, mock_profile_repo)

        levels = ["A1", "A2", "B1", "B2", "C1", "C2"]

        for level in levels:
            mock_profile = LanguageProfile(
                user_id=123456789,
                target_language="en",
                level=CEFRLevel[level],
                is_active=True
            )
            mock_profile_repo.add.return_value = mock_profile

            with patch('src.words.services.user.logger'):
                result = await service.create_language_profile(123456789, "en", level)

                assert result.level == CEFRLevel[level]
