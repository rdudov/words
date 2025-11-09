# Database Guidelines: SQLAlchemy Async Best Practices

## Overview

This guide provides comprehensive best practices for working with async SQLAlchemy in the Words project. Following these guidelines will help you avoid common pitfalls, write efficient database queries, and prevent runtime errors.

### Why This Document Exists

Async SQLAlchemy has fundamentally different behavior than sync SQLAlchemy, particularly around **relationship loading**. The most common issue developers face is the `MissingGreenlet` error, which occurs when trying to access relationships that weren't eagerly loaded.

This document explains:
- Why async SQLAlchemy requires eager loading
- How to implement eager loading correctly
- Which loading strategies to use and when
- How to troubleshoot lazy loading issues
- Real examples from this codebase

## The Greenlet Error: What It Is and Why It Happens

### The Error Message

```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called;
can't call await_only() here. Was IO attempted in an unexpected place?
```

### What Causes It

In async SQLAlchemy, **lazy loading does not work**. When you try to access a relationship that wasn't eagerly loaded, SQLAlchemy attempts to execute a database query synchronously, which is impossible in an async context.

**Example - This Will Fail:**

```python
async def get_profile_user(session, profile_id: int):
    # Query WITHOUT eager loading
    result = await session.execute(
        select(LanguageProfile)
        .where(LanguageProfile.profile_id == profile_id)
    )
    profile = result.scalar_one()

    # ERROR: MissingGreenlet raised here!
    native_lang = profile.user.native_language
```

### Why It's Actually Helpful

The `MissingGreenlet` error is **intentional and beneficial**:

1. **Catches bugs early**: Lazy loading bugs are caught during testing, not in production
2. **Forces explicit design**: You must think about which relationships you need
3. **Prevents N+1 queries**: You can't accidentally create performance problems
4. **Clear error messages**: The error tells you exactly what went wrong

## Best Practices for Eager Loading

### Core Rule

**Always eagerly load relationships that will be accessed after the query.**

If your code accesses `profile.user`, `user.profiles`, or any other relationship, that relationship MUST be eagerly loaded in the query.

### Using selectinload()

The most common eager loading strategy. Loads relationships in a **separate SELECT query**.

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Correct - eager loading with selectinload()
result = await session.execute(
    select(LanguageProfile)
    .where(LanguageProfile.profile_id == profile_id)
    .options(selectinload(LanguageProfile.user))
)
profile = result.scalar_one()
native_lang = profile.user.native_language  # Works!
```

**When to use selectinload():**
- For one-to-many relationships (User.profiles)
- For many-to-one relationships (LanguageProfile.user)
- When you want to avoid cartesian products
- Default choice for most cases

### Using joinedload()

Loads relationships using a SQL **LEFT OUTER JOIN**.

```python
from sqlalchemy.orm import joinedload

result = await session.execute(
    select(LanguageProfile)
    .where(LanguageProfile.profile_id == profile_id)
    .options(joinedload(LanguageProfile.user))
)
profile = result.scalar_one()
```

**When to use joinedload():**
- For one-to-one relationships
- For many-to-one relationships where parent is always present
- When you want a single SQL query instead of multiple queries
- When the relationship is small and won't cause cartesian products

**⚠️ Warning:** For one-to-many relationships, `joinedload()` can create cartesian products (duplicate parent rows). Use `selectinload()` instead.

### Using subqueryload()

Loads relationships using a **subquery**. Rarely needed in modern SQLAlchemy.

```python
from sqlalchemy.orm import subqueryload

result = await session.execute(
    select(User)
    .where(User.user_id == user_id)
    .options(subqueryload(User.profiles))
)
```

**When to use subqueryload():**
- Legacy code migration
- Specific performance optimization cases
- Usually `selectinload()` is a better choice

### Loading Multiple Relationships

You can eager load multiple relationships in a single query:

```python
# Load profile with BOTH user AND user_words
result = await session.execute(
    select(LanguageProfile)
    .where(LanguageProfile.profile_id == profile_id)
    .options(
        selectinload(LanguageProfile.user),
        selectinload(LanguageProfile.user_words)
    )
)
profile = result.scalar_one()

