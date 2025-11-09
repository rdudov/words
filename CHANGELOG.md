# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
