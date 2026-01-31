"""
Tests for Word and UserWord ORM models.

This module tests the Word and UserWord models, including:
- Word model creation and fields
- JSON fields functionality
- WordStatusEnum values
- UserWord model with spaced repetition fields
- Relationships between UserWord, Word, and LanguageProfile
- CASCADE delete behavior
- Timezone-aware datetime handling
- UNIQUE constraints
- Indexes
- Table creation
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, inspect, event as sa_event, text as sa_text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.words.models import Base, Word, WordStatusEnum, UserWord, User, LanguageProfile, CEFRLevel


class TestWordStatusEnum:
    """Tests for the WordStatusEnum."""

    def test_word_status_enum_has_all_statuses(self):
        """Test that WordStatusEnum contains all required status values."""
        statuses = [status.value for status in WordStatusEnum]
        assert "new" in statuses
        assert "learning" in statuses
        assert "reviewing" in statuses
        assert "mastered" in statuses
        assert len(statuses) == 4

    def test_word_status_enum_values_are_strings(self):
        """Test that all status values are strings for database storage."""
        for status in WordStatusEnum:
            assert isinstance(status.value, str)

    def test_word_status_enum_access(self):
        """Test that status values can be accessed by name."""
        assert WordStatusEnum.NEW.value == "new"
        assert WordStatusEnum.LEARNING.value == "learning"
        assert WordStatusEnum.REVIEWING.value == "reviewing"
        assert WordStatusEnum.MASTERED.value == "mastered"

    def test_word_status_enum_comparison(self):
        """Test that status enum members can be compared."""
        assert WordStatusEnum.NEW == WordStatusEnum.NEW
        assert WordStatusEnum.NEW != WordStatusEnum.LEARNING


class TestWordModel:
    """Tests for the Word model."""

    @pytest.mark.asyncio
    async def test_create_word_with_minimum_fields(self):
        """Test creating a Word with only required fields."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            word = Word(
                word="house",
                language="en"
            )
            session.add(word)
            await session.commit()
            await session.refresh(word)

            # Verify word was created
            assert word.word_id is not None
            assert word.word == "house"
            assert word.language == "en"
            assert word.level is None
            assert word.translations is None
            assert word.examples is None
            assert word.word_forms is None
            assert word.frequency_rank is None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_create_word_with_all_fields(self):
        """Test creating a Word with all fields populated."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            word = Word(
                word="house",
                language="en",
                level="B1",
                translations={"ru": ["дом"], "es": ["casa"]},
                examples=[
                    {"en": "My house is big", "ru": "Мой дом большой"},
                    {"en": "I live in a house", "ru": "Я живу в доме"}
                ],
                word_forms={"plural": "houses", "possessive": "house's"},
                frequency_rank=500
            )
            session.add(word)
            await session.commit()
            await session.refresh(word)

            # Verify all fields
            assert word.word_id is not None
            assert word.word == "house"
            assert word.language == "en"
            assert word.level == "B1"
            assert word.translations == {"ru": ["дом"], "es": ["casa"]}
            assert len(word.examples) == 2
            assert word.word_forms == {"plural": "houses", "possessive": "house's"}
            assert word.frequency_rank == 500

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_word_json_fields_work_correctly(self):
        """Test that JSON fields (translations, examples, word_forms) work correctly."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Test translations JSON
            word = Word(
                word="cat",
                language="en",
                translations={"ru": ["кот", "кошка"], "es": ["gato"]},
                examples=[
                    {"sentence": "The cat is sleeping", "translation": "Кот спит"}
                ],
                word_forms={"plural": "cats"}
            )
            session.add(word)
            await session.commit()
            await session.refresh(word)

            # Verify JSON data integrity
            assert isinstance(word.translations, dict)
            assert "ru" in word.translations
            assert len(word.translations["ru"]) == 2
            assert "кот" in word.translations["ru"]

            assert isinstance(word.examples, list)
            assert len(word.examples) == 1
            assert word.examples[0]["sentence"] == "The cat is sleeping"

            assert isinstance(word.word_forms, dict)
            assert word.word_forms["plural"] == "cats"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_word_unique_constraint_prevents_duplicates(self):
        """Test that UNIQUE constraint on (word, language) prevents duplicates."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create first word
            word1 = Word(word="dog", language="en")
            session.add(word1)
            await session.commit()

            # Try to create duplicate word with same word and language
            word2 = Word(word="dog", language="en", level="A1")  # Same word + language
            session.add(word2)

            # Should raise IntegrityError due to UNIQUE constraint
            with pytest.raises(IntegrityError):
                await session.commit()

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_word_unique_constraint_allows_same_word_different_language(self):
        """Test that same word in different languages is allowed."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create words with same spelling but different languages
            word_en = Word(word="chat", language="en")  # "chat" in English
            word_fr = Word(word="chat", language="fr")  # "chat" in French (means "cat")
            session.add_all([word_en, word_fr])
            await session.commit()

            # Verify both were created
            result = await session.execute(
                select(Word).where(Word.word == "chat")
            )
            words = result.scalars().all()
            assert len(words) == 2

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_word_can_be_queried_by_language_and_level(self):
        """Test that words can be queried by language and level."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create words with different levels
            words = [
                Word(word="hello", language="en", level="A1"),
                Word(word="house", language="en", level="A2"),
                Word(word="magnificent", language="en", level="C1"),
                Word(word="hola", language="es", level="A1"),
            ]
            session.add_all(words)
            await session.commit()

            # Query English A1 words
            result = await session.execute(
                select(Word).where(Word.language == "en", Word.level == "A1")
            )
            en_a1_words = result.scalars().all()
            assert len(en_a1_words) == 1
            assert en_a1_words[0].word == "hello"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_word_frequency_rank_ordering(self):
        """Test that words can be ordered by frequency rank."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create words with different frequency ranks
            words = [
                Word(word="the", language="en", frequency_rank=1),
                Word(word="be", language="en", frequency_rank=2),
                Word(word="to", language="en", frequency_rank=3),
                Word(word="of", language="en", frequency_rank=4),
            ]
            session.add_all(words)
            await session.commit()

            # Query and order by frequency
            result = await session.execute(
                select(Word)
                .where(Word.language == "en")
                .order_by(Word.frequency_rank)
            )
            ordered_words = result.scalars().all()

            assert len(ordered_words) == 4
            assert ordered_words[0].word == "the"
            assert ordered_words[1].word == "be"
            assert ordered_words[2].word == "to"
            assert ordered_words[3].word == "of"

        await engine.dispose()


