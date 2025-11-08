"""
User and LanguageProfile ORM models for the Words application.

This module contains models for:
- User: Telegram users with their preferences and settings
- CEFRLevel: Enum for language proficiency levels (A1-C2)
- LanguageProfile: User's learning profiles for different target languages
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, String, Boolean, ForeignKey, Enum as SQLEnum, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin, TZDateTime
from datetime import datetime
import enum

if TYPE_CHECKING:
    from typing import List


class User(Base, TimestampMixin):
    """
    User model representing a Telegram user.

    Attributes:
        user_id: Telegram user ID (primary key)
        native_language: User's native language (ISO 639-1 code)
        interface_language: Bot interface language (ISO 639-1 code)
        last_active_at: Last activity timestamp (timezone-aware)
        notification_enabled: Whether notifications are enabled
        timezone: User's timezone (default: Europe/Moscow)
        profiles: List of language learning profiles
    """
    __tablename__ = "users"
    __table_args__ = (
        Index('idx_users_last_active', 'last_active_at'),
    )

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    native_language: Mapped[str] = mapped_column(String(10), nullable=False)
    interface_language: Mapped[str] = mapped_column(String(10), nullable=False)
    last_active_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")

    # Relationships
    profiles: Mapped[list["LanguageProfile"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )


class CEFRLevel(enum.Enum):
    """
    CEFR (Common European Framework of Reference) language proficiency levels.

    Levels:
        A1: Beginner
        A2: Elementary
        B1: Intermediate
        B2: Upper Intermediate
        C1: Advanced
        C2: Proficient
    """
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class LanguageProfile(Base, TimestampMixin):
    """
    LanguageProfile model representing a user's learning profile for a target language.

    Each user can have multiple profiles for different target languages.
    Only one profile per language can be active at a time.

    Attributes:
        profile_id: Auto-incrementing primary key
        user_id: Foreign key to users table
        target_language: Target language being learned (ISO 639-1 code)
        level: CEFR proficiency level (A1-C2)
        is_active: Whether this profile is currently active
        user: Relationship to User model
        user_words: List of words being learned in this profile
        lessons: List of lessons for this profile
    """
    __tablename__ = "language_profiles"
    __table_args__ = (
        UniqueConstraint('user_id', 'target_language', name='uq_user_target_language'),
        Index('idx_profiles_user_active', 'user_id', 'is_active'),
    )

    profile_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    level: Mapped[CEFRLevel] = mapped_column(SQLEnum(CEFRLevel), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="profiles")

    # TODO: Add these relationships when UserWord and Lesson models are created (Tasks 1.5 & 1.6):
    # user_words: Mapped[list["UserWord"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    # lessons: Mapped[list["Lesson"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
