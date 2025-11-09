# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot for language learning with adaptive spaced repetition, LLM-powered validation, and intelligent word selection. The project has completed Phase 2 (User Management) and is ready for Phase 3 (Word Management).

**Current Status:**
- ✅ Phase 0 Complete: Project Setup (Tasks 0.1-0.3)
- ✅ Phase 1 Complete: Core Infrastructure (Tasks 1.1-1.9 complete)
- ✅ Phase 2 Complete: User Management (Tasks 2.1-2.7 complete)

## Project Structure

```
/opt/projects/words/
├── src/words/           # Main application package
├── tests/               # Test suite with pytest
├── data/                # Data directories (frequency lists, translations)
├── logs/                # Application logs
└── docs/                # Project documentation
```

## Getting Started

The project uses Python 3.11+ and requires a virtual environment:

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (once available)
pip install -r requirements.txt

# Run the application
python -m src.words
```

## Development Workflow

1. Follow the implementation plan in `docs/implementation_plan.md`
2. Run tests before committing: `pytest`
3. Update README.md after significant changes

## Logging Standards

The project uses Python's standard `logging` module with rotating file handlers. This provides consistent, production-ready logging without external dependencies.

**Core Principles:**
- Use standard `logging` module (NOT structlog or other libraries)
- Each module creates its own logger: `logger = logging.getLogger(__name__)`
- Centralized configuration in `src/words/utils/logger.py`
- Log rotation via `RotatingFileHandler`
- Dual output: console + rotating log files

**Initialization:**
The logging system is initialized in `src/words/__main__.py`:

```python
from src.words.utils.logger import setup_logging

# Call this ONCE at application startup
setup_logging()
```

**Module Usage:**
In every module that needs logging, add at the top level:

```python
import logging

logger = logging.getLogger(__name__)

# Then use throughout the module:
logger.info("User registered successfully")
logger.error("Failed to connect to database")
logger.exception("Unexpected error occurred")  # Includes stack trace
logger.warning("API rate limit approaching")
logger.debug("Processing item %d", item_id)
```

**CORRECT Examples:**
```python
# Simple message
logger.info("Bot started successfully")

# With string formatting (preferred)
logger.error("Failed to add word '%s' for user %d", word, user_id)

# With f-strings (acceptable)
logger.warning(f"Cache miss for key: {cache_key}")

# Exception logging (includes traceback)
try:
    risky_operation()
except Exception as e:
    logger.exception("Operation failed")  # Use exception(), not error()
```

**INCORRECT Examples (DO NOT USE):**
```python
# ❌ Wrong: Importing logger from utils
from src.words.utils.logger import logger  # NO!

# ❌ Wrong: Structured logging syntax
logger.info("user_registered", user_id=123, language="en")  # NO!

# ❌ Wrong: Using print statements
print(f"Error: {error}")  # NO! Use logger.error()

# ❌ Wrong: Creating logger with string literal
logger = logging.getLogger("my_module")  # NO! Use __name__
```

**Log Levels:**
- `DEBUG`: Detailed diagnostic information (disabled in production)
- `INFO`: General informational messages about application progress
- `WARNING`: Potentially problematic situations that aren't errors
- `ERROR`: Error events that might still allow the application to continue
- `CRITICAL`: Very severe errors that may prevent the application from running

**Configuration:**
Logging behavior is controlled by environment variables in `.env`:

```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log file path
LOG_FILE=logs/bot.log

# Maximum log file size before rotation (bytes)
MAX_LOG_SIZE=10485760  # 10MB default

# Number of backup log files to keep
MAX_LOG_BACKUP_COUNT=5  # Keep 5 old log files
```

**Log Rotation:**
When `logs/bot.log` reaches `MAX_LOG_SIZE`:
1. Current log renamed to `bot.log.1`
2. Previous `bot.log.1` renamed to `bot.log.2`
3. Continues up to `bot.log.{MAX_LOG_BACKUP_COUNT}`
4. Oldest backup is deleted
5. New `bot.log` file is started

**Best Practices:**
- Use `logger.exception()` instead of `logger.error()` when logging from exception handlers
- Use structured string formatting (`%s`, `%d`) instead of f-strings for better performance
- Log at appropriate levels (don't use INFO for debug details)
- Include relevant context (user_id, word_id, etc.) in error messages
- Never log sensitive data (passwords, API keys, personal info)
- Use `__name__` for logger names to get module hierarchy in logs

**When to Log:**
- INFO: User actions (registration, word addition, lesson completion)
- INFO: System lifecycle events (startup, shutdown, configuration loaded)
- WARNING: Recoverable errors (cache miss, retry attempts, deprecated usage)
- ERROR: Failures that affect functionality (API errors, database errors)
- EXCEPTION: Unhandled exceptions with full stack traces
- DEBUG: Detailed flow information for troubleshooting

## SQLAlchemy Async Best Practices

The project uses async SQLAlchemy which has special requirements for relationship loading.

**Core Rule:** Always eager load relationships that will be accessed after the query.

**Why:** In async SQLAlchemy, accessing relationships outside the query context triggers lazy loading, which fails with `MissingGreenlet` errors in async code.

**Solution:** Use eager loading options:

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Correct - eager loading with selectinload()
result = await session.execute(
    select(LanguageProfile)
    .where(LanguageProfile.user_id == user_id)
    .options(selectinload(LanguageProfile.user))
)
profile = result.scalar_one()
native_lang = profile.user.native_language  # Works!

# Incorrect - lazy loading will fail
result = await session.execute(
    select(LanguageProfile).where(LanguageProfile.user_id == user_id)
)
profile = result.scalar_one()
native_lang = profile.user.native_language  # ERROR: MissingGreenlet!
```

**Loading Strategies:**
- **`selectinload()`**: Use for one-to-many and most many-to-one relationships (default choice)
- **`joinedload()`**: Use for one-to-one relationships or small many-to-one
- Chain them for nested relationships: `selectinload(User.profiles).selectinload(LanguageProfile.user_words)`

**Documentation:**
- **Production code guidelines**: `docs/database_guidelines.md`
  - Comprehensive guide to eager loading
  - Comparison of loading strategies
  - Real examples from this codebase
  - Troubleshooting common issues
- **Testing and detection**: `tests/LAZY_LOADING_DETECTION.md`
  - How to test eager loading
  - Using the inspection API
  - Test fixtures and patterns
- **Repository examples**: `src/words/repositories/user.py`, `src/words/repositories/word.py`
  - See ProfileRepository.get_active_profile() for many-to-one loading
  - See UserRepository.get_by_telegram_id() for one-to-many loading
  - See UserWordRepository.get_user_word() for multiple relationships

**Key Points:**
- Use `selectinload()` for one-to-many relationships (avoids cartesian products)
- Use `joinedload()` for one-to-one relationships (single query)
- Always test relationship access in integration tests
- When you see `MissingGreenlet` error, add `selectinload()` to your query
- Load only relationships you actually access (performance)

**Common Pattern:**
```python
# Repository method with eager loading
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

**Remember:** If your code accesses a relationship (like `profile.user` or `user.profiles`), that relationship MUST be eagerly loaded in the query. See `docs/database_guidelines.md` for complete details.

## Rules

Находи и используй уже имеющиеся в проекте классы и методы. Не дублируй похожую функциональность.

Не используй глобальный python-интерпретатор. Используй venv, если он есть в проекте. Если venv нет, то создай его.

Пиши структурированный код. Разбивай на отдельные файлы для лучшего понимания.

После изменений проверяй README.md на актуальность.
