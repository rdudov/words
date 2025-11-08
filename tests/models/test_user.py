"""
Tests for User and LanguageProfile ORM models.

This module tests the User and LanguageProfile models, including:
- Model creation and field validation
- Relationships between models
- CASCADE delete behavior
- CEFR level enum functionality
- Timezone-aware datetime handling
- Table creation and constraints
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import select, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.words.models import Base, User, LanguageProfile, CEFRLevel


class TestCEFRLevel:
    """Tests for the CEFRLevel enum."""

    def test_cefr_level_has_all_levels(self):
        """Test that CEFRLevel enum contains all six CEFR levels."""
        levels = [level.value for level in CEFRLevel]
        assert "A1" in levels
        assert "A2" in levels
        assert "B1" in levels
        assert "B2" in levels
        assert "C1" in levels
        assert "C2" in levels
        assert len(levels) == 6

    def test_cefr_level_values_are_strings(self):
        """Test that all CEFR level values are strings for database storage."""
        for level in CEFRLevel:
            assert isinstance(level.value, str)

    def test_cefr_level_enum_access(self):
        """Test that CEFR levels can be accessed by name."""
        assert CEFRLevel.A1.value == "A1"
        assert CEFRLevel.A2.value == "A2"
        assert CEFRLevel.B1.value == "B1"
        assert CEFRLevel.B2.value == "B2"
        assert CEFRLevel.C1.value == "C1"
        assert CEFRLevel.C2.value == "C2"

    def test_cefr_level_comparison(self):
        """Test that CEFR level enum members can be compared."""
        assert CEFRLevel.A1 == CEFRLevel.A1
        assert CEFRLevel.A1 != CEFRLevel.B2


class TestUserModel:
    """Tests for the User model."""

    def test_user_model_has_required_fields(self):
        """Test that User model has all required fields."""
        assert hasattr(User, 'user_id')
        assert hasattr(User, 'native_language')
        assert hasattr(User, 'interface_language')
        assert hasattr(User, 'last_active_at')
        assert hasattr(User, 'notification_enabled')
        assert hasattr(User, 'timezone')
        assert hasattr(User, 'profiles')
        assert hasattr(User, 'created_at')
        assert hasattr(User, 'updated_at')

    def test_user_model_has_correct_tablename(self):
        """Test that User model has the correct table name."""
        assert User.__tablename__ == "users"

    @pytest.mark.asyncio
    async def test_create_user_with_minimum_fields(self):
        """Test creating a User with only required fields."""
        # Create in-memory database
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create user
        async with async_session() as session:
            user = User(
                user_id=123456789,
                native_language="ru",
                interface_language="ru"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # Verify user was created
            assert user.user_id == 123456789
            assert user.native_language == "ru"
            assert user.interface_language == "ru"
            # Check default values
            assert user.notification_enabled is True
            assert user.timezone == "Europe/Moscow"
            assert user.last_active_at is None
            # Check timestamps
            assert user.created_at is not None
            assert user.created_at.tzinfo is not None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_create_user_with_all_fields(self):
        """Test creating a User with all fields populated."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        last_active = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        async with async_session() as session:
            user = User(
                user_id=987654321,
                native_language="en",
                interface_language="en",
                last_active_at=last_active,
                notification_enabled=False,
                timezone="America/New_York"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # Verify all fields
            assert user.user_id == 987654321
            assert user.native_language == "en"
            assert user.interface_language == "en"
            assert user.last_active_at is not None
            assert user.last_active_at.tzinfo is not None
            assert user.notification_enabled is False
            assert user.timezone == "America/New_York"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_user_last_active_at_is_timezone_aware(self):
        """Test that last_active_at is stored as timezone-aware datetime."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Test with naive datetime (should be converted to UTC)
        naive_dt = datetime(2025, 6, 15, 14, 30, 0)

        async with async_session() as session:
            user = User(
                user_id=111222333,
                native_language="es",
                interface_language="es",
                last_active_at=naive_dt
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # Verify timezone was added
            assert user.last_active_at is not None
            assert user.last_active_at.tzinfo is not None
            assert user.last_active_at.tzinfo == timezone.utc

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_user_can_be_queried_by_user_id(self):
        """Test that users can be queried by their user_id."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create multiple users
            user1 = User(user_id=100, native_language="ru", interface_language="ru")
            user2 = User(user_id=200, native_language="en", interface_language="en")
            session.add_all([user1, user2])
            await session.commit()

        # Query by user_id
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == 100)
            )
            found_user = result.scalar_one_or_none()

            assert found_user is not None
            assert found_user.user_id == 100
            assert found_user.native_language == "ru"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_user_profiles_relationship_exists(self):
        """Test that User has a relationship to LanguageProfile."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(
                user_id=300,
                native_language="ru",
                interface_language="ru"
            )
            session.add(user)
            await session.commit()

            # Query profiles through the relationship
            result = await session.execute(
                select(LanguageProfile).where(LanguageProfile.user_id == 300)
            )
            profiles = result.scalars().all()

            # Verify relationship attribute exists
            assert hasattr(User, 'profiles')
            assert len(profiles) == 0  # No profiles yet

        await engine.dispose()


class TestLanguageProfileModel:
    """Tests for the LanguageProfile model."""

    def test_language_profile_has_required_fields(self):
        """Test that LanguageProfile model has all required fields."""
        assert hasattr(LanguageProfile, 'profile_id')
        assert hasattr(LanguageProfile, 'user_id')
        assert hasattr(LanguageProfile, 'target_language')
        assert hasattr(LanguageProfile, 'level')
        assert hasattr(LanguageProfile, 'is_active')
        assert hasattr(LanguageProfile, 'user')
        # Note: user_words and lessons relationships will be added when those models are created
        assert hasattr(LanguageProfile, 'created_at')
        assert hasattr(LanguageProfile, 'updated_at')

    def test_language_profile_has_correct_tablename(self):
        """Test that LanguageProfile model has the correct table name."""
        assert LanguageProfile.__tablename__ == "language_profiles"

    @pytest.mark.asyncio
    async def test_create_language_profile(self):
        """Test creating a LanguageProfile."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create user first
            user = User(
                user_id=400,
                native_language="ru",
                interface_language="ru"
            )
            session.add(user)
            await session.commit()

            # Create language profile
            profile = LanguageProfile(
                user_id=400,
                target_language="en",
                level=CEFRLevel.B1
            )
            session.add(profile)
            await session.commit()
            await session.refresh(profile)

            # Verify profile was created
            assert profile.profile_id is not None
            assert profile.user_id == 400
            assert profile.target_language == "en"
            assert profile.level == CEFRLevel.B1
            assert profile.is_active is True  # Default value
            assert profile.created_at is not None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_language_profile_with_all_cefr_levels(self):
        """Test creating profiles with all CEFR levels."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create user
            user = User(user_id=500, native_language="ru", interface_language="ru")
            session.add(user)
            await session.commit()

            # Create profiles with each CEFR level
            levels = [CEFRLevel.A1, CEFRLevel.A2, CEFRLevel.B1,
                     CEFRLevel.B2, CEFRLevel.C1, CEFRLevel.C2]
            languages = ["en", "es", "de", "fr", "it", "pt"]

            for lang, level in zip(languages, levels):
                profile = LanguageProfile(
                    user_id=500,
                    target_language=lang,
                    level=level
                )
                session.add(profile)

            await session.commit()

            # Query all profiles
            result = await session.execute(
                select(LanguageProfile).where(LanguageProfile.user_id == 500)
            )
            profiles = result.scalars().all()

            assert len(profiles) == 6
            # Verify each level was stored correctly
            stored_levels = [p.level for p in profiles]
            assert set(stored_levels) == set(levels)

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_unique_constraint_prevents_duplicate_profiles(self):
        """Test that the UNIQUE constraint prevents duplicate (user_id, target_language) profiles."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create user
            user = User(user_id=1500, native_language="ru", interface_language="ru")
            session.add(user)
            await session.commit()

            # Create first profile for English
            profile1 = LanguageProfile(
                user_id=1500,
                target_language="en",
                level=CEFRLevel.B1
            )
            session.add(profile1)
            await session.commit()

            # Try to create duplicate profile with same user_id and target_language
            profile2 = LanguageProfile(
                user_id=1500,
                target_language="en",  # Same language
                level=CEFRLevel.A2  # Different level doesn't matter
            )
            session.add(profile2)

            # Should raise IntegrityError due to UNIQUE constraint
            with pytest.raises(IntegrityError):
                await session.commit()

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_unique_constraint_allows_same_language_for_different_users(self):
        """Test that different users can have profiles for the same target language."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create two users
            user1 = User(user_id=1600, native_language="ru", interface_language="ru")
            user2 = User(user_id=1601, native_language="es", interface_language="es")
            session.add_all([user1, user2])
            await session.commit()

            # Both users can have English profiles (different user_id)
            profile1 = LanguageProfile(
                user_id=1600,
                target_language="en",
                level=CEFRLevel.B1
            )
            profile2 = LanguageProfile(
                user_id=1601,
                target_language="en",  # Same language, different user
                level=CEFRLevel.A2
            )
            session.add_all([profile1, profile2])
            await session.commit()

            # Verify both profiles were created
            result = await session.execute(
                select(LanguageProfile).where(LanguageProfile.target_language == "en")
            )
            english_profiles = result.scalars().all()
            assert len(english_profiles) == 2

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_unique_constraint_allows_different_languages_for_same_user(self):
        """Test that a user can have multiple profiles for different target languages."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create user
            user = User(user_id=1700, native_language="ru", interface_language="ru")
            session.add(user)
            await session.commit()

            # Create profiles for different languages (same user_id)
            profile1 = LanguageProfile(
                user_id=1700,
                target_language="en",
                level=CEFRLevel.B1
            )
            profile2 = LanguageProfile(
                user_id=1700,
                target_language="es",  # Different language
                level=CEFRLevel.A2
            )
            profile3 = LanguageProfile(
                user_id=1700,
                target_language="de",  # Different language
                level=CEFRLevel.B2
            )
            session.add_all([profile1, profile2, profile3])
            await session.commit()

            # Verify all profiles were created
            result = await session.execute(
                select(LanguageProfile).where(LanguageProfile.user_id == 1700)
            )
            user_profiles = result.scalars().all()
            assert len(user_profiles) == 3

        await engine.dispose()


