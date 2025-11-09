# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Task 3.5: Word Service Bug Fixes** - Fixed critical issues identified in code review
  - **CRITICAL**: Fixed translation data structure mismatch
    - Word model expects translations as dict: `{"ru": ["привет", "здравствуй"]}`
    - TranslationService returns list: `["привет", "здравствуй"]`
    - Now transforms translation list to dict format: `{target_language: translation_list}`
  - **HIGH**: Fixed incorrect language assignment for word storage
    - Words now stored with `source_language` instead of `target_language`
    - Updated `find_by_text_and_language()` calls to use `source_language`
    - Translations dict uses `target_language` as key
  - **HIGH**: Added comprehensive error handling
    - Wrapped entire method in try/except block
    - Added error logging with full context (profile_id, word, languages, error details)
    - Added transaction rollback on errors
    - Re-raises exceptions to allow caller handling
  - **HIGH**: Improved transaction management
    - Word now committed separately before creating UserWord
    - Added explicit rollback on error
    - Ensures data consistency
  - **MEDIUM**: Added input validation
    - Validates profile_id (not None, not zero, not negative)
    - Validates word_text (not empty, not whitespace-only)
    - Validates language codes (not empty, not whitespace-only)
    - Raises ValueError with descriptive messages
  - **MEDIUM**: Enhanced logging
    - Added `word_addition_started` log at method entry
    - Added `fetching_translation` debug log
    - Added `word_created` log for new words
    - Added `word_already_exists_reusing` debug log for existing words
    - Improved `word_already_in_user_vocabulary` warning with word text
    - Enhanced `word_added_to_user_vocabulary` with status
    - Added error logging for validation and general errors
  - Updated all 27 tests to match new behavior
    - Updated tests for correct language assignment (source vs target)
    - Updated tests for dict translation format
    - Added 7 new tests for input validation
    - Added 3 new tests for error handling and logging
    - All tests passing with 100% code coverage

### Added
- **Task 3.6: Add Word Handler** - Telegram bot handlers for adding words to user vocabulary
  - `cmd_add_word` handler for "➕ Add Word" button
    - Displays instruction message to user
    - Transitions to AddWordStates.waiting_for_word state
  - `process_word_input` handler for word processing
    - Validates word input (rejects empty or whitespace-only)
    - Shows processing message during translation lookup
    - Verifies user has active profile (redirects to registration if not)
    - Sets up all required services (LLM, cache, translation, word)
    - Implements automatic language detection with fallback:
      - First tries target→native (word in learning language)
      - Falls back to native→target (word in native language)
    - Adds word to user vocabulary via WordService
    - Formats and displays translation result with up to 2 examples
    - Handles errors gracefully with user-friendly messages
    - Clears FSM state when done
  - Router registered in main bot setup
  - HTML formatting for messages with bold word highlighting
  - Comprehensive error handling and logging
  - Comprehensive test suite with 19 tests (100% code coverage)
    - Unit tests with mocks for both handlers
    - Tests for state transitions
    - Tests for successful word addition
    - Tests for language detection (both directions)
    - Tests for validation (empty input, whitespace)
    - Tests for error handling and fallback
    - Tests for user profile validation
    - Tests for processing message display and deletion
    - Tests for translation result formatting
    - Integration tests for complete flow
  - Located at: `src/words/bot/handlers/words.py`
  - Tests at: `tests/bot/handlers/test_words.py`
  - Exports: `src/words/bot/handlers/__init__.py` updated
  - Registration: `src/words/bot/__init__.py` updated

- **Task 3.5: Word Service** - Service layer for word management and vocabulary operations
  - `WordService` class orchestrating word management, translation, and statistics
  - `add_word_for_user()` method for adding words to user vocabulary
    - Fetches translations via TranslationService (cache-first)
    - Creates or finds existing Word entity
    - Implements word deduplication (prevents adding same word twice)
    - Creates UserWord with status=NEW
    - Comprehensive error handling and logging
  - `get_word_with_translations()` method for retrieving word translations
    - Delegates to TranslationService for cache-first translation lookup
    - Returns translation data with examples and word forms
  - `get_user_vocabulary_stats()` method for vocabulary statistics
    - Returns counts by learning status (NEW, LEARNING, REVIEWING, MASTERED)
    - Calculates total vocabulary size
  - Comprehensive test suite with 27 tests (100% code coverage)
    - Unit tests with mocks for all methods
    - Tests for new word creation flow
    - Tests for existing word handling
    - Tests for word deduplication logic
    - Tests for statistics calculation
    - Tests for input validation (7 tests)
    - Tests for error handling (3 tests)
    - Integration tests with multiple users
    - Edge case handling tests
  - Located at: `src/words/services/word.py`
  - Tests at: `tests/services/test_word.py`

