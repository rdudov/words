# Services Directory

## Overview

This directory contains the service layer implementation for the Words application. Services orchestrate business logic between repositories and application handlers, coordinating multiple operations and managing complex workflows.

## Structure

### Available Services

- **user.py**: UserService (Phase 2)
  - User registration with timezone-aware timestamps
  - Language profile creation and management
  - Active language switching
  - Last active timestamp updates
  - Coordinates UserRepository and ProfileRepository

- **translation.py**: TranslationService (Task 3.3)
  - LLM-based word translation with caching
  - Answer validation with fuzzy matching
  - Cache-first strategy to minimize API costs
  - Graceful error handling and fallback
  - Coordinates LLMClient and CacheRepository
- **validation.py**: ValidationService (Task 4.2)
  - Three-level validation: exact, fuzzy, LLM
  - Uses FuzzyMatcher utilities for typo detection
  - Coordinates TranslationService for LLM validation
- **lesson.py**: LessonService (Tasks 4.5/4.6)
  - Lesson creation and completion summaries
  - Question generation with multiple choice options
  - Answer processing with statistics updates
  - Coordinates lesson, statistics, and word repositories

## Usage Pattern

Services are typically injected with their dependencies (repositories, clients) and used within handlers or other services:

```python
from src.words.services import TranslationService
from src.words.infrastructure.llm_client import LLMClient
from src.words.repositories.cache import CacheRepository

# Initialize dependencies
llm_client = LLMClient(api_key="...", model="gpt-4o-mini")
cache_repo = CacheRepository(session)

# Initialize service
translation_service = TranslationService(llm_client, cache_repo)

# Use service methods
result = await translation_service.translate_word(
    word="hello",
    source_lang="en",
    target_lang="ru"
)

is_correct, comment = await translation_service.validate_answer_with_llm(
    question="hello",
    expected="привет",
    user_answer="превет",
    source_lang="en",
    target_lang="ru",
    word_id=123,
    direction="forward"
)
```

## Key Features

- **Separation of Concerns**: Services isolate business logic from data access and presentation
- **Dependency Injection**: Services accept dependencies via constructor
- **Async/Await**: All service methods are async for non-blocking I/O
- **Comprehensive Logging**: All operations are logged for monitoring and debugging
- **Error Handling**: Services handle errors gracefully with appropriate fallbacks
- **Cache Optimization**: TranslationService implements cache-first strategy
- **Validation Pipeline**: ValidationService provides exact/fuzzy/LLM checks
- **Lesson Orchestration**: LessonService coordinates lesson flow and stats
- **Test Coverage**: Comprehensive unit and integration tests for all services

## Testing

Tests are located in `/home/user/words/tests/services/`:
- `test_user.py`: Tests for UserService (32 tests)
- `test_translation.py`: Tests for TranslationService (19 tests)

All service tests use mock-based unit tests to isolate business logic and verify correct coordination of dependencies.

## Design Principles

1. **Single Responsibility**: Each service has a clear, focused purpose
2. **Dependency Inversion**: Services depend on abstractions (repository interfaces)
3. **Fail Fast**: Input validation happens early with clear error messages
4. **Observable**: All operations are logged for monitoring
5. **Resilient**: Graceful degradation on external service failures