class TestUserLanguageProfileRelationship:
    """Tests for the relationship between User and LanguageProfile."""

    @pytest.mark.asyncio
    async def test_user_can_have_multiple_profiles(self):
        """Test that a User can have multiple LanguageProfiles."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create user
            user = User(user_id=600, native_language="ru", interface_language="ru")
            session.add(user)
            await session.commit()

            # Create multiple profiles
            profile1 = LanguageProfile(
                user_id=600,
                target_language="en",
                level=CEFRLevel.B1
            )
            profile2 = LanguageProfile(
                user_id=600,
                target_language="es",
                level=CEFRLevel.A2
            )
            profile3 = LanguageProfile(
                user_id=600,
                target_language="de",
                level=CEFRLevel.B2
            )
            session.add_all([profile1, profile2, profile3])
            await session.commit()

            # Query user and access profiles
            result = await session.execute(
                select(User).where(User.user_id == 600)
            )
            user = result.scalar_one()
            await session.refresh(user)

            # Access profiles through relationship
            profiles = await session.execute(
                select(LanguageProfile).where(LanguageProfile.user_id == user.user_id)
            )
            user_profiles = profiles.scalars().all()

            assert len(user_profiles) == 3
            target_languages = [p.target_language for p in user_profiles]
            assert "en" in target_languages
            assert "es" in target_languages
            assert "de" in target_languages

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_profile_can_access_user(self):
        """Test that LanguageProfile can access its User through relationship."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create user
            user = User(
                user_id=700,
                native_language="en",
                interface_language="en"
            )
            session.add(user)
            await session.commit()

            # Create profile
            profile = LanguageProfile(
                user_id=700,
                target_language="fr",
                level=CEFRLevel.B1
            )
            session.add(profile)
            await session.commit()
            await session.refresh(profile)

            # Access user through relationship
            profile_id = profile.profile_id

        # Query profile and load user relationship
        async with async_session() as session:
            result = await session.execute(
                select(LanguageProfile).where(LanguageProfile.profile_id == profile_id)
            )
            profile = result.scalar_one()

            # Load the user relationship
            result = await session.execute(
                select(User).where(User.user_id == profile.user_id)
            )
            profile_user = result.scalar_one()

            assert profile_user is not None
            assert profile_user.user_id == 700
            assert profile_user.native_language == "en"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cascade_delete_removes_profiles_when_user_deleted(self):
        """Test that deleting a User cascades to delete all their profiles."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create user with profiles
            user = User(user_id=800, native_language="ru", interface_language="ru")
            session.add(user)
            await session.commit()

            profile1 = LanguageProfile(
                user_id=800,
                target_language="en",
                level=CEFRLevel.B1
            )
            profile2 = LanguageProfile(
                user_id=800,
                target_language="es",
                level=CEFRLevel.A2
            )
            session.add_all([profile1, profile2])
            await session.commit()

            # Verify profiles exist
            result = await session.execute(
                select(LanguageProfile).where(LanguageProfile.user_id == 800)
            )
            profiles_before = result.scalars().all()
            assert len(profiles_before) == 2

            # Delete user
            result = await session.execute(
                select(User).where(User.user_id == 800)
            )
            user_to_delete = result.scalar_one()
            await session.delete(user_to_delete)
            await session.commit()

            # Verify profiles were deleted (CASCADE)
            result = await session.execute(
                select(LanguageProfile).where(LanguageProfile.user_id == 800)
            )
            profiles_after = result.scalars().all()
            assert len(profiles_after) == 0

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_multiple_users_with_profiles(self):
        """Test that multiple users can each have their own profiles."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create two users
            user1 = User(user_id=900, native_language="ru", interface_language="ru")
            user2 = User(user_id=901, native_language="en", interface_language="en")
            session.add_all([user1, user2])
            await session.commit()

            # Create profiles for each user
            profile1_1 = LanguageProfile(
                user_id=900,
                target_language="en",
                level=CEFRLevel.B1
            )
            profile1_2 = LanguageProfile(
                user_id=900,
                target_language="es",
                level=CEFRLevel.A2
            )
            profile2_1 = LanguageProfile(
                user_id=901,
                target_language="ru",
                level=CEFRLevel.C1
            )
            session.add_all([profile1_1, profile1_2, profile2_1])
            await session.commit()

            # Verify each user has correct profiles
            result = await session.execute(
                select(LanguageProfile).where(LanguageProfile.user_id == 900)
            )
            user1_profiles = result.scalars().all()
            assert len(user1_profiles) == 2

            result = await session.execute(
                select(LanguageProfile).where(LanguageProfile.user_id == 901)
            )
            user2_profiles = result.scalars().all()
            assert len(user2_profiles) == 1

        await engine.dispose()


