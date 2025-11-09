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

- **word.py**: WordRepository and UserWordRepository (Task 3.4)
  - Word management: `find_by_text_and_language()`, `get_frequency_words()`
  - User vocabulary management: `get_user_word()`, `get_user_vocabulary()`, `count_by_status()`
  - Eager loading of relationships using selectinload
  - Case-insensitive word lookups

## Usage Pattern

Repositories are typically used within services and accept an AsyncSession:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from src.words.repositories import CacheRepository, WordRepository, UserWordRepository
from src.words.models import WordStatusEnum

async def example(session: AsyncSession):
    # Cache example
    cache_repo = CacheRepository(session)
    result = await cache_repo.get_translation("hello", "en", "ru")

    if not result:
        # Fetch from API and cache
        result = await translation_api.translate("hello", "en", "ru")
        await cache_repo.set_translation("hello", "en", "ru", result)
        await session.commit()

    # Word repository example
    word_repo = WordRepository(session)
    word = await word_repo.find_by_text_and_language("hello", "en")
    frequent_words = await word_repo.get_frequency_words("en", "A1", limit=50)

    # User vocabulary example
    user_word_repo = UserWordRepository(session)
    user_word = await user_word_repo.get_user_word(profile_id=1, word_id=100)
    vocabulary = await user_word_repo.get_user_vocabulary(
        profile_id=1,
        status=WordStatusEnum.LEARNING
    )
    stats = await user_word_repo.count_by_status(profile_id=1)
```

## Key Features

- **Async/Await**: All repositories use async methods with AsyncSession
- **Type Safety**: Properly typed with modern Python type hints
- **Transaction Management**: Repositories use flush() but don't auto-commit
- **Cache Optimization**: CacheRepository implements upsert logic and expiration
- **Test Coverage**: Comprehensive unit and integration tests for all repositories

## Testing

Tests are located in `/home/user/words/tests/repositories/`:
- `test_base.py`: Tests for BaseRepository (26 tests)
- `test_user.py`: Tests for UserRepository and ProfileRepository (49 tests)
- `test_cache.py`: Tests for CacheRepository (14 tests)
- `test_word.py`: Tests for WordRepository and UserWordRepository (40 tests)

All repository tests use both mock-based unit tests and integration tests with real SQLite in-memory databases. Total: 129 tests with 100% coverage for all repository code.