class TestUserWordModel:
    """Tests for the UserWord model."""

    @pytest.mark.asyncio
    async def test_create_user_word_with_minimum_fields(self):
        """Test creating a UserWord with only required fields."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create prerequisite records
            user = User(user_id=1000, native_language="ru", interface_language="ru")
            session.add(user)
            await session.commit()

            profile = LanguageProfile(user_id=1000, target_language="en", level=CEFRLevel.B1)
            session.add(profile)
            await session.commit()

            word = Word(word="test", language="en")
            session.add(word)
            await session.commit()

            # Create UserWord
            user_word = UserWord(
                profile_id=profile.profile_id,
                word_id=word.word_id
            )
            session.add(user_word)
            await session.commit()
            await session.refresh(user_word)

            # Verify defaults
            assert user_word.user_word_id is not None
            assert user_word.profile_id == profile.profile_id
            assert user_word.word_id == word.word_id
            assert user_word.status == WordStatusEnum.NEW
            assert user_word.added_at is not None
            assert user_word.added_at.tzinfo is not None
            assert user_word.last_reviewed_at is None
            assert user_word.next_review_at is None
            assert user_word.review_interval == 0
            assert user_word.easiness_factor == 2.5
            assert user_word.created_at is not None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_create_user_word_with_all_fields(self):
        """Test creating a UserWord with all fields populated."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        now = datetime.now(timezone.utc)
        last_review = now - timedelta(days=2)
        next_review = now + timedelta(days=3)

        async with async_session() as session:
            # Create prerequisite records
            user = User(user_id=2000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=2000, target_language="en", level=CEFRLevel.B2)
            word = Word(word="advanced", language="en", level="B2")
            session.add_all([user, profile, word])
            await session.commit()

            # Create UserWord with all fields
            user_word = UserWord(
                profile_id=profile.profile_id,
                word_id=word.word_id,
                status=WordStatusEnum.REVIEWING,
                added_at=now - timedelta(days=30),
                last_reviewed_at=last_review,
                next_review_at=next_review,
                review_interval=5,
                easiness_factor=2.8
            )
            session.add(user_word)
            await session.commit()
            await session.refresh(user_word)

            # Verify all fields
            assert user_word.status == WordStatusEnum.REVIEWING
            assert user_word.last_reviewed_at is not None
            assert user_word.last_reviewed_at.tzinfo is not None
            assert user_word.next_review_at is not None
            assert user_word.next_review_at.tzinfo is not None
            assert user_word.review_interval == 5
            assert user_word.easiness_factor == 2.8

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_user_word_spaced_repetition_fields(self):
        """Test UserWord spaced repetition fields work correctly."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create prerequisite records
            user = User(user_id=3000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=3000, target_language="en", level=CEFRLevel.A1)
            word = Word(word="cat", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            # Create UserWord and simulate review progression
            user_word = UserWord(
                profile_id=profile.profile_id,
                word_id=word.word_id,
                status=WordStatusEnum.NEW,
                review_interval=0,
                easiness_factor=2.5
            )
            session.add(user_word)
            await session.commit()

            # Simulate first review (NEW -> LEARNING)
            user_word.status = WordStatusEnum.LEARNING
            user_word.last_reviewed_at = datetime.now(timezone.utc)
            user_word.review_interval = 1
            user_word.next_review_at = datetime.now(timezone.utc) + timedelta(days=1)
            await session.commit()

            # Simulate successful review (increase interval)
            user_word.review_interval = 3
            user_word.next_review_at = datetime.now(timezone.utc) + timedelta(days=3)
            user_word.easiness_factor = 2.6
            await session.commit()

            await session.refresh(user_word)

            # Verify spaced repetition data
            assert user_word.status == WordStatusEnum.LEARNING
            assert user_word.review_interval == 3
            assert user_word.easiness_factor == 2.6
            assert user_word.last_reviewed_at is not None
            assert user_word.next_review_at is not None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_user_word_datetime_fields_are_timezone_aware(self):
        """Test that datetime fields are timezone-aware."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Test with naive datetimes (should be converted to UTC)
        naive_added = datetime(2025, 1, 1, 10, 0, 0)
        naive_last_review = datetime(2025, 1, 5, 14, 30, 0)
        naive_next_review = datetime(2025, 1, 10, 14, 30, 0)

        async with async_session() as session:
            user = User(user_id=4000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=4000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="timezone", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(
                profile_id=profile.profile_id,
                word_id=word.word_id,
                added_at=naive_added,
                last_reviewed_at=naive_last_review,
                next_review_at=naive_next_review
            )
            session.add(user_word)
            await session.commit()
            await session.refresh(user_word)

            # Verify all datetime fields are timezone-aware
            assert user_word.added_at.tzinfo is not None
            assert user_word.added_at.tzinfo == timezone.utc
            assert user_word.last_reviewed_at.tzinfo is not None
            assert user_word.last_reviewed_at.tzinfo == timezone.utc
            assert user_word.next_review_at.tzinfo is not None
            assert user_word.next_review_at.tzinfo == timezone.utc

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_user_word_relationship_to_word(self):
        """Test UserWord relationship to Word."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=5000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=5000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="relationship", language="en", translations={"ru": ["отношение"]})
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            user_word_id = user_word.user_word_id

        # Query and load relationship
        async with async_session() as session:
            result = await session.execute(
                select(UserWord).where(UserWord.user_word_id == user_word_id)
            )
            user_word = result.scalar_one()

            # Load word relationship
            result = await session.execute(
                select(Word).where(Word.word_id == user_word.word_id)
            )
            word = result.scalar_one()

            assert word is not None
            assert word.word == "relationship"
            assert word.translations == {"ru": ["отношение"]}

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_user_word_relationship_to_language_profile(self):
        """Test UserWord relationship to LanguageProfile."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=6000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=6000, target_language="es", level=CEFRLevel.A2)
            word = Word(word="hola", language="es")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            user_word_id = user_word.user_word_id

        # Query and load relationship
        async with async_session() as session:
            result = await session.execute(
                select(UserWord).where(UserWord.user_word_id == user_word_id)
            )
            user_word = result.scalar_one()

            # Load profile relationship
            result = await session.execute(
                select(LanguageProfile).where(LanguageProfile.profile_id == user_word.profile_id)
            )
            profile = result.scalar_one()

            assert profile is not None
            assert profile.target_language == "es"
            assert profile.level == CEFRLevel.A2

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_user_word_unique_constraint_prevents_duplicates(self):
        """Test that UNIQUE constraint on (profile_id, word_id) prevents duplicates."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=7000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=7000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="unique", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            # Create first user_word
            user_word1 = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word1)
            await session.commit()

            # Try to create duplicate
            user_word2 = UserWord(
                profile_id=profile.profile_id,
                word_id=word.word_id,
                status=WordStatusEnum.LEARNING  # Different status doesn't matter
            )
            session.add(user_word2)

            # Should raise IntegrityError
            with pytest.raises(IntegrityError):
                await session.commit()

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_user_word_unique_constraint_allows_same_word_different_profiles(self):
        """Test that the same word can be in different profiles."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Create two users with profiles
            user1 = User(user_id=8000, native_language="ru", interface_language="ru")
            user2 = User(user_id=8001, native_language="es", interface_language="es")
            profile1 = LanguageProfile(user_id=8000, target_language="en", level=CEFRLevel.B1)
            profile2 = LanguageProfile(user_id=8001, target_language="en", level=CEFRLevel.A1)
            word = Word(word="shared", language="en")
            session.add_all([user1, user2, profile1, profile2, word])
            await session.commit()

            # Both profiles can have the same word
            user_word1 = UserWord(profile_id=profile1.profile_id, word_id=word.word_id)
            user_word2 = UserWord(profile_id=profile2.profile_id, word_id=word.word_id)
            session.add_all([user_word1, user_word2])
            await session.commit()

            # Verify both were created
            result = await session.execute(
                select(UserWord).where(UserWord.word_id == word.word_id)
            )
            user_words = result.scalars().all()
            assert len(user_words) == 2

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cascade_delete_word_removes_user_words(self):
        """Test that deleting a Word cascades to delete related UserWords."""
        # SQLite requires foreign keys to be enabled for CASCADE to work
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False}
        )

        # Enable foreign key support for SQLite
        @sa_event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            # Enable foreign keys for this connection
            await conn.execute(sa_text("PRAGMA foreign_keys=ON"))
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            # Enable foreign keys for this session
            await session.execute(sa_text("PRAGMA foreign_keys=ON"))

            user = User(user_id=9000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=9000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="cascade", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()

            word_id = word.word_id

            # Verify user_word exists
            result = await session.execute(
                select(UserWord).where(UserWord.word_id == word_id)
            )
            assert result.scalar_one_or_none() is not None

            # Delete word
            await session.delete(word)
            await session.commit()

            # Verify user_word was deleted (CASCADE)
            result = await session.execute(
                select(UserWord).where(UserWord.word_id == word_id)
            )
            assert result.scalar_one_or_none() is None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cascade_delete_profile_removes_user_words(self):
        """Test that deleting a LanguageProfile cascades to delete related UserWords."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=10000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=10000, target_language="en", level=CEFRLevel.B1)
            word1 = Word(word="first", language="en")
            word2 = Word(word="second", language="en")
            session.add_all([user, profile, word1, word2])
            await session.commit()

            user_word1 = UserWord(profile_id=profile.profile_id, word_id=word1.word_id)
            user_word2 = UserWord(profile_id=profile.profile_id, word_id=word2.word_id)
            session.add_all([user_word1, user_word2])
            await session.commit()

            profile_id = profile.profile_id

            # Verify user_words exist
            result = await session.execute(
                select(UserWord).where(UserWord.profile_id == profile_id)
            )
            assert len(result.scalars().all()) == 2

            # Delete profile
            await session.delete(profile)
            await session.commit()

            # Verify user_words were deleted (CASCADE)
            result = await session.execute(
                select(UserWord).where(UserWord.profile_id == profile_id)
            )
            assert len(result.scalars().all()) == 0

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_profile_can_access_user_words_through_relationship(self):
        """Test that LanguageProfile can access its UserWords through relationship."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=11000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=11000, target_language="en", level=CEFRLevel.B1)
            word1 = Word(word="apple", language="en")
            word2 = Word(word="banana", language="en")
            word3 = Word(word="cherry", language="en")
            session.add_all([user, profile, word1, word2, word3])
            await session.commit()

            user_word1 = UserWord(profile_id=profile.profile_id, word_id=word1.word_id)
            user_word2 = UserWord(profile_id=profile.profile_id, word_id=word2.word_id)
            user_word3 = UserWord(profile_id=profile.profile_id, word_id=word3.word_id)
            session.add_all([user_word1, user_word2, user_word3])
            await session.commit()

            profile_id = profile.profile_id

        # Query profile and access user_words
        async with async_session() as session:
            result = await session.execute(
                select(LanguageProfile).where(LanguageProfile.profile_id == profile_id)
            )
            profile = result.scalar_one()

            # Access user_words through relationship
            result = await session.execute(
                select(UserWord).where(UserWord.profile_id == profile.profile_id)
            )
            user_words = result.scalars().all()

            assert len(user_words) == 3

        await engine.dispose()


class TestTableCreation:
    """Tests for table creation and schema validation."""

    @pytest.mark.asyncio
    async def test_timestamp_mixin_integration_in_user_word(self):
        """Test that TimestampMixin is properly integrated in UserWord model."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=12000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=12000, target_language="en", level=CEFRLevel.B1)
            word = Word(word="timestamp", language="en")
            session.add_all([user, profile, word])
            await session.commit()

            user_word = UserWord(profile_id=profile.profile_id, word_id=word.word_id)
            session.add(user_word)
            await session.commit()
            await session.refresh(user_word)

            # Verify timestamps
            assert user_word.created_at is not None
            assert user_word.created_at.tzinfo is not None
            assert user_word.updated_at is not None
            assert user_word.updated_at.tzinfo is not None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_all_word_status_enum_values_can_be_stored(self):
        """Test that all WordStatusEnum values can be stored in the database."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            user = User(user_id=13000, native_language="ru", interface_language="ru")
            profile = LanguageProfile(user_id=13000, target_language="en", level=CEFRLevel.B1)
            words = [
                Word(word=f"word{i}", language="en")
                for i in range(4)
            ]
            session.add_all([user, profile] + words)
            await session.commit()

            # Create user_words with each status
            statuses = [
                WordStatusEnum.NEW,
                WordStatusEnum.LEARNING,
                WordStatusEnum.REVIEWING,
                WordStatusEnum.MASTERED
            ]

            user_words = []
            for word, status in zip(words, statuses):
                user_word = UserWord(
                    profile_id=profile.profile_id,
                    word_id=word.word_id,
                    status=status
                )
                user_words.append(user_word)
                session.add(user_word)

            await session.commit()

            # Verify all statuses were stored
            result = await session.execute(
                select(UserWord).where(UserWord.profile_id == profile.profile_id)
            )
            stored_user_words = result.scalars().all()

            stored_statuses = [uw.status for uw in stored_user_words]
            assert len(stored_statuses) == 4
            assert WordStatusEnum.NEW in stored_statuses
            assert WordStatusEnum.LEARNING in stored_statuses
            assert WordStatusEnum.REVIEWING in stored_statuses
            assert WordStatusEnum.MASTERED in stored_statuses

        await engine.dispose()
