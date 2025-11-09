# Logging Unification Plan

## Executive Summary

This document provides a comprehensive plan to unify logging across the `/opt/projects/words` project according to the reference implementation from `/opt/projects/companions/calypso/main.py`. The current project uses `structlog` in some modules and standard `logging` in others, creating inconsistency. This plan eliminates `structlog` entirely and establishes a single, consistent logging standard using Python's built-in `logging` module with rotating file handlers.

## Reference Implementation Analysis

The calypso project demonstrates a clean, production-ready logging setup:

**Key Features:**
- Uses Python's standard `logging` module (NOT structlog)
- `RotatingFileHandler` for automatic log rotation
- Configuration via environment variables:
  - `MAX_LOG_SIZE` (default: 10MB = 10*1024*1024 bytes)
  - `MAX_LOG_BACKUP_COUNT` (default: 5 backup files)
- Log format: `'%(asctime)s - %(name)s - %(levelname)s - %(message)s'`
- Dual output: console (StreamHandler) + file (RotatingFileHandler)
- Directory creation via `setup_log_directories()` function
- Module-level loggers: `logger = logging.getLogger(__name__)`
- Standard methods: `logger.info()`, `logger.error()`, `logger.exception()`, `logger.warning()`, `logger.debug()`

## Current State Analysis

### Files Using Logging

**Source Files (src/):**
1. `src/words/utils/logger.py` - Uses structlog (NEEDS COMPLETE REWRITE)
2. `src/words/__main__.py` - Imports from utils.logger (NEEDS UPDATE)
3. `src/words/infrastructure/database.py` - Uses `logging.getLogger(__name__)` (CORRECT)
4. `src/words/infrastructure/llm_client.py` - Uses `logging.getLogger(__name__)` (CORRECT)
5. `src/words/services/user.py` - Imports from utils.logger (NEEDS UPDATE)
6. `src/words/services/word.py` - Imports from utils.logger (NEEDS UPDATE)
7. `src/words/services/translation.py` - Imports from utils.logger (NEEDS UPDATE)
8. `src/words/bot/__init__.py` - Imports from utils.logger (NEEDS UPDATE)
9. `src/words/bot/handlers/start.py` - No logging (OPTIONAL: ADD IF NEEDED)
10. `src/words/bot/handlers/words.py` - Imports from utils.logger (NEEDS UPDATE)

**Test Files (tests/):**
1. `tests/utils/test_logger.py` - Tests structlog setup (NEEDS REWRITE)
2. `tests/test_main.py` - May use logger (NEEDS REVIEW)
3. `tests/bot/test_setup.py` - May use logger (NEEDS REVIEW)
4. `tests/test_init_db_script.py` - May use logger (NEEDS REVIEW)
5. `tests/services/test_user.py` - May use logger (NEEDS REVIEW)
6. `tests/services/test_word.py` - May use logger (NEEDS REVIEW)
7. `tests/services/test_translation.py` - May use logger (NEEDS REVIEW)

### Current Problems

1. **Inconsistent Logging Library:** Mix of structlog and standard logging
2. **Structured Logs Syntax:** Files using structlog call `logger.info("event", key=value)` which won't work with standard logging
3. **Import Pattern:** Many files import from `src.words.utils.logger` instead of using `logging.getLogger(__name__)`
4. **No Log Rotation:** structlog setup doesn't implement RotatingFileHandler
5. **Missing Environment Variables:** .env.example lacks MAX_LOG_SIZE and MAX_LOG_BACKUP_COUNT
6. **Dependency Issue:** structlog is in requirements.txt but shouldn't be

## Detailed Task Specifications

---

## Task 1: Rewrite src/words/utils/logger.py

### Root Cause
The current logger.py uses structlog library with structured logging patterns that are incompatible with the standard logging approach used in calypso. This creates inconsistency and adds unnecessary dependency.

### Severity & Impact
- **Severity:** HIGH
- **Impact Scope:** Core infrastructure - affects all modules that use logging
- **User Impact:** None (internal infrastructure change)

### Affected Components
- **Files:**
  - `src/words/utils/logger.py`
- **Functions/Classes:**
  - `setup_logging()` function (complete rewrite needed)
  - Module-level `logger` variable (remove, deprecated pattern)
- **Dependencies:**
  - Will remove structlog dependency
  - Uses only standard library (logging, logging.handlers.RotatingFileHandler)

### Fix Strategy

1. **Remove all structlog imports and code**
   - Delete all references to structlog
   - Remove structured logging processors

2. **Implement setup_log_directories() function**
   - Create function matching calypso pattern
   - Create 'logs' directory if it doesn't exist
   - Use `os.makedirs(directory, exist_ok=True)`

3. **Implement setup_logging() function**
   - Configure root logger (not module logger)
   - Set log level from settings (settings.log_level)
   - Create formatter with calypso format string
   - Add StreamHandler for console output
   - Add RotatingFileHandler for file output with rotation
   - Return None (or nothing) - no longer return logger instance

4. **Configure RotatingFileHandler**
   - Use settings.log_file for filename
   - Read MAX_LOG_SIZE from environment (default: 10*1024*1024)
   - Read MAX_LOG_BACKUP_COUNT from environment (default: 5)
   - Set encoding='utf-8'

5. **Remove module-level logger**
   - Delete `logger = setup_logging()` line
   - Each module should create its own logger

### Implementation Details

**Complete new src/words/utils/logger.py:**

