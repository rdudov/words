"""
Base repository pattern implementation for the Words application.

This module provides a generic BaseRepository class with common CRUD operations
using SQLAlchemy async sessions. All specific repositories should inherit from this base.
"""

from typing import TypeVar, Generic, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.inspection import inspect

T = TypeVar('T', bound=DeclarativeBase)


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations.

    Provides generic async CRUD operations for SQLAlchemy models.
    Use this as a base class for specific model repositories.

    Type Parameters:
        T: The SQLAlchemy model type this repository manages

    Attributes:
        session: AsyncSession for database operations
        model: The SQLAlchemy model class

    Example:
        >>> class UserRepository(BaseRepository[User]):
        ...     def __init__(self, session: AsyncSession):
        ...         super().__init__(session, User)
        ...
        ...     async def get_by_username(self, username: str) -> User | None:
        ...         result = await self.session.execute(
        ...             select(self.model).where(self.model.username == username)
        ...         )
        ...         return result.scalar_one_or_none()
    """

    def __init__(self, session: AsyncSession, model: Type[T]):
        """Initialize repository with session and model type.

        Args:
            session: AsyncSession for database operations
            model: SQLAlchemy model class this repository manages
        """
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> T | None:
        """Get entity by primary key ID.

        Args:
            id: Primary key value

        Returns:
            Entity instance or None if not found

        Example:
            >>> user = await user_repo.get_by_id(123)
            >>> if user:
            ...     print(f"Found user: {user.username}")
        """
        # Get primary key column name dynamically
        pk_column = inspect(self.model).primary_key[0]
        result = await self.session.execute(
            select(self.model).where(pk_column == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """Get all entities with pagination.

        Args:
            limit: Maximum number of entities to return (default: 100)
            offset: Number of entities to skip (default: 0)

        Returns:
            List of entity instances

        Example:
            >>> # Get first 50 users
            >>> users = await user_repo.get_all(limit=50)
            >>> # Get next 50 users
            >>> more_users = await user_repo.get_all(limit=50, offset=50)
        """
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def add(self, entity: T) -> T:
        """Add new entity to the database.

        The entity is added to the session and flushed to get the ID,
        but not committed. Call commit() to persist changes.

        Args:
            entity: Entity instance to add

        Returns:
            The added entity with populated ID and defaults

        Example:
            >>> user = User(username="john", email="john@example.com")
            >>> user = await user_repo.add(user)
            >>> print(f"Created user with ID: {user.id}")
            >>> await user_repo.commit()
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: T) -> None:
        """Delete entity from the database.

        The entity is marked for deletion and flushed, but not committed.
        Call commit() to persist changes.

        Args:
            entity: Entity instance to delete

        Example:
            >>> user = await user_repo.get_by_id(123)
            >>> if user:
            ...     await user_repo.delete(user)
            ...     await user_repo.commit()
        """
        await self.session.delete(entity)
        await self.session.flush()

    async def commit(self) -> None:
        """Commit the current transaction.

        Persists all pending changes (adds, updates, deletes) to the database.

        Example:
            >>> user = User(username="john")
            >>> await user_repo.add(user)
            >>> await user_repo.commit()
        """
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction.

        Discards all pending changes and reverts to the last committed state.

        Example:
            >>> try:
            ...     user = User(username="john")
            ...     await user_repo.add(user)
            ...     # Something went wrong
            ...     await user_repo.rollback()
            ... except Exception as e:
            ...     await user_repo.rollback()
            ...     raise
        """
        await self.session.rollback()