# Both relationships are now accessible
user = profile.user                    # Safe!
words = profile.user_words             # Safe!
```

### Loading Nested Relationships

Chain `selectinload()` calls to load relationships several levels deep:

```python
# Load user -> profiles -> user_words -> word
result = await session.execute(
    select(User)
    .where(User.user_id == user_id)
    .options(
        selectinload(User.profiles)
        .selectinload(LanguageProfile.user_words)
        .selectinload(UserWord.word)
    )
)
user = result.scalar_one()

# Access nested relationships safely
for profile in user.profiles:              # Safe!
    for user_word in profile.user_words:   # Safe!
        print(user_word.word.word)         # Safe!
```

## Comparison of Loading Strategies

| Strategy | SQL Queries | Use Case | Pros | Cons |
|----------|-------------|----------|------|------|
| `selectinload()` | 2+ (separate SELECT) | One-to-many, many-to-one | Avoids cartesian products, efficient | Multiple round-trips |
| `joinedload()` | 1 (LEFT OUTER JOIN) | One-to-one, small many-to-one | Single query | Can create cartesian products |
| `subqueryload()` | 2 (subquery) | Legacy compatibility | Works for collections | Usually slower than selectinload |

**Recommendation:** Use `selectinload()` by default unless you have a specific reason to use `joinedload()`.

## Common Patterns in This Project

### Pattern 1: Repository Methods with Eager Loading

All repository methods that return objects with relationships should use eager loading.

**Example from `/home/user/words/src/words/repositories/user.py`:**

```python
class UserRepository(BaseRepository[User]):
    async def get_by_telegram_id(self, user_id: int) -> User | None:
        """Get user by Telegram ID with profiles eagerly loaded."""
        result = await self.session.execute(
            select(User)
            .where(User.user_id == user_id)
            .options(selectinload(User.profiles))  # Eager load!
        )
        return result.scalar_one_or_none()
```

**Why:** Callers of this method will likely access `user.profiles`, so we eagerly load it.

### Pattern 2: Accessing Relationships in Handlers

When handlers access relationships, the repository must eager load them.

**Example from `/home/user/words/src/words/repositories/user.py`:**

```python
class ProfileRepository(BaseRepository[LanguageProfile]):
    async def get_active_profile(self, user_id: int) -> LanguageProfile | None:
        """
        Get active profile with user eagerly loaded.

        Uses selectinload(LanguageProfile.user) because handlers access
        profile.user.native_language for LLM context.
        """
        result = await self.session.execute(
            select(LanguageProfile)
            .where(LanguageProfile.user_id == user_id)
            .where(LanguageProfile.is_active == True)
            .options(selectinload(LanguageProfile.user))  # Required!
        )
        return result.scalar_one_or_none()
```

**Why:** Bot handlers call `profile.user.native_language` to pass context to the LLM.

### Pattern 3: Loading Multiple Related Objects

When you need access to multiple relationships, load them all.

**Example from `/home/user/words/src/words/repositories/word.py`:**

```python
class UserWordRepository(BaseRepository[UserWord]):
    async def get_user_word(
        self,
        profile_id: int,
        word_id: int
    ) -> UserWord | None:
        """Get user's word with eagerly loaded statistics and word details."""
        result = await self.session.execute(
            select(UserWord).where(
                and_(
                    UserWord.profile_id == profile_id,
                    UserWord.word_id == word_id
                )
            ).options(
                selectinload(UserWord.word),        # Load word details
                selectinload(UserWord.statistics)   # Load statistics
            )
        )
        return result.scalar_one_or_none()
```

**Why:** Callers need both `user_word.word` and `user_word.statistics`.

### Pattern 4: Loading Collections with Filters

When loading collections, you can also filter them.

```python
# Load user with only active profiles
result = await session.execute(
    select(User)
    .where(User.user_id == user_id)
    .options(
        selectinload(User.profiles).where(LanguageProfile.is_active == True)
    )
)
user = result.scalar_one()
active_profiles = user.profiles  # Contains only active profiles
```

### Pattern 5: When NOT to Use Eager Loading

If you never access a relationship, don't load it.

```python
# If you only need profile fields, not the user
result = await session.execute(
    select(LanguageProfile)
    .where(LanguageProfile.profile_id == profile_id)
    # No .options() needed - we won't access profile.user
)
profile = result.scalar_one()