```python
"""
Logging configuration for the Words application.

This module provides centralized logging setup using Python's standard
logging module with rotating file handlers for production use.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.words.config.settings import settings


def setup_log_directories():
    """
    Create necessary directories for logs if they don't exist.

    Creates the logs directory structure needed for application logging.
    Uses exist_ok=True to avoid errors if directories already exist.
    """
    directories = ['logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def setup_logging():
    """
    Configure logging for the application.

    Sets up both console and file logging with rotation:
    - Console output via StreamHandler
    - File output via RotatingFileHandler with configurable rotation
    - Log format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    - Log level from settings
    - File rotation controlled by MAX_LOG_SIZE and MAX_LOG_BACKUP_COUNT env vars

    This function configures the root logger, so all module loggers will
    inherit these settings. Each module should create its own logger using:
        logger = logging.getLogger(__name__)

    Environment Variables:
        MAX_LOG_SIZE: Maximum log file size in bytes (default: 10MB)
        MAX_LOG_BACKUP_COUNT: Number of backup files to keep (default: 5)
    """
    # Create log directories
    setup_log_directories()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Create rotating file handler
    # Default: 10MB per file, keep 5 backup files
    file_handler = RotatingFileHandler(
        settings.log_file,
        maxBytes=int(os.getenv('MAX_LOG_SIZE', 10*1024*1024)),  # 10MB default
        backupCount=int(os.getenv('MAX_LOG_BACKUP_COUNT', 5)),
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
```

**Key Changes:**
- Removed all structlog imports and configuration
- Implemented setup_log_directories() matching calypso
- Rewrote setup_logging() to configure root logger
- Added RotatingFileHandler with environment variable configuration
- Removed module-level logger instance
- Used calypso's format string exactly
- Added comprehensive docstrings

### Testing Requirements

**Unit Tests (tests/utils/test_logger.py):**
- Test setup_log_directories() creates 'logs' directory
- Test setup_logging() configures root logger correctly
- Test log format matches expected pattern
- Test both handlers (console and file) are added
- Test RotatingFileHandler uses correct parameters
- Test environment variables (MAX_LOG_SIZE, MAX_LOG_BACKUP_COUNT) are respected
- Test default values when env vars not set
- Test that log messages appear in both console and file

**Integration Tests:**
- Import logger.py and call setup_logging() early in application startup
- Verify logs are written to file with correct format
- Verify log rotation occurs when file size exceeds MAX_LOG_SIZE
- Verify backup files are created correctly

### Validation Criteria

- [ ] No structlog imports remain
- [ ] setup_log_directories() function exists and works
- [ ] setup_logging() configures root logger (not module logger)
- [ ] RotatingFileHandler configured with env vars
- [ ] Log format matches calypso exactly
- [ ] Console and file handlers both present
- [ ] No module-level logger variable
- [ ] All tests pass
- [ ] Logs appear in logs/ directory
- [ ] Log rotation works correctly

### Risks & Considerations

- **Breaking Change:** This is a significant API change - any code importing logger from utils.logger will break
- **Call Timing:** setup_logging() must be called early in application startup (in __main__.py)
- **Test Mocking:** Tests that mock logger will need updates
- **Log Format:** Any code parsing logs will need to handle new format

### Dependencies

This task must be completed FIRST before any other logging tasks, as all other tasks depend on the new logger.py implementation.

---

## Task 2: Update CLAUDE.md with Logging Standards

### Root Cause
CLAUDE.md lacks a dedicated section documenting the project's logging standards, leading to inconsistent logging practices across the codebase.

### Severity & Impact
- **Severity:** MEDIUM
- **Impact Scope:** Documentation - affects developer guidance
- **User Impact:** None (documentation only)

### Affected Components
- **Files:**
  - `/opt/projects/words/CLAUDE.md`
- **Sections:**
  - New section to add: "## Logging Standards"

### Fix Strategy

1. **Add new section after "Development Workflow"**
   - Insert "## Logging Standards" section
   - Document the standard approach matching calypso

2. **Document core principles**
   - Standard logging module only (no structlog)
   - RotatingFileHandler usage
   - Module-level logger pattern

3. **Provide code examples**
   - Show correct logger initialization
   - Show correct logging calls
   - Show incorrect patterns to avoid

4. **Reference environment variables**
   - Document MAX_LOG_SIZE
   - Document MAX_LOG_BACKUP_COUNT

### Implementation Details

**Add to CLAUDE.md after line 46 (after "Development Workflow" section):**

```markdown
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
```

### Testing Requirements

- Review CLAUDE.md renders correctly
- Verify code examples are syntactically correct
- Ensure formatting is consistent with rest of document

### Validation Criteria

- [ ] "## Logging Standards" section added
- [ ] All code examples are correct and tested
- [ ] Environment variables documented
- [ ] Best practices clearly stated
- [ ] CORRECT and INCORRECT examples provided
- [ ] Log rotation explained
- [ ] Formatting is consistent

### Risks & Considerations

- **Documentation Length:** Adds substantial content to CLAUDE.md (acceptable - this is critical info)
- **Code Examples:** Must be kept in sync if logging implementation changes

### Dependencies

Should be done AFTER Task 1 (logger.py rewrite) so examples match actual implementation.

---

## Task 3: Update .claude/agents/code-developer.md

### Root Cause
The code-developer agent instructions don't explicitly mention logging standards, which can lead to inconsistent logging practices in new code.

### Severity & Impact
- **Severity:** MEDIUM
- **Impact Scope:** Developer agent guidance
- **User Impact:** None (agent instructions)

### Affected Components
- **Files:**
  - `/opt/projects/words/.claude/agents/code-developer.md`
- **Sections:**
  - "Working Principles (CRITICAL - MUST FOLLOW)" section

### Fix Strategy

1. **Add logging standard to "Working Principles" section**
   - Add bullet point about unified logging standard
   - Reference CLAUDE.md section

2. **Keep addition concise**
   - Single bullet point
   - Link to detailed documentation

### Implementation Details

