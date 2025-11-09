# Lazy Loading Detection in Tests

## Overview

In async SQLAlchemy, **lazy loading is automatically detected and prevented** by the framework itself. When you try to access a relationship that wasn't eagerly loaded, SQLAlchemy raises a `MissingGreenlet` error.

**This is the built-in "detection system" - no additional configuration is needed!**

## Why This Matters

Accessing relationships in async code requires those relationships to be eagerly loaded using `selectinload()` or `joinedload()`. Attempting lazy loading in async context causes this error:

```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called;
can't call await_only() here. Was IO attempted in an unexpected place?
```

This error is **intentional** and **helpful** - it catches lazy loading bugs during testing before they reach production.

## How It Works (Automatic!)

```python
# This code will automatically raise MissingGreenlet error:
async def get_user_profile(session, user_id):
    user = await session.get(User, user_id)
    # MissingGreenlet error raised here!
    profiles = user.profiles  # Attempted lazy load
```

**The error happens automatically - you don't need to configure anything special.**

## Best Practices

### 1. Always Use Eager Loading

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# CORRECT: Eager load relationships
async def get_user_with_profiles(session, user_id):
    result = await session.execute(
        select(User)
        .where(User.user_id == user_id)
        .options(selectinload(User.profiles))
    )
    user = result.scalar_one()
    profiles = user.profiles  # Safe - already loaded!
    return user, profiles
```

### 2. Test Relationship Access

Always test that your code accesses the relationships it needs:

```python
@pytest.mark.asyncio
async def test_get_user_with_profiles(integration_test_session):
    """Test that get_user_with_profiles loads profiles correctly."""
    # Setup test data...

    user, profiles = await get_user_with_profiles(integration_test_session, user_id=123)

    # This line tests that profiles were eagerly loaded
    # If they weren't, MissingGreenlet would be raised here
    assert len(profiles) > 0  # Accessing profiles tests eager loading!
```

### 3. Use SQLAlchemy Inspection to Verify Loading

For explicit verification that a relationship was eagerly loaded:

```python
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm.base import NO_VALUE

@pytest.mark.asyncio
async def test_profile_user_relationship_is_loaded(integration_test_session):
    """Explicitly verify that profile.user is eagerly loaded."""
    # Get profile with eager loading
    result = await integration_test_session.execute(
        select(LanguageProfile)
        .where(LanguageProfile.profile_id == 1)
        .options(selectinload(LanguageProfile.user))
    )
    profile = result.scalar_one()

    # Use SQLAlchemy inspection to verify loading
    inspection = sa_inspect(profile)
    user_attr = inspection.attrs.user

    # Check if user relationship is loaded
    is_loaded = user_attr.loaded_value is not NO_VALUE

    assert is_loaded, "User relationship was not eagerly loaded!"
    assert user_attr.loaded_value.user_id == 123
```

## Common Patterns

### Pattern 1: Single Relationship

```python
# Load profile with user
result = await session.execute(
    select(LanguageProfile)
    .where(LanguageProfile.profile_id == 1)
    .options(selectinload(LanguageProfile.user))
)
profile = result.scalar_one()
user = profile.user  # Safe!
```

### Pattern 2: Multiple Relationships

```python
# Load user with profiles
result = await session.execute(
    select(User)
    .where(User.user_id == 123)
    .options(selectinload(User.profiles))
)
user = result.scalar_one()
profiles = user.profiles  # Safe!
```

### Pattern 3: Nested Relationships

```python
# Load user with profiles, and each profile's user_words
result = await session.execute(
    select(User)
    .where(User.user_id == 123)
    .options(
        selectinload(User.profiles).selectinload(LanguageProfile.user_words)
    )
)
user = result.scalar_one()
for profile in user.profiles:
    words = profile.user_words  # Safe!
```

### Pattern 4: Multiple Separate Relationships

```python
# Load profile with both user AND user_words
result = await session.execute(
    select(LanguageProfile)
    .where(LanguageProfile.profile_id == 1)
    .options(
        selectinload(LanguageProfile.user),
        selectinload(LanguageProfile.user_words)
    )
)
profile = result.scalar_one()
user = profile.user  # Safe!
words = profile.user_words  # Safe!
```

## Troubleshooting

### Issue: MissingGreenlet Error in Tests

**Symptom:**
```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called
```

**Cause:**
Your code is trying to lazy load a relationship in async context.

**Solution:**
Add `selectinload()` to your query:

```python
# Before (causes error):
user = await session.get(User, user_id)
profiles = user.profiles  # MissingGreenlet!