# Only access profile's own fields
print(profile.target_language)  # Safe
print(profile.level)            # Safe
# Don't access profile.user!
```

## Troubleshooting Lazy Loading Issues

### Issue 1: MissingGreenlet Error in Production Code

**Symptom:**
```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called
```

**Diagnosis:**
1. Check the stack trace to find which relationship is being accessed
2. Look for code like `obj.relationship_name`
3. Find the query that loaded `obj`

**Solution:**
Add `selectinload()` to the query:

```python
# Before (causes error):
result = await session.execute(
    select(LanguageProfile).where(LanguageProfile.profile_id == profile_id)
)
profile = result.scalar_one()
native_lang = profile.user.native_language  # ERROR!

# After (fixed):
result = await session.execute(
    select(LanguageProfile)
    .where(LanguageProfile.profile_id == profile_id)
    .options(selectinload(LanguageProfile.user))  # Add this!
)
profile = result.scalar_one()
native_lang = profile.user.native_language  # Works!
```

### Issue 2: Error Says "Was IO attempted in an unexpected place?"

**Cause:**
You're accessing a relationship that wasn't eagerly loaded.

**Steps to Fix:**
1. Find which relationship is being accessed (check stack trace)
2. Find the query that loaded the parent object
3. Add `selectinload()` for that relationship to the query

**Example:**

Stack trace shows error at:
```python
# handlers/words.py, line 45
translation_prompt = f"Translate to {profile.user.native_language}"
```

Solution:
```python
# In ProfileRepository.get_active_profile()
# Add: .options(selectinload(LanguageProfile.user))
```

### Issue 3: How Do I Know Which Relationships to Eager Load?

**Answer:**
Look at your code and identify which relationships you access.

```python
async def process_user_data(session, user_id):
    result = await session.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one()

    # You access user.profiles here
    for profile in user.profiles:  # ← Need: selectinload(User.profiles)

        # You access profile.user_words here
        for word in profile.user_words:  # ← Need: selectinload(LanguageProfile.user_words)
            print(word.word)

# Solution: Add both relationships to the query
result = await session.execute(
    select(User)
    .where(User.user_id == user_id)
    .options(
        selectinload(User.profiles)
        .selectinload(LanguageProfile.user_words)
    )
)
```

### Issue 4: Testing Reveals MissingGreenlet Error

**This is good!** Your tests are catching the bug before production.

**Fix in your repository/service code:**
1. Find the failing test
2. Look at which relationship is being accessed
3. Add `selectinload()` to the repository method
4. Re-run the test

### Issue 5: Performance - Too Much Data Loaded

**Symptom:**
Queries are slow because you're loading relationships you don't need.

**Solution:**
Only eager load relationships you actually access. Review your code and remove unnecessary `selectinload()` calls.

```python
# Bad - loading data we don't use
result = await session.execute(
    select(User)
    .where(User.user_id == user_id)
    .options(
        selectinload(User.profiles)
        .selectinload(LanguageProfile.user_words)
        .selectinload(UserWord.word)
        .selectinload(UserWord.statistics)
    )
)
user = result.scalar_one()
print(user.native_language)  # We only needed this field!

# Good - only load what we need
result = await session.execute(
    select(User).where(User.user_id == user_id)
    # No options needed - we only access User fields
)
```

## Verifying Eager Loading

### Method 1: Access the Relationship (Automatic Detection)

The simplest way - just access the relationship in your code:

```python
result = await session.execute(
    select(User)
    .where(User.user_id == user_id)
    .options(selectinload(User.profiles))
)
user = result.scalar_one()

# This line tests eager loading
# If profiles weren't loaded, MissingGreenlet would be raised
profiles = user.profiles  # Automatic verification!
```

### Method 2: Use SQLAlchemy Inspection API

For explicit verification in tests:

```python
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm.base import NO_VALUE

result = await session.execute(
    select(LanguageProfile)
    .where(LanguageProfile.profile_id == profile_id)
    .options(selectinload(LanguageProfile.user))
)
profile = result.scalar_one()

