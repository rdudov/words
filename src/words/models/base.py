"""
Base ORM models and mixins for the Words application.

This module provides the declarative base class for all ORM models
and common mixins like timestamp fields.
"""

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, TypeDecorator
from datetime import datetime, timezone


class TZDateTime(TypeDecorator):
    """TypeDecorator that ensures datetime objects are timezone-aware.

    This decorator stores datetimes as UTC and ensures they are always
    timezone-aware when retrieved from the database, even with SQLite
    which doesn't natively support timezone-aware datetimes.
    """
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert timezone-aware datetime to UTC before storing."""
        if value is not None:
            if value.tzinfo is None:
                # If naive datetime, assume it's UTC
                value = value.replace(tzinfo=timezone.utc)
            else:
                # Convert to UTC
                value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        """Ensure retrieved datetime is timezone-aware (UTC)."""
        if value is not None and value.tzinfo is None:
            # Make naive datetime timezone-aware (UTC)
            value = value.replace(tzinfo=timezone.utc)
        return value


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all ORM models.

    Inherits from AsyncAttrs to enable async attribute loading
    and DeclarativeBase for SQLAlchemy ORM functionality.
    """
    pass


class TimestampMixin:
    """Mixin for created_at/updated_at timestamps.

    Add this mixin to any model that needs automatic timestamp tracking.
    created_at is set once on creation, updated_at is updated on every modification.
    All timestamps are timezone-aware (UTC).
    """
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        TZDateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True
    )