**In code-developer.md, add to "Working Principles (CRITICAL - MUST FOLLOW)" section (after line 23):**

```markdown
Before writing any code, you MUST:
- **Reuse existing code**: Always search for and utilize existing classes, methods, and functions in the project. Never duplicate similar functionality.
- **Use virtual environments**: Never use the global Python interpreter. Always use the project's venv if it exists. If no venv exists, create one first.
- **Follow logging standards**: Use ONLY standard Python logging with module-level loggers (`logger = logging.getLogger(__name__)`). Never import logger from utils. See the "Logging Standards" section in CLAUDE.md for details.
- **Structure your code**: Break code into separate, well-organized files for better comprehension and maintainability.
- **Update documentation**: After making changes, verify that README.md and other documentation remain current and accurate.
```

**Key Changes:**
- Added new bullet point about logging standards
- Explicitly prohibits importing logger from utils
- References CLAUDE.md for full details
- Maintains consistent formatting with other bullet points

### Testing Requirements

- Verify markdown renders correctly
- Check link/reference to CLAUDE.md is clear

### Validation Criteria

- [ ] Logging standard bullet point added
- [ ] Reference to CLAUDE.md included
- [ ] Formatting consistent with other bullet points
- [ ] Message is clear and concise

### Risks & Considerations

- **Minimal Risk:** This is documentation only
- **Future-Proof:** May need updates if logging approach changes

### Dependencies

Should be done AFTER Task 2 (CLAUDE.md update) so reference is valid.

---

## Task 4: Update .claude/agents/code-reviewer.md

### Root Cause
The code-reviewer agent instructions don't include logging standards in the review checklist, potentially missing logging issues during reviews.

### Severity & Impact
- **Severity:** MEDIUM
- **Impact Scope:** Code review agent guidance
- **User Impact:** None (agent instructions)

### Affected Components
- **Files:**
  - `/opt/projects/words/.claude/agents/code-reviewer.md`
- **Sections:**
  - "Analyze the Implementation" checklist (around line 22)

### Fix Strategy

1. **Add logging standard to review checklist**
   - Add item to "Analyze the Implementation" bullet list
   - Reference CLAUDE.md section

2. **Keep addition concise**
   - Single bullet point in checklist
   - Link to detailed documentation

### Implementation Details

**In code-reviewer.md, add to "Analyze the Implementation" checklist (after line 25):**

```markdown
2. **Analyze the Implementation**: Examine the code changes with attention to:
   - Correctness: Does the code actually accomplish the stated task?
   - Logic errors or edge cases that weren't handled
   - Adherence to project-specific standards (check CLAUDE.md context if available)
   - Code structure and organization (avoid duplication, use existing project utilities)
   - Logging standards: Verify use of standard logging with `logging.getLogger(__name__)`, not imports from utils. See CLAUDE.md "Logging Standards" section
   - Error handling and input validation
   - Security vulnerabilities
   - Performance considerations
   - Testing coverage and testability (avoid senseless tests with too much mocking)
   - Documentation and code clarity
   - Naming conventions and code style
   - Resource management (memory leaks, file handles, connections)
```

**Key Changes:**
- Added logging standards check to review checklist
- Positioned logically with other code structure checks
- References CLAUDE.md for full details
- Maintains consistent formatting

### Testing Requirements

- Verify markdown renders correctly
- Check reference to CLAUDE.md is clear

### Validation Criteria

- [ ] Logging standard check added to checklist
- [ ] Reference to CLAUDE.md included
- [ ] Formatting consistent with other checklist items
- [ ] Positioned appropriately in list

### Risks & Considerations

- **Minimal Risk:** This is documentation only
- **Review Thoroughness:** Adds one more item to check, but improves consistency

### Dependencies

Should be done AFTER Task 2 (CLAUDE.md update) so reference is valid.

---

## Task 5: Update All Python Files Using Logging

### Root Cause
Multiple Python files import logger from `src.words.utils.logger` and use structured logging syntax that is incompatible with standard logging.

### Severity & Impact
- **Severity:** HIGH
- **Impact Scope:** All modules using logging (10+ files in src/, 7+ files in tests/)
- **User Impact:** None (internal code refactoring)

### Affected Components

**Source Files:**
- `src/words/__main__.py`
- `src/words/services/user.py`
- `src/words/services/word.py`
- `src/words/services/translation.py`
- `src/words/bot/__init__.py`
- `src/words/bot/handlers/words.py`

**Test Files:**
- `tests/utils/test_logger.py` (major rewrite)
- `tests/test_main.py`
- `tests/bot/test_setup.py`
- `tests/test_init_db_script.py`
- `tests/services/test_user.py`
- `tests/services/test_word.py`
- `tests/services/test_translation.py`

**Note:** Files already using `logging.getLogger(__name__)` correctly:
- `src/words/infrastructure/database.py` (already correct)
- `src/words/infrastructure/llm_client.py` (already correct)

### Fix Strategy

For each file, perform these transformations:

1. **Replace import statement**
   - OLD: `from src.words.utils.logger import logger`
   - NEW: `import logging` at top of file, then `logger = logging.getLogger(__name__)` at module level

2. **Convert structured log calls to standard format**
   - OLD: `logger.info("event_name", key1=value1, key2=value2)`
   - NEW: `logger.info("Event name: key1=%s, key2=%s", value1, value2)`

3. **Handle log message formatting**
   - Use f-strings for simple cases: `logger.info(f"User {user_id} registered")`
   - Use % formatting for performance-critical code: `logger.info("User %d registered", user_id)`
   - Avoid concatenation: DON'T use `"text" + str(var)`

4. **Special cases**
   - `logger.exception()` for exception handlers (includes stack trace)
   - `logger.debug()` for detailed flow information
   - Include context in messages (user_id, word_id, etc.)

