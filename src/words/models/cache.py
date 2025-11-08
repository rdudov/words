"""
Cache ORM models for the Words application.

This module contains models for:
- CachedTranslation: Cache for translation API responses to reduce external API calls
- CachedValidation: Cache for LLM validation results to speed up repeated answers
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, JSON, Text, Boolean, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TZDateTime
from datetime import datetime, timezone

if TYPE_CHECKING:
    from typing import Dict, Any


class CachedTranslation(Base):
    """
    CachedTranslation model for caching translation API responses.

    Caches translations to reduce external API calls and improve response time.
    Supports optional TTL (Time To Live) via expires_at field.

    Attributes:
        cache_id: Auto-incrementing primary key
        word: The word to translate (max 255 chars)
        source_language: Source language code (ISO 639-1, e.g., "en")
        target_language: Target language code (ISO 639-1, e.g., "ru")
        translation_data: JSON dict containing translation results from API
        cached_at: When the translation was cached (timezone-aware UTC)
        expires_at: Optional expiration timestamp for cache invalidation (timezone-aware UTC)
    """
    __tablename__ = "cached_translations"
    __table_args__ = (
        UniqueConstraint('word', 'source_language', 'target_language', name='uq_translation_cache'),
        Index('idx_cached_translations_word', 'word'),
        Index('idx_cached_translations_languages', 'source_language', 'target_language'),
        Index('idx_cached_translations_expires', 'expires_at'),
    )

    cache_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(255), nullable=False)
    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    translation_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    cached_at: Mapped[datetime] = mapped_column(
        TZDateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)


class CachedValidation(Base):
    """
    CachedValidation model for caching LLM validation results.

    Caches validation results to avoid repeated LLM API calls for identical answers.
    Stores validation for both forward (target->native) and backward (native->target) directions.

    Attributes:
        validation_id: Auto-incrementing primary key
        word_id: Foreign key to words table (CASCADE delete)
        direction: Validation direction ("forward" or "backward")
        expected_answer: The correct/expected answer
        user_answer: The user's submitted answer
        is_correct: Whether the answer was validated as correct
        llm_comment: Optional LLM feedback/explanation as text
        cached_at: When the validation was cached (timezone-aware UTC)
        word: Relationship to Word model
    """
    __tablename__ = "cached_validations"
    __table_args__ = (
        UniqueConstraint(
            'word_id', 'direction', 'expected_answer', 'user_answer',
            name='uq_validation_cache'
        ),
        Index('idx_cached_validations_word', 'word_id'),
        Index('idx_cached_validations_direction', 'word_id', 'direction'),
    )

    validation_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("words.word_id", ondelete="CASCADE"),
        nullable=False
    )
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    expected_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    user_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    llm_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    cached_at: Mapped[datetime] = mapped_column(
        TZDateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    word: Mapped["Word"] = relationship()