# Inspect the object
inspection = sa_inspect(profile)
user_attr = inspection.attrs.user

# Check if relationship is loaded
is_loaded = user_attr.loaded_value is not NO_VALUE

assert is_loaded, "User relationship was not eagerly loaded!"
```

### Method 3: Check Query Output (Development)

Enable SQL logging to see the queries:

```python
# In your .env file
LOG_LEVEL=DEBUG

# SQLAlchemy will log all SQL queries
# Look for SELECT statements that load relationships
```

## Integration with Testing

This project has comprehensive testing documentation in `/home/user/words/tests/LAZY_LOADING_DETECTION.md`.

### Key Testing Practices

1. **Integration tests automatically catch lazy loading issues**
   - Use the `integration_test_session` fixture
   - Access relationships in your tests
   - MissingGreenlet errors will fail the test

2. **Test relationship access explicitly**
   ```python
   @pytest.mark.asyncio
   async def test_get_user_loads_profiles(integration_test_session):
       """Test that get_by_telegram_id loads profiles."""
       repo = UserRepository(integration_test_session)
       user = await repo.get_by_telegram_id(123)

       # This tests eager loading - will fail if profiles not loaded
       assert len(user.profiles) == 2
   ```

3. **Use inspection for strict verification**
   ```python
   @pytest.mark.asyncio
   async def test_profile_eagerly_loads_user(integration_test_session):
       """Verify user relationship is eagerly loaded."""
       from sqlalchemy import inspect as sa_inspect
       from sqlalchemy.orm.base import NO_VALUE

       repo = ProfileRepository(integration_test_session)
       profile = await repo.get_active_profile(123)

       # Verify eager loading with inspection
       inspection = sa_inspect(profile)
       is_loaded = inspection.attrs.user.loaded_value is not NO_VALUE

       assert is_loaded, "User not eagerly loaded!"
   ```

See the testing documentation for more examples and strategies.

## Performance Considerations

### Eager Loading Trade-offs

**Advantages:**
- Prevents N+1 query problems
- Reduces total database round-trips
- Predictable performance
- Required for async SQLAlchemy

**Disadvantages:**
- May load unnecessary data
- Can create large result sets
- Memory usage increases with deep nesting

### Optimization Strategies

1. **Load only what you need**
   ```python
   # Don't load relationships you won't access
   result = await session.execute(
       select(User).where(User.user_id == user_id)
       # Only add selectinload if you'll access the relationship
   )
   ```

2. **Use pagination for large collections**
   ```python
   result = await session.execute(
       select(UserWord)
       .where(UserWord.profile_id == profile_id)
       .options(selectinload(UserWord.word))
       .limit(100)  # Limit the number of results
   )
   ```

3. **Consider separate queries for heavy relationships**
   ```python
   # If user_words is huge, load it separately
   user = await get_user(user_id)

   # Only load words if needed
   if display_vocabulary:
       words = await get_user_words(profile_id)
   ```

4. **Monitor query performance**
   ```python
   # Enable SQL query logging during development
   # Look for slow queries in logs
   # Use EXPLAIN to analyze query plans
   ```

## Common Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: Using session.get() for Related Data

```python
# Bad - session.get() doesn't support eager loading options
user = await session.get(User, user_id)
profiles = user.profiles  # MissingGreenlet error!

# Good - use select() with options
result = await session.execute(
    select(User)
    .where(User.user_id == user_id)
    .options(selectinload(User.profiles))
)
user = result.scalar_one()
profiles = user.profiles  # Works!
```

### ❌ Anti-Pattern 2: Lazy Loading in Loops

```python
# Bad - causes N+1 queries in sync code, fails in async
users = await get_all_users()  # No eager loading
for user in users:
    profiles = user.profiles  # MissingGreenlet error N times!

# Good - eager load once
result = await session.execute(
    select(User).options(selectinload(User.profiles))
)
users = result.scalars().all()
for user in users:
    profiles = user.profiles  # Works!