# After (fixed):
from sqlalchemy import select
from sqlalchemy.orm import selectinload

result = await session.execute(
    select(User)
    .where(User.user_id == user_id)
    .options(selectinload(User.profiles))
)
user = result.scalar_one()
profiles = user.profiles  # Works!
```

### Issue: Error Says "Was IO attempted in an unexpected place?"

**Cause:**
You're accessing a relationship that wasn't eagerly loaded.

**Solution:**
1. Find which relationship is being accessed (check the stack trace)
2. Add selectinload() for that relationship to your query
3. Re-run the test

**Example:**
```python
# Stack trace shows: profile.user is being accessed
# Solution: Add selectinload(LanguageProfile.user)

result = await session.execute(
    select(LanguageProfile)
    .where(LanguageProfile.profile_id == profile_id)
    .options(selectinload(LanguageProfile.user))  # Add this!
)
```

### Issue: How do I know which relationships to eager load?

**Answer:**
Look at your code and identify which relationships you access:

```python
async def process_user_data(session, user_id):
    result = await session.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one()

    # You access user.profiles here
    for profile in user.profiles:  # Need: selectinload(User.profiles)

        # You access profile.user_words here
        for word in profile.user_words:  # Need: selectinload(LanguageProfile.user_words)
            print(word.word)

# Solution:
result = await session.execute(
    select(User)
    .where(User.user_id == user_id)
    .options(
        selectinload(User.profiles).selectinload(LanguageProfile.user_words)
    )
)
```

## Testing Strategies

### Strategy 1: Integration Tests Catch Lazy Loading Automatically

```python
@pytest.mark.asyncio
async def test_user_service_get_with_profiles(integration_test_session):
    """Integration test automatically detects lazy loading."""
    from src.words.services.user import UserService

    service = UserService(integration_test_session)
    user = await service.get_user_with_profiles(user_id=123)

    # If get_user_with_profiles doesn't use selectinload,
    # this line will raise MissingGreenlet
    assert len(user.profiles) > 0
```

### Strategy 2: Explicit Eager Loading Tests

```python
@pytest.mark.asyncio
async def test_repository_uses_eager_loading(integration_test_session):
    """Explicitly test that repository uses selectinload."""
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.orm.base import NO_VALUE
    from src.words.repositories.user import UserRepository

    repo = UserRepository(integration_test_session)
    user = await repo.get_by_telegram_id(123)

    # Verify profiles were eagerly loaded
    inspection = sa_inspect(user)
    profiles_attr = inspection.attrs.profiles
    is_loaded = profiles_attr.loaded_value is not NO_VALUE

    assert is_loaded, "UserRepository.get_by_telegram_id should use selectinload(User.profiles)"
```

### Strategy 3: Negative Tests (Verify Error is Raised)

```python
@pytest.mark.asyncio
async def test_lazy_load_raises_missing_greenlet(integration_test_session):
    """Test that lazy loading raises MissingGreenlet error."""
    from sqlalchemy import select

    # Query WITHOUT selectinload
    result = await integration_test_session.execute(
        select(User).where(User.user_id == 123)
    )
    user = result.scalar_one()

    # Accessing profiles should raise MissingGreenlet
    with pytest.raises(sqlalchemy.exc.MissingGreenlet):
        _ = user.profiles  # Lazy load attempt
