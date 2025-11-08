"""
WordStatistics ORM model for the Words application.

This module contains the model for:
- WordStatistics: Aggregated learning statistics for each word
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Integer, ForeignKey, String, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    pass


class WordStatistics(Base):
    """
    WordStatistics model representing aggregated learning statistics for a word.

    Tracks statistics for each combination of user_word, direction, and test_type.
    This allows tracking how well a user knows a word in different contexts
    (e.g., en->ru translation vs ru->en translation, or different test types).

    Attributes:
        stat_id: Auto-incrementing primary key
        user_word_id: Foreign key to user_words (CASCADE delete)
        direction: Translation direction (e.g., "en->ru", "ru->en")
        test_type: Type of test (e.g., "translation", "multiple_choice")
        correct_count: Number of consecutive correct answers
        total_attempts: Total number of attempts for this combination
        total_correct: Total number of correct answers (all time)
        total_errors: Total number of incorrect answers (all time)
        user_word: Relationship to UserWord
    """
    __tablename__ = "word_statistics"
    __table_args__ = (
        UniqueConstraint(
            'user_word_id', 'direction', 'test_type',
            name='uq_userword_direction_testtype'
        ),
        Index('idx_stats_user_word', 'user_word_id'),
    )

    stat_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_word_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user_words.user_word_id", ondelete="CASCADE"),
        nullable=False
    )
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    test_type: Mapped[str] = mapped_column(String(20), nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)
    total_correct: Mapped[int] = mapped_column(Integer, default=0)
    total_errors: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user_word: Mapped["UserWord"] = relationship(back_populates="statistics")