### Implementation Details

#### src/words/__main__.py

**BEFORE:**
```python
from src.words.utils.logger import logger

async def main():
    logger.info("Starting bot...")
    # ... code ...
    logger.info("Bot is running. Press Ctrl+C to stop.")
    # ...
    logger.info("Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
```

**AFTER:**
```python
import logging
from src.words.utils.logger import setup_logging

logger = logging.getLogger(__name__)

async def main():
    # Initialize logging FIRST
    setup_logging()

    logger.info("Starting bot...")
    # ... code ...
    logger.info("Bot is running. Press Ctrl+C to stop.")
    # ...
    logger.info("Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
```

**Changes:**
- Import `logging` and `setup_logging`
- Create module-level logger with `__name__`
- Call `setup_logging()` at start of main()
- No changes to actual log messages (already simple strings)

---

#### src/words/services/user.py

**BEFORE:**
```python
from src.words.utils.logger import logger

class UserService:
    async def register_user(self, user_id: int, native_language: str, interface_language: str) -> User:
        # ...
        logger.info(
            "user_registered",
            user_id=user_id,
            native_language=native_language
        )
        return user

    async def create_language_profile(self, user_id: int, target_language: str, level: str) -> LanguageProfile:
        # ...
        logger.info(
            "profile_created",
            user_id=user_id,
            language=target_language,
            level=level
        )
        return profile

    async def switch_active_language(self, user_id: int, target_language: str) -> LanguageProfile:
        # ...
        logger.info(
            "language_switched",
            user_id=user_id,
            language=target_language
        )
        return profile
```

**AFTER:**
```python
import logging

logger = logging.getLogger(__name__)

class UserService:
    async def register_user(self, user_id: int, native_language: str, interface_language: str) -> User:
        # ...
        logger.info(
            "User registered: user_id=%d, native_language=%s",
            user_id,
            native_language
        )
        return user

    async def create_language_profile(self, user_id: int, target_language: str, level: str) -> LanguageProfile:
        # ...
        logger.info(
            "Language profile created: user_id=%d, language=%s, level=%s",
            user_id,
            target_language,
            level
        )
        return profile

    async def switch_active_language(self, user_id: int, target_language: str) -> LanguageProfile:
        # ...
        logger.info(
            "Language switched: user_id=%d, language=%s",
            user_id,
            target_language
        )
        return profile
```

**Changes:**
- Changed import to `import logging`
- Added `logger = logging.getLogger(__name__)`
- Converted structured logs to formatted strings with %s, %d placeholders
- Kept semantic meaning of messages

---

#### src/words/services/word.py

**BEFORE (excerpts):**
```python
from src.words.utils.logger import logger

class WordService:
    async def add_word_for_user(self, profile_id: int, word_text: str, source_language: str, target_language: str) -> UserWord:
        try:
            logger.info(
                "word_addition_started",
                profile_id=profile_id,
                word=word_text,
                source_language=source_language,
                target_language=target_language
            )

            # ... code ...

            if word:
                logger.debug(
                    "word_exists_checking_user_vocabulary",
                    word_id=word.word_id,
                    word=word_text,
                    profile_id=profile_id
                )

                if user_word:
                    logger.warning(
                        "word_already_in_user_vocabulary",
                        profile_id=profile_id,
                        word_id=word.word_id,
                        word=word_text
                    )
                    return user_word

            logger.info(
                "word_added_to_user_vocabulary",
                profile_id=profile_id,
                word=word_text,
                word_id=word.word_id,
                status=user_word.status.value
            )

        except ValueError as ve:
            logger.error(
                "word_addition_validation_failed",
                profile_id=profile_id,
                word=word_text,
                error=str(ve)
            )
            raise

        except Exception as e:
            logger.error(
                "word_addition_failed",
                profile_id=profile_id,
                word=word_text,
                source_language=source_language,
                target_language=target_language,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
```

**AFTER:**
```python
import logging

logger = logging.getLogger(__name__)

class WordService:
    async def add_word_for_user(self, profile_id: int, word_text: str, source_language: str, target_language: str) -> UserWord:
        try:
            logger.info(
                "Word addition started: profile_id=%d, word='%s', source=%s, target=%s",
                profile_id,
                word_text,
                source_language,
                target_language
            )

            # ... code ...

            if word:
                logger.debug(
                    "Word exists, checking user vocabulary: word_id=%d, word='%s', profile_id=%d",
                    word.word_id,
                    word_text,
                    profile_id
                )

                if user_word:
                    logger.warning(
                        "Word already in user vocabulary: profile_id=%d, word_id=%d, word='%s'",
                        profile_id,
                        word.word_id,
                        word_text
                    )
                    return user_word

            logger.info(
                "Word added to user vocabulary: profile_id=%d, word='%s', word_id=%d, status=%s",
                profile_id,
                word_text,
                word.word_id,
                user_word.status.value
            )

        except ValueError as ve:
            logger.error(
                "Word addition validation failed: profile_id=%d, word='%s', error=%s",
                profile_id,
                word_text,
                str(ve)
            )
            raise

        except Exception as e:
            logger.error(
                "Word addition failed: profile_id=%d, word='%s', source=%s, target=%s, error=%s (%s)",
                profile_id,
                word_text,
                source_language,
                target_language,
                str(e),
                type(e).__name__
            )
            raise
```

**Changes:**
- Changed import to `import logging`
- Added `logger = logging.getLogger(__name__)`
- Converted all structured logs to formatted strings
- Used %d for integers, %s for strings
- Kept all context information in messages

---

#### src/words/services/translation.py