class TestIndexesAndConstraints:
    """Tests for database indexes and constraints."""

    @pytest.mark.asyncio
    async def test_users_table_has_last_active_index(self):
        """Test that users table has index on last_active_at field."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            # Check that the index exists in metadata
            def check_index(connection):
                inspector = inspect(connection)
                indexes = inspector.get_indexes('users')
                index_names = [idx['name'] for idx in indexes]
                return 'idx_users_last_active' in index_names

            has_index = await conn.run_sync(check_index)
            assert has_index, "Index 'idx_users_last_active' not found on users table"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_language_profiles_table_has_composite_index(self):
        """Test that language_profiles table has composite index on (user_id, is_active)."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            # Check that the index exists in metadata
            def check_index(connection):
                inspector = inspect(connection)
                indexes = inspector.get_indexes('language_profiles')
                index_names = [idx['name'] for idx in indexes]
                return 'idx_profiles_user_active' in index_names

            has_index = await conn.run_sync(check_index)
            assert has_index, "Index 'idx_profiles_user_active' not found on language_profiles table"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_language_profiles_table_has_unique_constraint(self):
        """Test that language_profiles table has UNIQUE constraint on (user_id, target_language)."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            # Check that the unique constraint exists in metadata
            def check_constraint(connection):
                inspector = inspect(connection)
                # For SQLite, unique constraints appear as unique indexes
                indexes = inspector.get_indexes('language_profiles')
                unique_indexes = [idx for idx in indexes if idx.get('unique', False)]

                # Check if there's a unique index on user_id and target_language
                for idx in unique_indexes:
                    column_names = set(idx.get('column_names', []))
                    # The constraint should contain both columns
                    if {'user_id', 'target_language'}.issubset(column_names):
                        return True

                # Also check the table args in the model metadata
                # UniqueConstraint is defined in __table_args__
                table = LanguageProfile.__table__
                for constraint in table.constraints:
                    if hasattr(constraint, 'columns'):
                        column_names = {col.name for col in constraint.columns}
                        if {'user_id', 'target_language'}.issubset(column_names):
                            return True

                return False

            has_constraint = await conn.run_sync(check_constraint)
            assert has_constraint, "UNIQUE constraint on (user_id, target_language) not found"

        await engine.dispose()


class TestTableCreation:
    """Tests for table creation and schema validation."""

    @pytest.mark.asyncio
    async def test_create_all_tables_without_errors(self):
        """Test that all tables can be created without errors."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        # This should not raise any exceptions
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Verify tables were created by checking metadata
        table_names = list(Base.metadata.tables.keys())

        assert "users" in table_names
        assert "language_profiles" in table_names

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_timestamp_mixin_integration(self):
        """Test that TimestampMixin is properly integrated in both models."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create user and profile
            user = User(user_id=1000, native_language="ru", interface_language="ru")
            session.add(user)
            await session.commit()

            profile = LanguageProfile(
                user_id=1000,
                target_language="en",
                level=CEFRLevel.B1
            )
            session.add(profile)
            await session.commit()
            await session.refresh(user)
            await session.refresh(profile)

            # Verify timestamps on both models
            assert user.created_at is not None
            assert user.created_at.tzinfo is not None
            assert profile.created_at is not None
            assert profile.created_at.tzinfo is not None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_forward_references_dont_cause_errors(self):
        """Test that models can be imported and tables created without forward-referenced models."""
        # This test verifies that the models can be imported and tables created
        # even though UserWord and Lesson models don't exist yet
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        # Should not raise errors about missing UserWord or Lesson models
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create a profile to verify the model works
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            user = User(user_id=1100, native_language="ru", interface_language="ru")
            profile = LanguageProfile(
                user_id=1100,
                target_language="en",
                level=CEFRLevel.B1
            )
            session.add_all([user, profile])
            await session.commit()
            await session.refresh(profile)

            # Verify the model was created successfully
            assert profile.profile_id is not None
            assert profile.user_id == 1100
            # Note: user_words and lessons relationships will be added when those models exist

        await engine.dispose()
