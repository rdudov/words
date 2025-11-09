"""
Repository layer for the Words application.

This module provides the repository pattern implementation for data access,
including base repository with common CRUD operations and specific repositories
for each model.
"""

from .base import BaseRepository
from .user import UserRepository, ProfileRepository
from .cache import CacheRepository
from .word import WordRepository, UserWordRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "ProfileRepository",
    "CacheRepository",
    "WordRepository",
    "UserWordRepository",
]