**BEFORE (excerpts):**
```python
from src.words.utils.logger import logger

class TranslationService:
    async def translate_word(self, word: str, source_lang: str, target_lang: str) -> dict:
        cached = await self.cache_repo.get_translation(word, source_lang, target_lang)

        if cached:
            logger.debug(
                "translation_cache_hit",
                word=word,
                source=source_lang,
                target=target_lang
            )
            return cached

        logger.info(
            "translation_llm_call",
            word=word,
            source=source_lang,
            target=target_lang
        )

        try:
            result = await self.llm_client.translate_word(word, source_lang, target_lang)
            return result
        except Exception as e:
            logger.error(
                "translation_failed",
                word=word,
                error=str(e)
            )
            raise

    async def validate_answer_with_llm(self, question: str, expected: str, user_answer: str,
                                       source_lang: str, target_lang: str, word_id: int,
                                       direction: str) -> tuple[bool, str]:
        cached = await self.cache_repo.get_validation(word_id, direction, expected, user_answer)

        if cached:
            logger.debug(
                "validation_cache_hit",
                word_id=word_id,
                user_answer=user_answer
            )
            return cached

        logger.info(
            "validation_llm_call",
            word_id=word_id,
            expected=expected,
            user_answer=user_answer
        )

        try:
            result = await self.llm_client.validate_answer(
                question, expected, user_answer, source_lang, target_lang
            )
            return (result["is_correct"], result["comment"])
        except Exception as e:
            logger.error(
                "validation_failed",
                word_id=word_id,
                error=str(e)
            )
            return (False, "Validation service unavailable. Please try again.")
```

**AFTER:**
```python
import logging

logger = logging.getLogger(__name__)

class TranslationService:
    async def translate_word(self, word: str, source_lang: str, target_lang: str) -> dict:
        cached = await self.cache_repo.get_translation(word, source_lang, target_lang)

        if cached:
            logger.debug(
                "Translation cache hit: word='%s', source=%s, target=%s",
                word,
                source_lang,
                target_lang
            )
            return cached

        logger.info(
            "Translation LLM call: word='%s', source=%s, target=%s",
            word,
            source_lang,
            target_lang
        )

        try:
            result = await self.llm_client.translate_word(word, source_lang, target_lang)
            return result
        except Exception as e:
            logger.error(
                "Translation failed: word='%s', error=%s",
                word,
                str(e)
            )
            raise

    async def validate_answer_with_llm(self, question: str, expected: str, user_answer: str,
                                       source_lang: str, target_lang: str, word_id: int,
                                       direction: str) -> tuple[bool, str]:
        cached = await self.cache_repo.get_validation(word_id, direction, expected, user_answer)

        if cached:
            logger.debug(
                "Validation cache hit: word_id=%d, user_answer='%s'",
                word_id,
                user_answer
            )
            return cached

        logger.info(
            "Validation LLM call: word_id=%d, expected='%s', user_answer='%s'",
            word_id,
            expected,
            user_answer
        )

        try:
            result = await self.llm_client.validate_answer(
                question, expected, user_answer, source_lang, target_lang
            )
            return (result["is_correct"], result["comment"])
        except Exception as e:
            logger.error(
                "Validation failed: word_id=%d, error=%s",
                word_id,
                str(e)
            )
            return (False, "Validation service unavailable. Please try again.")
```

**Changes:**
- Changed import to `import logging`
- Added `logger = logging.getLogger(__name__)`
- Converted all structured logs to formatted strings
- Maintained all context information

---

#### src/words/bot/__init__.py

**BEFORE:**
```python
from src.words.utils.logger import logger

async def setup_bot() -> tuple[Bot, Dispatcher]:
    # ... code ...
    logger.info("Bot initialized")
    return bot, dp
```

**AFTER:**
```python
import logging

logger = logging.getLogger(__name__)

async def setup_bot() -> tuple[Bot, Dispatcher]:
    # ... code ...
    logger.info("Bot initialized")
    return bot, dp
```

**Changes:**
- Changed import to `import logging`
- Added `logger = logging.getLogger(__name__)`
- No change to log message (already simple string)

---

#### src/words/bot/handlers/words.py

**BEFORE (excerpts):**
```python
from src.words.utils.logger import logger

@router.message(StateFilter(AddWordStates.waiting_for_word))
async def process_word_input(message: Message, state: FSMContext) -> None:
    try:
        # ... code ...

        except Exception as e:
            logger.debug("failed_to_delete_processing_message", error=str(e))

        # ... code ...

        logger.info(
            "language_detected_target_to_native",
            word=word_text,
            source=source_lang,
            target=target_lang
        )

        # ... code ...

        logger.debug(
            "first_translation_attempt_failed_trying_reverse",
            word=word_text,
            error=str(e)
        )

        logger.info(
            "language_detected_native_to_target",
            word=word_text,
            source=source_lang,
            target=target_lang
        )

        # ... code ...

        logger.debug("failed_to_delete_processing_message", error=str(e))

        logger.info(
            "word_added_via_bot",
            user_id=user_id,
            profile_id=profile.profile_id,
            word=word_text,
            source_language=source_lang,
            target_language=target_lang
        )

    except Exception as e:
        logger.error(
            "add_word_failed",
            user_id=user_id,
            word=word_text,
            error=str(e),
            error_type=type(e).__name__
        )

        logger.debug("failed_to_delete_processing_message", error=str(delete_error))
```

