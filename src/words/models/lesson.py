"""
Lesson and LessonAttempt ORM models for the Words application.

This module contains models for:
- Lesson: Learning sessions with progress tracking
- LessonAttempt: Individual word attempts within a lesson
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Integer, ForeignKey, String, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TZDateTime
from datetime import datetime, timezone

if TYPE_CHECKING:
    from typing import List


class Lesson(Base):
    """
    Lesson model representing a learning session.

    Tracks the overall progress of a lesson including how many words
    were tested and how many answers were correct or incorrect.

    Attributes:
        lesson_id: Auto-incrementing primary key
        profile_id: Foreign key to language_profiles (CASCADE delete)
        started_at: When the lesson was started (timezone-aware UTC)
        completed_at: When the lesson was completed (timezone-aware UTC, nullable)
        words_count: Total number of words in this lesson
        correct_answers: Number of correct answers in this lesson
        incorrect_answers: Number of incorrect answers in this lesson
        profile: Relationship to LanguageProfile
        attempts: List of lesson attempts (CASCADE delete)
    """
    __tablename__ = "lessons"
    __table_args__ = (
        Index('idx_lessons_profile', 'profile_id', 'started_at'),
    )

    lesson_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("language_profiles.profile_id", ondelete="CASCADE"),
        nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        TZDateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    words_count: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_answers: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    profile: Mapped["LanguageProfile"] = relationship(back_populates="lessons")
    attempts: Mapped[list["LessonAttempt"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan"
    )


class LessonAttempt(Base):
    """
    LessonAttempt model representing a single word attempt within a lesson.

    Records each individual attempt to answer a question about a word,
    including the user's answer, correct answer, and validation method.

    Attributes:
        attempt_id: Auto-incrementing primary key
        lesson_id: Foreign key to lessons (CASCADE delete)
        user_word_id: Foreign key to user_words
        direction: Translation direction (e.g., "en->ru", "ru->en")
        test_type: Type of test (e.g., "translation", "multiple_choice")
        user_answer: User's answer (nullable for skipped questions)
        correct_answer: The correct answer
        is_correct: Whether the user's answer was correct
        validation_method: How the answer was validated ("exact", "fuzzy", "llm")
        attempted_at: When the attempt was made (timezone-aware UTC)
        lesson: Relationship to Lesson
        user_word: Relationship to UserWord
    """
    __tablename__ = "lesson_attempts"
    __table_args__ = (
        Index('idx_attempts_lesson', 'lesson_id'),
        Index('idx_attempts_user_word', 'user_word_id'),
    )

    attempt_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lessons.lesson_id", ondelete="CASCADE"),
        nullable=False
    )
    user_word_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user_words.user_word_id"),
        nullable=False
    )
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    test_type: Mapped[str] = mapped_column(String(20), nullable=False)
    user_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    validation_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(
        TZDateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    lesson: Mapped["Lesson"] = relationship(back_populates="attempts")
    user_word: Mapped["UserWord"] = relationship()