```

### ❌ Anti-Pattern 3: Over-eager Loading

```python
# Bad - loading everything "just in case"
result = await session.execute(
    select(User)
    .where(User.user_id == user_id)
    .options(
        selectinload(User.profiles)
        .selectinload(LanguageProfile.user_words)
        .selectinload(UserWord.word)
        .selectinload(UserWord.statistics)
    )
)
user = result.scalar_one()
print(user.native_language)  # We only needed this!

# Good - load only what you access
result = await session.execute(
    select(User).where(User.user_id == user_id)
)
user = result.scalar_one()
print(user.native_language)
```

### ❌ Anti-Pattern 4: Not Testing Relationship Access

```python
# Bad - test doesn't verify relationship loading
@pytest.mark.asyncio
async def test_get_user(integration_test_session):
    repo = UserRepository(integration_test_session)
    user = await repo.get_by_telegram_id(123)
    assert user is not None  # Doesn't test relationship access!

# Good - test accesses the relationship
@pytest.mark.asyncio
async def test_get_user_with_profiles(integration_test_session):
    repo = UserRepository(integration_test_session)
    user = await repo.get_by_telegram_id(123)
    assert len(user.profiles) == 2  # Tests eager loading!
```

## Quick Reference

### When to Use Each Loading Strategy

| Scenario | Use | Example |
|----------|-----|---------|
| One-to-many (User → Profiles) | `selectinload()` | `selectinload(User.profiles)` |
| Many-to-one (Profile → User) | `selectinload()` or `joinedload()` | `selectinload(LanguageProfile.user)` |
| One-to-one | `joinedload()` | `joinedload(User.profile)` |
| Nested relationships | Chain `selectinload()` | `selectinload(User.profiles).selectinload(LanguageProfile.user_words)` |
| Multiple relationships | Multiple `.options()` | `.options(selectinload(A), selectinload(B))` |

### Checklist for Adding Repository Methods

When adding a new repository method:

- [ ] Identify which relationships will be accessed by callers
- [ ] Add `selectinload()` for each accessed relationship
- [ ] Write a test that accesses those relationships
- [ ] Run the test to verify no MissingGreenlet errors
- [ ] Document why relationships are eagerly loaded (inline comment)

### Error Resolution Flowchart

```
MissingGreenlet error?
    ↓
Check stack trace for relationship access
    ↓
Find the query that loaded the parent object
    ↓
Add .options(selectinload(ParentModel.relationship))
    ↓
Re-run the code/test
    ↓
Still fails? Check for nested relationships
```

## References and Further Reading

### Project Documentation

- **Testing Guide**: `/home/user/words/tests/LAZY_LOADING_DETECTION.md`
  - Focus on testing strategies and fixtures
  - Examples of test patterns
  - Using the inspection API

- **Project Guidelines**: `/home/user/words/CLAUDE.md`
  - Quick reference for SQLAlchemy async best practices
  - Integration with project workflow

### Code Examples

- **User Repository**: `/home/user/words/src/words/repositories/user.py`
  - `UserRepository.get_by_telegram_id()` - Loading one-to-many
  - `ProfileRepository.get_active_profile()` - Loading many-to-one

- **Word Repository**: `/home/user/words/src/words/repositories/word.py`
  - `UserWordRepository.get_user_word()` - Loading multiple relationships
  - `UserWordRepository.get_user_vocabulary()` - Loading with filters

- **Test Examples**: `/home/user/words/tests/repositories/test_user.py`
  - Integration tests with relationship access
  - Explicit eager loading verification
  - Using SQLAlchemy inspection API

### External Resources

- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Eager Loading Guide](https://docs.sqlalchemy.org/en/20/orm/loading_relationships.html)
- [MissingGreenlet Error Explanation](https://docs.sqlalchemy.org/en/20/errors.html#error-xd2s)
- [Relationship Loading Techniques](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html)

## Summary

**The Golden Rules:**

1. **Always eager load relationships accessed after the query**
2. **Use `selectinload()` as the default strategy**
3. **Test relationship access in integration tests**
4. **When you see MissingGreenlet, add `selectinload()`**
5. **Load only what you need for performance**

Following these guidelines will help you write efficient, bug-free async SQLAlchemy code that integrates seamlessly with the Words project architecture.