**AFTER:**
```python
import logging

logger = logging.getLogger(__name__)

@router.message(StateFilter(AddWordStates.waiting_for_word))
async def process_word_input(message: Message, state: FSMContext) -> None:
    try:
        # ... code ...

        except Exception as e:
            logger.debug("Failed to delete processing message: %s", str(e))

        # ... code ...

        logger.info(
            "Language detected (target→native): word='%s', source=%s, target=%s",
            word_text,
            source_lang,
            target_lang
        )

        # ... code ...

        logger.debug(
            "First translation attempt failed, trying reverse: word='%s', error=%s",
            word_text,
            str(e)
        )

        logger.info(
            "Language detected (native→target): word='%s', source=%s, target=%s",
            word_text,
            source_lang,
            target_lang
        )

        # ... code ...

        logger.debug("Failed to delete processing message: %s", str(e))

        logger.info(
            "Word added via bot: user_id=%d, profile_id=%d, word='%s', source=%s, target=%s",
            user_id,
            profile.profile_id,
            word_text,
            source_lang,
            target_lang
        )

    except Exception as e:
        logger.error(
            "Add word failed: user_id=%d, word='%s', error=%s (%s)",
            user_id,
            word_text,
            str(e),
            type(e).__name__
        )

        logger.debug("Failed to delete processing message: %s", str(delete_error))
```

**Changes:**
- Changed import to `import logging`
- Added `logger = logging.getLogger(__name__)`
- Converted all structured logs to formatted strings
- Made messages more readable with proper English

---

#### tests/utils/test_logger.py

**This file needs COMPLETE REWRITE** because it tests structlog functionality.

**BEFORE (entire file):**
```python
"""Tests for logging configuration."""

import logging
from pathlib import Path

import pytest
import structlog

from src.words.utils.logger import setup_logging


def test_setup_logging_creates_log_directory(tmp_path, monkeypatch):
    """Test that setup_logging creates the log directory."""
    log_file = tmp_path / "test.log"

    # Mock settings to use tmp_path
    from src.words.config import settings as original_settings

    class MockSettings:
        log_file = str(log_file)
        log_level = "INFO"
        debug = False

    monkeypatch.setattr("src.words.utils.logger.settings", MockSettings())

    # Call setup_logging
    logger = setup_logging()

    # Verify directory was created
    assert log_file.parent.exists()
    assert isinstance(logger, structlog.stdlib.BoundLogger)


def test_setup_logging_configures_handlers():
    """Test that setup_logging configures both file and console handlers."""
    logger = setup_logging()

    # Get root logger
    root = logging.getLogger()

    # Should have file and console handlers
    assert len(root.handlers) >= 2

    handler_types = [type(h).__name__ for h in root.handlers]
    assert "FileHandler" in handler_types or "StreamHandler" in handler_types


def test_setup_logging_respects_log_level(monkeypatch):
    """Test that setup_logging respects the configured log level."""
    from src.words.config import settings as original_settings

    class MockSettings:
        log_file = "test.log"
        log_level = "DEBUG"
        debug = True

    monkeypatch.setattr("src.words.utils.logger.settings", MockSettings())

    logger = setup_logging()
    root = logging.getLogger()

    # Should be set to DEBUG
    assert root.level == logging.DEBUG
```

**AFTER (entire file):**
```python
"""Tests for logging configuration."""

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

import pytest

from src.words.utils.logger import setup_logging, setup_log_directories


def test_setup_log_directories_creates_logs_dir(tmp_path, monkeypatch):
    """Test that setup_log_directories creates the logs directory."""
    # Change to tmp directory
    monkeypatch.chdir(tmp_path)

    # Call function
    setup_log_directories()

    # Verify logs directory was created
    assert (tmp_path / "logs").exists()
    assert (tmp_path / "logs").is_dir()


def test_setup_log_directories_idempotent(tmp_path, monkeypatch):
    """Test that setup_log_directories can be called multiple times safely."""
    monkeypatch.chdir(tmp_path)

    # Call multiple times
    setup_log_directories()
    setup_log_directories()
    setup_log_directories()

    # Should still work and directory should exist
    assert (tmp_path / "logs").exists()


def test_setup_logging_creates_log_directory(tmp_path, monkeypatch):
    """Test that setup_logging creates the log directory."""
    log_file = tmp_path / "logs" / "test.log"

    # Mock settings
    class MockSettings:
        log_file = str(log_file)
        log_level = "INFO"

    monkeypatch.setattr("src.words.utils.logger.settings", MockSettings())
    monkeypatch.chdir(tmp_path)

    # Call setup_logging
    setup_logging()

    # Verify directory was created
    assert log_file.parent.exists()


def test_setup_logging_configures_handlers():
    """Test that setup_logging configures both file and console handlers."""
    # Clear existing handlers
    root = logging.getLogger()
    root.handlers.clear()

    setup_logging()

    # Should have exactly 2 handlers: console and file
    assert len(root.handlers) == 2

    handler_types = [type(h).__name__ for h in root.handlers]
    assert "StreamHandler" in handler_types
    assert "RotatingFileHandler" in handler_types


def test_setup_logging_uses_rotating_file_handler():
    """Test that setup_logging uses RotatingFileHandler with rotation config."""
    root = logging.getLogger()
    root.handlers.clear()

    setup_logging()

    # Find the RotatingFileHandler
    rotating_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
    assert len(rotating_handlers) == 1

    handler = rotating_handlers[0]

    # Check default values (10MB, 5 backups)
    assert handler.maxBytes == 10 * 1024 * 1024
    assert handler.backupCount == 5


def test_setup_logging_respects_env_vars(monkeypatch):
    """Test that setup_logging respects MAX_LOG_SIZE and MAX_LOG_BACKUP_COUNT."""
    root = logging.getLogger()
    root.handlers.clear()

    # Set environment variables
    monkeypatch.setenv("MAX_LOG_SIZE", "5242880")  # 5MB
    monkeypatch.setenv("MAX_LOG_BACKUP_COUNT", "3")

    setup_logging()

    # Find the RotatingFileHandler
    rotating_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
    handler = rotating_handlers[0]

    # Check configured values
    assert handler.maxBytes == 5242880
    assert handler.backupCount == 3


def test_setup_logging_respects_log_level(monkeypatch):
    """Test that setup_logging respects the configured log level."""
    root = logging.getLogger()
    root.handlers.clear()

    class MockSettings:
        log_file = "test.log"
        log_level = "DEBUG"

    monkeypatch.setattr("src.words.utils.logger.settings", MockSettings())

    setup_logging()

    # Should be set to DEBUG
    assert root.level == logging.DEBUG


def test_setup_logging_uses_correct_format():
    """Test that setup_logging uses the correct log format."""
    root = logging.getLogger()
    root.handlers.clear()

    setup_logging()

    # Check formatter on handlers
    for handler in root.handlers:
        formatter = handler.formatter
        assert formatter is not None
        # Check format string matches calypso pattern
        assert formatter._fmt == '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def test_module_logger_gets_correct_name():
    """Test that module loggers get the correct __name__."""
    # Simulate a module creating its own logger
    module_logger = logging.getLogger("test.module.name")

    assert module_logger.name == "test.module.name"

    # Should inherit root logger configuration
    root = logging.getLogger()
    if root.handlers:
        # Module logger should use root logger's handlers
        assert module_logger.level == logging.NOTSET or module_logger.level == root.level


def test_logging_to_file_and_console(tmp_path, monkeypatch, caplog):
    """Test that logs are written to both file and console."""
    log_file = tmp_path / "logs" / "test.log"

    class MockSettings:
        log_file = str(log_file)
        log_level = "INFO"

    monkeypatch.setattr("src.words.utils.logger.settings", MockSettings())
    monkeypatch.chdir(tmp_path)

    # Clear and setup
    root = logging.getLogger()
    root.handlers.clear()
    setup_logging()

    # Create a test logger
    test_logger = logging.getLogger("test_module")

    # Write a test message
    test_message = "Test log message for dual output"
    test_logger.info(test_message)

    # Check file
    assert log_file.exists()
    log_content = log_file.read_text()
    assert test_message in log_content
    assert "test_module" in log_content
    assert "INFO" in log_content
```