```

## FAQ

**Q: Do I need a special fixture for lazy loading detection?**
A: No! The standard `integration_test_session` fixture is sufficient. Async SQLAlchemy automatically detects lazy loading.

**Q: What's the difference between `selectinload` and `joinedload`?**
A:
- `selectinload`: Loads relationships in separate SELECT queries (better for collections, avoids cartesian products)
- `joinedload`: Loads relationships via SQL JOIN (better for single objects, can be more efficient)
- Both prevent lazy loading!

**Q: Can lazy loading ever work in async code?**
A: No. Lazy loading fundamentally doesn't work in async SQLAlchemy. You must use eager loading.

**Q: What if I forget to add selectinload?**
A: Your tests will fail with MissingGreenlet error, which is exactly what you want! It catches the bug during testing.

**Q: Should all my queries use selectinload?**
A: Only when you need to access the relationship. If you never access user.profiles in your code, you don't need to load it.

**Q: How do I load relationships several levels deep?**
A: Chain selectinload calls:

```python
# Load user -> profiles -> user_words -> word
select(User).options(
    selectinload(User.profiles)
    .selectinload(LanguageProfile.user_words)
    .selectinload(UserWord.word)
)
```

**Q: Does this impact performance?**
A: Eager loading can improve performance by reducing round-trips, but it can also load unnecessary data. Load only what you need.

## Patterns Used in This Project

This section provides real examples from the Words project codebase, showing how we use the `integration_test_session` fixture and implement eager loading in practice.

### Using integration_test_session Fixture

The `integration_test_session` fixture is defined in `/home/user/words/tests/conftest.py` and is the standard fixture for all integration tests in this project.

**Example from tests/repositories/test_user.py:**

```python
@pytest.mark.asyncio
async def test_integration_get_by_telegram_id_with_profiles(
    integration_test_session  # Use this fixture for integration tests
):
    """Test get_by_telegram_id loads user with profiles."""
    # Create test data
    user = User(user_id=123456789, native_language="ru", interface_language="ru")
    integration_test_session.add(user)
    await integration_test_session.commit()

    profile1 = LanguageProfile(
        user_id=123456789,
        target_language="en",
        level=CEFRLevel.B1
    )
    profile2 = LanguageProfile(
        user_id=123456789,
        target_language="es",
        level=CEFRLevel.A2
    )
    integration_test_session.add_all([profile1, profile2])
    await integration_test_session.commit()

    # Get user by telegram ID
    repo = UserRepository(integration_test_session)
    retrieved_user = await repo.get_by_telegram_id(123456789)

    # This line tests eager loading - if profiles weren't loaded,
    # MissingGreenlet would be raised here!
    assert len(retrieved_user.profiles) == 2
```

### Using test_user_with_profile Fixture

The `test_user_with_profile` fixture creates a user with an active profile for testing. It's defined in `/home/user/words/tests/conftest.py`.

**Example from tests/repositories/test_user.py:**

```python
@pytest.mark.asyncio
async def test_get_active_profile_eagerly_loads_user(
    integration_test_session,
    test_user_with_profile  # Creates user with profile
):
    """Test that get_active_profile() uses eager loading for user relationship."""
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.orm.base import NO_VALUE

    repo = ProfileRepository(integration_test_session)
    profile = await repo.get_active_profile(123456789)

    # Use SQLAlchemy inspection to verify eager loading
    inspection = sa_inspect(profile)
    user_attr = inspection.attrs.user

    # Check if user relationship is loaded
    is_loaded = user_attr.loaded_value is not NO_VALUE

    assert is_loaded, (
        "User relationship is not eagerly loaded in get_active_profile()! "
        "This will cause MissingGreenlet errors when accessing profile.user "
        "in async context."
    )
