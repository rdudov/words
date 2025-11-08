"""
Word and UserWord ORM models for the Words application.

This module contains models for:
- Word: Individual words in the database with translations, examples, and metadata
- WordStatusEnum: Enum for word learning status (NEW, LEARNING, REVIEWING, MASTERED)
- UserWord: User's personal word learning progress with spaced repetition data
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, JSON, ForeignKey, Enum as SQLEnum, UniqueConstraint, Index, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin, TZDateTime
from datetime import datetime, timezone
import enum

if TYPE_CHECKING:
    from typing import List, Dict, Any


class Word(Base):
    """
    Word model representing a word in the database.

    Stores word data including translations, examples, word forms,
    and frequency information for language learning.

    Attributes:
        word_id: Auto-incrementing primary key
        word: The word itself (e.g., "house", "cat")
        language: Language code (ISO 639-1, e.g., "en", "ru")
        level: CEFR level (A1-C2) if applicable
        translations: JSON dict of translations {"en": ["house", "home"], "ru": ["дом"]}
        examples: JSON list of example sentences
        word_forms: JSON dict of word forms (plural, past tense, etc.)
        frequency_rank: Frequency ranking (lower = more common)
    """
    __tablename__ = "words"
    __table_args__ = (
        UniqueConstraint('word', 'language', name='uq_word_language'),
        Index('idx_words_language_level', 'language', 'level'),
        Index('idx_words_frequency', 'language', 'frequency_rank'),
    )

    word_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    level: Mapped[str | None] = mapped_column(String(2), nullable=True)
    translations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    examples: Mapped[list | None] = mapped_column(JSON, nullable=True)
    word_forms: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    frequency_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)


class WordStatusEnum(enum.Enum):
    """
    Word learning status enum.

    Represents the current learning state of a word in the spaced repetition system.

    Values:
        NEW: Word was just added, not yet reviewed
        LEARNING: Word is being actively learned (early reviews)
        REVIEWING: Word is in regular review cycle
        MASTERED: Word has been successfully memorized
    """
    NEW = "new"
    LEARNING = "learning"
    REVIEWING = "reviewing"
    MASTERED = "mastered"


class UserWord(Base, TimestampMixin):
    """
    UserWord model representing a user's learning progress for a specific word.

    Tracks spaced repetition data and learning statistics for each word
    in a user's language profile. Implements the SuperMemo SM-2 algorithm
    for optimal review scheduling.

    Attributes:
        user_word_id: Auto-incrementing primary key
        profile_id: Foreign key to language_profiles (CASCADE delete)
        word_id: Foreign key to words (CASCADE delete)
        status: Current learning status (WordStatusEnum)
        added_at: When the word was added (timezone-aware UTC)
        last_reviewed_at: Last review timestamp (timezone-aware UTC)
        next_review_at: Next scheduled review (timezone-aware UTC)
        review_interval: Current review interval in days
        easiness_factor: SM-2 easiness factor (default 2.5)
        profile: Relationship to LanguageProfile
        word: Relationship to Word
        statistics: List of learning statistics for this word
    """
    __tablename__ = "user_words"
    __table_args__ = (
        UniqueConstraint('profile_id', 'word_id', name='uq_profile_word'),
        Index('idx_user_words_profile', 'profile_id'),
        Index('idx_user_words_status', 'profile_id', 'status'),
        Index('idx_user_words_next_review', 'profile_id', 'next_review_at'),
    )

    user_word_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("language_profiles.profile_id", ondelete="CASCADE"),
        nullable=False
    )
    word_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("words.word_id", ondelete="CASCADE"),
        nullable=False
    )
    status: Mapped[WordStatusEnum] = mapped_column(
        SQLEnum(WordStatusEnum),
        default=WordStatusEnum.NEW
    )
    added_at: Mapped[datetime] = mapped_column(
        TZDateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    last_reviewed_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    review_interval: Mapped[int] = mapped_column(Integer, default=0)
    easiness_factor: Mapped[float] = mapped_column(Float, default=2.5)

    # Relationships
    profile: Mapped["LanguageProfile"] = relationship(back_populates="user_words")
    word: Mapped["Word"] = relationship()
    statistics: Mapped[list["WordStatistics"]] = relationship(
        back_populates="user_word",
        cascade="all, delete-orphan"
    )