**Changes:**
- Complete rewrite
- Removed all structlog references
- Added tests for setup_log_directories()
- Added tests for RotatingFileHandler configuration
- Added tests for environment variable handling
- Added test for log format string
- Added test for dual output (file + console)
- Added test for module logger naming
- Much more comprehensive coverage

---

#### Other Test Files

For test files that use logging:
- **tests/test_main.py**: Update import if present
- **tests/bot/test_setup.py**: Update import if present
- **tests/test_init_db_script.py**: Update import if present
- **tests/services/test_user.py**: Update import if present
- **tests/services/test_word.py**: Update import if present
- **tests/services/test_translation.py**: Update import if present

**General pattern for test files:**
```python
# If they currently import:
from src.words.utils.logger import logger

# Change to:
import logging

# Then in test fixtures or test setup, create logger:
logger = logging.getLogger(__name__)

# Or mock the logger if needed:
@pytest.fixture
def mock_logger(mocker):
    return mocker.patch('logging.getLogger')
```

### Testing Requirements

**For each updated file:**
- Run syntax check: `python -m py_compile <file>`
- Run existing tests: `pytest <test_file>`
- Verify logs appear correctly
- Check log format matches expected pattern

**Integration Tests:**
- Run full test suite: `pytest`
- Start application and verify logs appear in logs/bot.log
- Verify log rotation works by filling log file
- Check console output matches file output

### Validation Criteria

- [ ] All files updated to use `import logging`
- [ ] All files use `logger = logging.getLogger(__name__)`
- [ ] No files import from `src.words.utils.logger` (except setup_logging in __main__.py)
- [ ] All structured log calls converted to standard format
- [ ] tests/utils/test_logger.py completely rewritten
- [ ] All tests pass
- [ ] Application starts successfully
- [ ] Logs appear in console and file
- [ ] Log format matches calypso pattern

### Risks & Considerations

- **Breaking Change:** Large-scale refactoring across many files
- **Testing Impact:** May need to update many test mocks
- **Log Parsing:** Any log parsing tools will need updates
- **Review Burden:** Many files changed at once - careful review needed

### Dependencies

Must be done AFTER Task 1 (logger.py rewrite) is complete.

---

## Task 6: Update requirements.txt and pyproject.toml

### Root Cause
The project dependencies include `structlog==24.1.0` which is no longer needed after moving to standard logging.

### Severity & Impact
- **Severity:** LOW
- **Impact Scope:** Dependencies - affects installation and virtual environment
- **User Impact:** None (reduces dependencies)

### Affected Components
- **Files:**
  - `/opt/projects/words/requirements.txt`
- **Dependencies:**
  - Remove: `structlog==24.1.0`

### Fix Strategy

1. **Remove structlog from requirements.txt**
   - Delete the line containing structlog

2. **Verify no other references**
   - Search codebase for any structlog mentions
   - Check if any indirect dependencies need structlog

3. **Update virtual environment**
   - After change, rebuild venv or uninstall structlog

### Implementation Details

**requirements.txt - BEFORE:**
```txt
# ... other dependencies ...

# Logging
structlog==24.1.0

# Configuration
# Note: pydantic version constraint <2.6,>=2.4.1 ensures compatibility with aiogram 3.4.1
```

**requirements.txt - AFTER:**
```txt
# ... other dependencies ...

# Configuration
# Note: pydantic version constraint <2.6,>=2.4.1 ensures compatibility with aiogram 3.4.1
```

**Changes:**
- Removed `structlog==24.1.0` line
- Removed "# Logging" comment (no longer needed as we use stdlib)