```

### Repository Pattern Examples

Our repositories use eager loading consistently to avoid lazy loading issues.

**Example from src/words/repositories/user.py:**

```python
class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Get user by Telegram ID with eagerly loaded profiles.

        Uses selectinload to prevent lazy loading issues in async context.
        """
        result = await self.session.execute(
            select(User)
            .where(User.user_id == telegram_id)
            .options(selectinload(User.profiles))  # Eager load!
        )
        return result.scalar_one_or_none()
```

**Example from src/words/repositories/word.py:**

```python
class ProfileRepository(BaseRepository[LanguageProfile]):
    """Repository for LanguageProfile model operations."""

    async def get_active_profile(self, user_id: int) -> Optional[LanguageProfile]:
        """
        Get the active language profile for a user.

        Uses selectinload to eagerly load the user relationship.
        """
        result = await self.session.execute(
            select(LanguageProfile)
            .where(LanguageProfile.user_id == user_id)
            .where(LanguageProfile.is_active == True)
            .options(selectinload(LanguageProfile.user))  # Eager load!
        )
        return result.scalar_one_or_none()
```

### Testing Eager Loading with SQLAlchemy Inspection

We use SQLAlchemy's inspection API to explicitly verify relationships are eagerly loaded.

**Example from tests/repositories/test_user.py (lines 712-756):**

```python
@pytest.mark.asyncio
async def test_get_active_profile_eagerly_loads_user(
    integration_test_session,
    test_user_with_profile
):
    """
    Test that get_active_profile() uses eager loading for user relationship.

    This test verifies that the user relationship is eagerly loaded
    using selectinload to prevent lazy loading issues in async context.

    Uses SQLAlchemy inspection API to verify the relationship is loaded,
    not just that it can be accessed (which could work even with lazy loading
    in some contexts).

    This test will FAIL if:
    - selectinload(LanguageProfile.user) is removed from get_active_profile()
    - The user relationship is not eagerly loaded
    """
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.orm.base import NO_VALUE

    repo = ProfileRepository(integration_test_session)
    profile = await repo.get_active_profile(123456789)

    assert profile is not None

    # Use SQLAlchemy inspection to verify eager loading
    inspection = sa_inspect(profile)
    user_attr = inspection.attrs.user

    # Check if user relationship is loaded
    # loaded_value will be NO_VALUE if lazy loading is used
    # loaded_value will be the actual User object if eager loading worked
    is_loaded = user_attr.loaded_value is not NO_VALUE

    assert is_loaded, (
        "User relationship is not eagerly loaded in get_active_profile()! "
        "This will cause MissingGreenlet errors when accessing profile.user "
        "in async context (e.g., in bot handlers)."
    )

    # Verify the loaded user has correct data
    loaded_user = user_attr.loaded_value
    assert loaded_user is not None
    assert loaded_user.user_id == 123456789
```

### Using strict_integration_session Fixture

The `strict_integration_session` fixture is an optional, explicitly-named version of `integration_test_session` for tests that specifically focus on lazy loading detection.

**Example usage:**

```python
@pytest.mark.asyncio
async def test_repository_prevents_lazy_loading(strict_integration_session):
    """
    Test that repository methods prevent lazy loading errors.

    Using strict_integration_session makes the intent explicit:
    this test is specifically about lazy loading detection.
    """
    # Create test data
    user = User(user_id=123, native_language="ru", interface_language="ru")
    strict_integration_session.add(user)
    await strict_integration_session.commit()

    # Test that relationship access works (was eagerly loaded)
    repo = UserRepository(strict_integration_session)
    retrieved_user = await repo.get_by_telegram_id(123)

    # This will fail if profiles weren't eagerly loaded
    assert len(retrieved_user.profiles) == 0
```

### Common Project Fixtures

**Fixtures available in `/home/user/words/tests/conftest.py`:**

1. **`integration_test_engine`**: Provides async SQLAlchemy engine with in-memory SQLite
2. **`integration_test_session`**: Provides async session for integration tests (standard fixture)
3. **`test_user_with_profile`**: Creates a user with an active language profile
4. **`strict_integration_session`**: Same as `integration_test_session` but with explicit naming for lazy loading tests

**Example of fixture composition:**

```python
@pytest.mark.asyncio
async def test_complex_scenario(
    integration_test_session,  # Database session
    test_user_with_profile      # Pre-created user + profile
):
    """Test using multiple fixtures together."""
    user, profile = test_user_with_profile

    # Add more test data
    word = Word(word="hello", language="en", level="A1")
    integration_test_session.add(word)
    await integration_test_session.commit()

    # Test your logic here
    repo = ProfileRepository(integration_test_session)
    active_profile = await repo.get_active_profile(user.user_id)

    # Relationships are eagerly loaded
    assert active_profile.user.user_id == user.user_id
```

### Real Test Files to Reference

- **`/home/user/words/tests/repositories/test_user.py`**: Comprehensive examples of testing User and LanguageProfile repositories with eager loading
- **`/home/user/words/tests/repositories/test_word.py`**: Examples of testing Word and UserWord repositories
- **`/home/user/words/src/words/repositories/user.py`**: Repository implementation with proper eager loading
- **`/home/user/words/src/words/repositories/word.py`**: More repository examples

### Quick Reference: Project-Specific Commands

```bash
# Run all integration tests
pytest tests/repositories/

# Run specific test file
pytest tests/repositories/test_user.py

# Run tests with verbose output (shows eager loading queries)
pytest tests/repositories/test_user.py -v

# Run only integration tests (by marker, if configured)
pytest -m integration
```

## Summary

1. **Lazy loading detection is automatic** in async SQLAlchemy (MissingGreenlet errors)
2. **Always use `selectinload()` or `joinedload()`** when accessing relationships
3. **Test relationship access** in integration tests
4. **When MissingGreenlet occurs**, add selectinload() to the query
5. **No special configuration needed** - use the standard `integration_test_session` fixture

The framework already prevents lazy loading for you. Just follow eager loading best practices!

## Further Reading

- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Eager Loading Guide](https://docs.sqlalchemy.org/en/20/orm/loading_relationships.html)
- [MissingGreenlet Error Explanation](https://docs.sqlalchemy.org/en/20/errors.html#error-xd2s)

## Examples in This Codebase

See these files for real examples:
- `/home/user/words/src/words/repositories/user.py` - Uses selectinload() correctly
- `/home/user/words/src/words/repositories/word.py` - Multiple selectinload() examples
- `/home/user/words/tests/repositories/test_user.py` - Tests with explicit eager loading verification
