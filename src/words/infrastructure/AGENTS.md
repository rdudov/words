# Infrastructure Directory

This directory contains infrastructure components for the Words application, including external service integrations, database management, and other technical infrastructure.

## Files

### `__init__.py`
Module initialization file that exports infrastructure components for easy importing throughout the application.

**Exports:**
- `engine` - SQLAlchemy async database engine
- `AsyncSessionLocal` - Database session factory
- `get_session` - Context manager for database sessions
- `init_db` - Database initialization function
- `close_db` - Database cleanup function
- `LLMClient` - Base LLM client for OpenAI integration
- `RateLimitedLLMClient` - LLM client with rate limiting and circuit breaker

### `database.py`
Database infrastructure module providing SQLAlchemy async engine, session management, and database lifecycle functions.

**Key Components:**
- `engine` - Async SQLAlchemy engine configured from settings
- `AsyncSessionLocal` - Session factory for creating database sessions
- `get_session()` - Async context manager for automatic session cleanup and transaction management
- `init_db()` - Initialize database schema (create all tables)
- `close_db()` - Dispose database connections on shutdown

**Features:**
- Automatic commit on success, rollback on error
- NullPool for SQLite connections (testing)
- Standard pool for PostgreSQL (production)
- Connection pre-ping for reliability

### `llm_client.py`
LLM (Large Language Model) client for OpenAI API integration, providing word translation and answer validation services.

**Key Components:**

#### `LLMClient`
Base LLM client with OpenAI async integration.

**Features:**
- Async OpenAI API client
- Automatic retry logic with exponential backoff (3 attempts, 2-10s wait)
- JSON response parsing
- Comprehensive error handling
- Structured logging

**Methods:**
- `translate_word(word, source_lang, target_lang)` - Get word translations, examples, and word forms
- `validate_answer(question, expected_answer, user_answer, source_lang, target_lang)` - Validate user answers with fuzzy matching
- `_build_translation_prompt()` - Build prompts for translation requests
- `_build_validation_prompt()` - Build prompts for answer validation

#### `RateLimitedLLMClient`
Extended LLM client with rate limiting and fault tolerance.

**Features:**
- **Token Bucket Rate Limiting:** AsyncLimiter ensures API quota compliance (default: 2500 requests/minute with safety margin)
- **Concurrent Request Limiting:** Semaphore controls max concurrent requests (default: 10)
- **Circuit Breaker Pattern:** Automatically opens after 5 consecutive failures, attempts recovery after 60 seconds
- Inherits all features from base `LLMClient`

**Configuration:**
- `max_concurrent` - Maximum concurrent requests (default: 10)
- `requests_per_minute` - Maximum requests per minute (default: 2500, OpenAI limit: 3000)

**Methods:**
- `translate_word()` - Translation with rate limiting and circuit breaker
- `validate_answer()` - Validation with rate limiting and circuit breaker
- `_call_with_circuit_breaker()` - Execute calls with circuit breaker protection

**Circuit Breaker Behavior:**
- Opens after 5 consecutive failures
- Stops sending requests to LLM API
- After 60 seconds, attempts one request to test recovery
- Closes on successful recovery

## Usage Examples

### Database Session Management

```python
from src.words.infrastructure import get_session
from src.words.models import User

async def create_user(telegram_id: int, username: str):
    async with get_session() as session:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        # Automatically commits on success, rolls back on error
```

### LLM Client Usage

```python
from src.words.infrastructure import RateLimitedLLMClient
from src.words.config.settings import settings

# Initialize rate-limited client
llm_client = RateLimitedLLMClient(
    api_key=settings.llm_api_key,
    model=settings.llm_model,
    max_concurrent=10,
    requests_per_minute=2500
)

# Translate a word
translation = await llm_client.translate_word(
    word="hello",
    source_lang="English",
    target_lang="Russian"
)
# Returns: {
#     "word": "hello",
#     "translations": ["привет", "здравствуй"],
#     "examples": [...],
#     "word_forms": {...}
# }

# Validate user answer
validation = await llm_client.validate_answer(
    question="hello",
    expected_answer="привет",
    user_answer="привет",
    source_lang="English",
    target_lang="Russian"
)
# Returns: {
#     "is_correct": true,
#     "comment": "Правильно!"
# }
```

## Dependencies

- **SQLAlchemy** - Async ORM and database toolkit
- **aiogram** - Telegram Bot API framework
- **openai** - OpenAI API client
- **tenacity** - Retry logic with exponential backoff
- **aiolimiter** - Async rate limiting (token bucket)
- **circuitbreaker** - Circuit breaker pattern implementation

## Testing

All infrastructure components have comprehensive test coverage located in `tests/infrastructure/`:
- `test_database.py` - Database infrastructure tests (48% coverage)
- `test_llm_client.py` - LLM client tests (89% coverage, 25 tests)

Run tests with:
```bash
pytest tests/infrastructure/ -v
```