**Verify no pyproject.toml:**
The project doesn't have a pyproject.toml file (verified in analysis), so no changes needed there.

**Cleanup Command:**
After updating requirements.txt, run:
```bash
pip uninstall structlog -y
pip install -r requirements.txt
```

### Testing Requirements

- Verify pip install -r requirements.txt succeeds
- Verify no import errors when running application
- Run full test suite to ensure no hidden dependencies on structlog

### Validation Criteria

- [ ] structlog removed from requirements.txt
- [ ] pip install -r requirements.txt completes successfully
- [ ] Application runs without import errors
- [ ] All tests pass
- [ ] No structlog references remain in codebase

### Risks & Considerations

- **Dependency Check:** Ensure no other packages depend on structlog
- **Virtual Environment:** Developers will need to recreate or update their venv
- **CI/CD:** Any CI/CD pipelines will automatically get the updated dependencies

### Dependencies

Should be done AFTER Task 5 (update all Python files) to ensure no code still uses structlog.

---

## Task 7: Update .env.example

### Root Cause
The .env.example file doesn't include the new environment variables for log rotation configuration (MAX_LOG_SIZE, MAX_LOG_BACKUP_COUNT).

### Severity & Impact
- **Severity:** LOW
- **Impact Scope:** Configuration documentation
- **User Impact:** New developers won't know about log rotation settings

### Affected Components
- **Files:**
  - `/opt/projects/words/.env.example`
- **Sections:**
  - "# Logging" section

### Fix Strategy

1. **Add MAX_LOG_SIZE to Logging section**
   - Add after LOG_FILE
   - Include comment explaining the value

2. **Add MAX_LOG_BACKUP_COUNT to Logging section**
   - Add after MAX_LOG_SIZE
   - Include comment explaining the value

3. **Update section comment**
   - Clarify that these control log rotation

### Implementation Details

**.env.example - BEFORE:**
```bash
# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# Development
DEBUG=false
```

**.env.example - AFTER:**
```bash
# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log
# Maximum log file size in bytes before rotation (default: 10MB)
MAX_LOG_SIZE=10485760
# Number of backup log files to keep (default: 5)
MAX_LOG_BACKUP_COUNT=5

# Development
DEBUG=false
```

**Changes:**
- Added MAX_LOG_SIZE with default value and comment
- Added MAX_LOG_BACKUP_COUNT with default value and comment
- Preserved existing LOG_LEVEL and LOG_FILE entries
- Values match the defaults in logger.py

### Testing Requirements

- Verify .env.example is syntactically valid
- Check that values match defaults in logger.py
- Ensure comments are clear and helpful

### Validation Criteria

- [ ] MAX_LOG_SIZE added to .env.example
- [ ] MAX_LOG_BACKUP_COUNT added to .env.example
- [ ] Default values match logger.py defaults
- [ ] Comments explain the settings clearly
- [ ] File syntax is valid

### Risks & Considerations

- **Documentation Only:** Very low risk
- **Default Values:** Must match logger.py for consistency

### Dependencies

Should be done AFTER Task 1 (logger.py rewrite) to ensure values match implementation.

---

## Implementation Sequence

Execute tasks in this order to minimize dependencies and conflicts:

1. **Task 1** - Rewrite `src/words/utils/logger.py` (FIRST - foundation for everything)
2. **Task 7** - Update `.env.example` (simple, quick win)
3. **Task 2** - Update `CLAUDE.md` (documentation foundation)
4. **Task 3** - Update `.claude/agents/code-developer.md` (references Task 2)
5. **Task 4** - Update `.claude/agents/code-reviewer.md` (references Task 2)
6. **Task 5** - Update all Python files using logging (BIG TASK - depends on Task 1)
7. **Task 6** - Update `requirements.txt` (LAST - after code no longer uses structlog)

## Verification Checklist

After completing all tasks:

- [ ] No structlog imports anywhere in codebase
- [ ] All modules use `logger = logging.getLogger(__name__)`
- [ ] No imports from `src.words.utils.logger` (except setup_logging in __main__)
- [ ] setup_logging() called in __main__.py
- [ ] All tests pass (pytest)
- [ ] Application starts without errors
- [ ] Logs appear in logs/bot.log
- [ ] Log format matches: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- [ ] Log rotation works (test by filling log file)
- [ ] Console output works
- [ ] Environment variables (MAX_LOG_SIZE, MAX_LOG_BACKUP_COUNT) are respected
- [ ] CLAUDE.md documents logging standards
- [ ] Code-developer agent mentions logging standards
- [ ] Code-reviewer agent checks logging standards
- [ ] .env.example includes rotation settings
- [ ] requirements.txt does not include structlog
- [ ] Virtual environment doesn't have structlog installed

## Rollback Plan

If issues arise during implementation:

1. **Immediate Rollback:**
   - Revert all commits related to logging changes
   - Restore structlog in requirements.txt
   - Reinstall dependencies

2. **Partial Rollback:**
   - Keep new logger.py but don't update files yet
   - Fix issues before proceeding

3. **Testing in Branch:**
   - Perform all changes in a feature branch
   - Test thoroughly before merging to main

## Success Metrics

- **Zero structlog references** in codebase (verify with grep)
- **All tests passing** (pytest exit code 0)
- **Application runs** without import errors
- **Logs work** in both console and file
- **Log rotation works** as configured
- **Documentation complete** (CLAUDE.md, .env.example, agent files)

## Notes

- This is a significant refactoring touching many files
- Each task is independent enough to be assigned separately
- Tasks build on each other (respect dependencies)
- Testing is critical at each step
- Documentation ensures consistency going forward
- The calypso reference implementation is the gold standard