- **Task 3.3: Translation Service** - Service layer for LLM-based translation and validation
  - `TranslationService` class orchestrating LLM client and cache repository
  - `translate_word()` method with cache-first strategy
    - Checks cache before calling LLM to minimize API costs
    - Caches translation results that never expire
    - Returns word translations, examples, and word forms
    - Comprehensive error handling and logging
  - `validate_answer_with_llm()` method with cache-first strategy
    - Intelligent answer validation with fuzzy matching
    - Graceful fallback on LLM errors (returns user-friendly message)
    - Caches validation results by word ID, direction, and answers
  - Comprehensive test suite with 19 tests (100% code coverage)
    - Unit tests with mocks for both methods
    - Tests for cache hits and misses
    - Tests for LLM errors and fallback behavior
    - Tests for proper logging
    - Integration tests with mocked dependencies
    - Edge case handling tests
  - Located at: `src/words/services/translation.py`
  - Tests at: `tests/services/test_translation.py`

- **Task 3.2: Cache Repository** - Repository for managing LLM result caching
  - `CacheRepository` class for translation and validation caching
  - `get_translation()` and `set_translation()` methods for translation caching
    - Automatic cache expiration handling
    - Upsert logic to avoid duplicate cache entries
    - Case-insensitive word lookup (normalized to lowercase)
  - `get_validation()` and `set_validation()` methods for validation result caching
    - Caches LLM validation results by word, direction, expected and user answers
    - Case-insensitive answer lookup
  - Reduces API costs by avoiding repeated LLM calls for identical requests
  - Comprehensive test suite with 25 tests (100% code coverage)
    - Unit tests with mocks for all methods
    - Integration tests with real SQLite database
    - Tests for cache hits/misses, expiration, upsert, and case sensitivity
  - Located at: `src/words/repositories/cache.py`
  - Tests at: `tests/repositories/test_cache.py`

- **Task 3.1: LLM Client** - OpenAI-based LLM client for word translation and answer validation
  - Base `LLMClient` class with async OpenAI integration
  - `translate_word()` method for getting word translations, examples, and word forms
  - `validate_answer()` method for intelligent answer validation with fuzzy matching
  - Automatic retry logic with exponential backoff using tenacity
  - JSON response parsing with comprehensive error handling
  - `RateLimitedLLMClient` extending base client with:
    - Token bucket rate limiting using AsyncLimiter (configurable, default: 2500 req/min)
    - Concurrent request limiting using Semaphore (configurable, default: 10 concurrent)
    - Circuit breaker pattern for fault tolerance (opens after 5 failures, recovers after 60s)
  - Comprehensive test suite with 25 tests (89% code coverage)
  - Located at: `src/words/infrastructure/llm_client.py`

## [0.2.0] - 2025-11-09

### Added
- **Phase 2: User Management** - Complete user registration and management system
  - Base repository pattern for data access layer
  - User repository with CRUD operations
  - User service with business logic
  - Bot state machine for conversation flows
  - Telegram keyboards for user interaction
  - Registration handler for new users
  - Main bot setup with all components integrated

## [0.1.0] - 2025-11-08

### Added
- **Phase 1: Core Infrastructure** - Complete database and configuration setup
  - Configuration management with Pydantic Settings
  - SQLAlchemy async database infrastructure
  - ORM models for User, Word, Lesson, Statistics, and Cache tables
  - Structured logging with development and production modes
  - Database initialization script
  - Comprehensive test suite for infrastructure and models

### Added
- **Phase 0: Project Setup** - Initial project structure and configuration
  - Project directory structure
  - Python virtual environment setup
  - Dependencies management (requirements.txt)
  - Configuration files (.env template, pytest.ini)
  - Initial documentation (README, CLAUDE.md)
