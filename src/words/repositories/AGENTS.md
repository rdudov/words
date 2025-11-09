# Repositories Directory

## Overview

This directory contains the repository pattern implementation for data access in the Words application. Repositories abstract the database access layer and provide a clean API for working with models.

## Structure

### Base Repository
- **base.py**: Generic BaseRepository class with common CRUD operations
  - `get_by_id()`: Retrieve entity by primary key
  - `get_all()`: Get all entities with pagination
  - `add()`: Add new entity to database
  - `delete()`: Remove entity from database
  - `commit()`: Commit transaction
  - `rollback()`: Rollback transaction

### Specific Repositories

- **user.py**: UserRepository and ProfileRepository
  - User management (create, get by telegram_id, update timezone, etc.)
  - Language profile management (create, get by user and language, etc.)

- **cache.py**: CacheRepository (Task 3.2)
  - Translation caching: `get_translation()`, `set_translation()`
  - Validation caching: `get_validation()`, `set_validation()`
  - Handles cache expiration and upsert logic
  - Normalizes inputs to lowercase for case-insensitive lookups

## Usage Pattern

Repositories are typically used within services and accept an AsyncSession:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from src.words.repositories import CacheRepository

async def example(session: AsyncSession):
    cache_repo = CacheRepository(session)

    # Get cached translation
    result = await cache_repo.get_translation("hello", "en", "ru")

    if not result:
        # Fetch from API and cache
        result = await translation_api.translate("hello", "en", "ru")
        await cache_repo.set_translation("hello", "en", "ru", result)
        await session.commit()
```

## Key Features

- **Async/Await**: All repositories use async methods with AsyncSession
- **Type Safety**: Properly typed with modern Python type hints
- **Transaction Management**: Repositories use flush() but don't auto-commit
- **Cache Optimization**: CacheRepository implements upsert logic and expiration
- **Test Coverage**: Comprehensive unit and integration tests for all repositories

## Testing

Tests are located in `/home/user/words/tests/repositories/`:
- `test_base.py`: Tests for BaseRepository
- `test_user.py`: Tests for UserRepository and ProfileRepository
- `test_cache.py`: Tests for CacheRepository

All repository tests use both mock-based unit tests and integration tests with real SQLite in-memory databases.
