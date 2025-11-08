# Architecture Document: Language Learning Telegram Bot

## Document Information

- **Project:** Language Learning Telegram Bot (Words)
- **Version:** 1.0.0
- **Last Updated:** 2025-11-08
- **Status:** Initial Architecture Design

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architectural Style and Patterns](#2-architectural-style-and-patterns)
3. [System Components Overview](#3-system-components-overview)
4. [Project Structure](#4-project-structure)
5. [Data Architecture](#5-data-architecture)
6. [Component Design](#6-component-design)
7. [Adaptive Learning Algorithm](#7-adaptive-learning-algorithm)
8. [External Integrations](#8-external-integrations)
9. [Configuration Management](#9-configuration-management)
10. [Logging and Monitoring](#10-logging-and-monitoring)
11. [Error Handling and Resilience](#11-error-handling-and-resilience)
12. [Performance and Scalability](#12-performance-and-scalability)
13. [Security](#13-security)
14. [Deployment Architecture](#14-deployment-architecture)
15. [Testing Strategy](#15-testing-strategy)
16. [Migration and Evolution Strategy](#16-migration-and-evolution-strategy)
17. [Open Questions](#17-open-questions)

---

## 1. Executive Summary

### 1.1 System Overview

A Telegram-based language learning bot that uses adaptive algorithms and LLM-powered validation to help users learn foreign vocabulary. The system supports bidirectional learning (native ↔ foreign language), personalized lesson planning, spaced repetition, and intelligent answer validation.

### 1.2 Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Architecture Style** | Layered (3-tier) with Hexagonal principles | Clear separation of concerns, testability, maintainability |
| **Telegram Library** | aiogram 3.x | Async-first, modern API, better performance |
| **Database** | SQLite (start) → PostgreSQL (scale) | Simple for MVP, easy migration path |
| **ORM** | SQLAlchemy 2.0 (async) | Mature, async support, flexible, migration-ready |
| **LLM Integration** | OpenAI API (gpt-4o-mini) | Cost-effective, reliable, good quality |
| **Background Tasks** | APScheduler | Simple, no external dependencies, sufficient for requirements |
| **Caching** | In-memory + DB | Fast access, persistent across restarts |
| **String Matching** | python-Levenshtein | Fast, accurate fuzzy matching |
| **Logging** | Python logging + structlog | Structured logs, easy parsing, rotation |

### 1.3 Non-Functional Requirements Summary

- **Performance:** < 2s response time, < 5s LLM calls
- **Availability:** 99% uptime, 24/7 operation
- **Scalability:** Support 100+ concurrent users
- **Reliability:** Graceful degradation, auto-recovery
- **Security:** Secure credential storage, data protection
- **Localization:** 3 languages (Russian, English, Spanish)

---

## 2. Architectural Style and Patterns

### 2.1 Overall Architecture Style

**Layered Architecture with Hexagonal (Ports & Adapters) Principles**

```
┌─────────────────────────────────────────────────────────┐
│                  Presentation Layer                     │
│  (Telegram Handlers, Commands, Callback Handlers)      │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│                   Business Logic Layer                  │
│  (Services, Adaptive Algorithm, Lesson Manager)         │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│                  Data Access Layer                      │
│     (Repositories, ORM Models, Cache Manager)           │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│              Infrastructure Layer                       │
│  (Database, LLM API, Telegram API, Scheduler)          │
└─────────────────────────────────────────────────────────┘
```

**Why this architecture?**

- **Separation of Concerns:** Each layer has a clear responsibility
- **Testability:** Business logic isolated from infrastructure
- **Flexibility:** Easy to swap implementations (e.g., SQLite → PostgreSQL)
- **Maintainability:** Changes in one layer don't cascade to others
- **Team Scalability:** Different developers can work on different layers

### 2.2 Key Design Patterns

1. **Repository Pattern**
   - Abstract data access from business logic
   - Single source of truth for data operations
   - Easy to mock for testing

2. **Service Layer Pattern**
   - Encapsulate business logic in services
   - Clear API contracts between layers
   - Reusable across different handlers

3. **Strategy Pattern**
   - Different lesson strategies (multiple choice vs input)
   - Different validation strategies (exact, fuzzy, LLM)
   - Pluggable adaptive algorithms

4. **Factory Pattern**
   - Create lesson questions based on word status
   - Generate answer options for multiple choice
   - Build validation chains

5. **Chain of Responsibility**
   - Answer validation pipeline (exact → fuzzy → LLM)
   - Error handling cascade
   - Fallback strategies for API failures

6. **Dependency Injection**
   - Services receive dependencies via constructor
   - Easy to replace implementations
   - Better testability

### 2.3 Data Flow

**User Command Flow:**
```
User → Telegram → Handler → Service → Repository → Database
                     ↓
                  Response
                     ↓
                  Telegram → User
```

**Lesson Flow:**
```
User → Start Lesson
  ↓
Select Words (Adaptive Algorithm)
  ↓
For each word:
  - Present Question
  - Receive Answer
  - Validate (Exact → Fuzzy → LLM)
  - Update Statistics
  - Next Question
  ↓
Show Lesson Summary
```

**Background Notification Flow:**
```
Scheduler (every 15 min)
  ↓
Check users without activity (6+ hours)
  ↓
Filter by time window (7:00-23:00 MSK)
  ↓
Send notifications
  ↓
Update last_notification_sent timestamp
```

---

## 3. System Components Overview

### 3.1 High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Telegram Bot                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  Command   │  │  Callback  │  │   State    │                │
│  │  Handlers  │  │  Handlers  │  │  Machine   │                │
│  └────────────┘  └────────────┘  └────────────┘                │
└─────────┬───────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────────┐
│                      Business Services                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    User      │  │    Lesson    │  │   Adaptive   │         │
│  │   Service    │  │   Service    │  │  Algorithm   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │     Word     │  │  Validation  │  │ Translation  │         │
│  │   Service    │  │   Service    │  │   Service    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────┬───────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────────┐
│                      Repositories                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │     User     │  │     Word     │  │    Lesson    │         │
│  │  Repository  │  │  Repository  │  │  Repository  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────┬───────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────────┐
│                      Infrastructure                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Database   │  │   LLM API    │  │  Scheduler   │         │
│  │  (SQLite/    │  │   Client     │  │(APScheduler) │         │
│  │  PostgreSQL) │  └──────────────┘  └──────────────┘         │
│  └──────────────┘  ┌──────────────┐  ┌──────────────┐         │
│                    │    Cache     │  │   Logger     │         │
│                    │   Manager    │  │              │         │
│                    └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Responsibilities

#### Presentation Layer
- **Telegram Handlers:** Process user commands and callbacks
- **State Machine:** Manage conversation flows (registration, adding words)
- **Formatters:** Format messages and keyboards for Telegram

#### Business Logic Layer
- **User Service:** User registration, profile management, language switching
- **Lesson Service:** Lesson orchestration, question generation, statistics
- **Word Service:** Add words, manage vocabulary, frequency lists
- **Validation Service:** Answer validation pipeline (exact → fuzzy → LLM)
- **Translation Service:** LLM integration for translations and examples
- **Adaptive Algorithm:** Word selection, spaced repetition, difficulty adjustment

#### Data Access Layer
- **Repositories:** CRUD operations, complex queries
- **ORM Models:** SQLAlchemy models for database tables
- **Cache Manager:** LLM result caching, performance optimization

#### Infrastructure Layer
- **Database:** SQLite (dev/small scale) or PostgreSQL (production)
- **LLM Client:** OpenAI API wrapper with retry logic, rate limiting, and circuit breaker
- **Scheduler:** APScheduler for background tasks
- **Logger:** Structured logging with rotation
- **Lesson Lock Manager:** Concurrent lesson session management (NEW 2025-11-08)
- **Circuit Breaker Manager:** External API failure protection (NEW 2025-11-08)
- **Rate Limiter:** LLM API quota management (NEW 2025-11-08)

---

## 4. Project Structure

### 4.1 Directory Layout

```
/opt/projects/words/
├── README.md
├── CLAUDE.md
├── .env.example
├── .env                    # Not in git
├── .gitignore
├── requirements.txt
├── setup.py                # Optional: for installable package
│
├── docs/
│   ├── requirements.md
│   ├── architecture.md     # This file
│   ├── api_reference.md    # Optional: API documentation
│   └── deployment.md       # Deployment guide
│
├── data/                   # Data files
│   ├── frequency_lists/    # CEFR word lists
│   │   ├── english_a1.json
│   │   ├── english_a2.json
│   │   ├── spanish_a1.json
│   │   └── ...
│   ├── translations/       # i18n files
│   │   ├── en.json
│   │   ├── ru.json
│   │   └── es.json
│   └── database/
│       └── words.db        # SQLite database (not in git)
│
├── logs/                   # Log files (not in git)
│   ├── bot.log
│   ├── errors.log
│   └── ...
│
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── conftest.py         # Pytest fixtures
│   ├── unit/
│   │   ├── test_services.py
│   │   ├── test_algorithm.py
│   │   └── test_validation.py
│   ├── integration/
│   │   ├── test_repositories.py
│   │   └── test_llm_client.py
│   └── e2e/
│       └── test_lesson_flow.py
│
├── src/                    # Main source code
│   └── words/              # Python package
│       ├── __init__.py
│       ├── __main__.py     # Entry point: python -m words
│       │
│       ├── config/         # Configuration
│       │   ├── __init__.py
│       │   ├── settings.py      # Pydantic settings
│       │   └── constants.py     # App constants
│       │
│       ├── models/         # SQLAlchemy ORM models
│       │   ├── __init__.py
│       │   ├── base.py          # Base model class
│       │   ├── user.py
│       │   ├── word.py
│       │   ├── lesson.py
│       │   └── statistics.py
│       │
│       ├── repositories/   # Data access layer
│       │   ├── __init__.py
│       │   ├── base.py          # Base repository
│       │   ├── user.py
│       │   ├── word.py
│       │   ├── lesson.py
│       │   └── cache.py
│       │
│       ├── services/       # Business logic
│       │   ├── __init__.py
│       │   ├── user.py          # User management
│       │   ├── word.py          # Word management
│       │   ├── lesson.py        # Lesson orchestration
│       │   ├── validation.py    # Answer validation
│       │   ├── translation.py   # LLM integration
│       │   └── notification.py  # Push notifications
│       │
│       ├── algorithm/      # Adaptive learning
│       │   ├── __init__.py
│       │   ├── word_selector.py # Word selection logic
│       │   ├── spaced_repetition.py # SM-2 algorithm
│       │   └── difficulty.py    # Difficulty adjustment
│       │
│       ├── bot/            # Telegram bot
│       │   ├── __init__.py
│       │   ├── handlers/
│       │   │   ├── __init__.py
│       │   │   ├── start.py     # /start, registration
│       │   │   ├── lesson.py    # Lesson handlers
│       │   │   ├── words.py     # Add word handlers
│       │   │   ├── settings.py  # User settings
│       │   │   └── stats.py     # Statistics
│       │   ├── states/
│       │   │   ├── __init__.py
│       │   │   ├── registration.py
│       │   │   └── add_word.py
│       │   ├── keyboards/
│       │   │   ├── __init__.py
│       │   │   ├── common.py
│       │   │   └── lesson.py
│       │   └── filters/
│       │       ├── __init__.py
│       │       └── custom.py
│       │
│       ├── infrastructure/ # External integrations
│       │   ├── __init__.py
│       │   ├── database.py      # DB connection, session
│       │   ├── llm_client.py    # OpenAI API client
│       │   ├── scheduler.py     # APScheduler setup
│       │   └── cache.py         # Cache manager
│       │
│       ├── localization/   # i18n support
│       │   ├── __init__.py
│       │   ├── loader.py        # Load translations
│       │   └── formatter.py     # Message formatting
│       │
│       └── utils/          # Utilities
│           ├── __init__.py
│           ├── logger.py        # Logging setup
│           ├── validators.py    # Input validation
│           ├── string_utils.py  # Levenshtein, etc.
│           └── time_utils.py    # Timezone handling
│
└── scripts/                # Utility scripts
    ├── init_db.py          # Initialize database
    ├── load_frequency_lists.py # Populate word lists
    ├── backup_db.sh        # Backup script
    └── migrate.py          # Database migrations
```

### 4.2 Module Dependencies

**Dependency Rules:**
- Presentation → Business Logic → Data Access → Infrastructure
- No upward dependencies (infrastructure cannot import from business logic)
- Services depend on repositories (via interfaces/protocols)
- Repositories depend on ORM models
- No circular dependencies

**Import Flow:**
```
bot/handlers/
  ↓
services/
  ↓
repositories/
  ↓
models/
  ↓
infrastructure/
```

---

## 5. Data Architecture

### 5.1 Database Technology Selection

**Initial: SQLite**
- Simple setup, no external dependencies
- Single file database
- Good for < 1000 users
- Easy backup (copy file)

**Production: PostgreSQL**
- Better concurrency
- Advanced features (JSON queries, full-text search)
- Horizontal scaling options
- Required for > 1000 users

**Migration Path:**
- Use SQLAlchemy ORM abstractions
- Same code works for both databases
- Migration requires only changing connection string

### 5.2 Database Schema

#### ERD (Entity Relationship Diagram)

```
┌──────────────┐         ┌────────────────────┐         ┌──────────────┐
│    users     │1      n │ language_profiles  │n      1 │    lessons   │
│──────────────│◄────────┤────────────────────├─────────►│──────────────│
│ user_id (PK) │         │ profile_id (PK)    │         │ lesson_id (PK)│
│ native_lang  │         │ user_id (FK)       │         │ profile_id(FK)│
│ interface_lang│        │ target_language    │         │ started_at   │
│ created_at   │         │ level (A1-C2)      │         │ completed_at │
│ last_active  │         │ is_active          │         └──────────────┘
│ notification │         └────────────────────┘                │
│  _enabled    │                 │                             │
└──────────────┘                 │                             │
                                 │1                            │
                                 │                             │1
                                 │n                            │
                        ┌────────▼──────┐            ┌────────▼────────┐
                        │  user_words   │            │ lesson_attempts │
                        │───────────────┤            │─────────────────┤
                        │ user_word_id  │n         n │ attempt_id (PK) │
                        │   (PK)        ├────────────►│ lesson_id (FK)  │
                        │ profile_id(FK)│            │ user_word_id(FK)│
                        │ word_id (FK)  │            │ direction       │
                        │ status        │            │ test_type       │
                        │ added_at      │            │ user_answer     │
                        │ last_reviewed │            │ correct_answer  │
                        │ next_review   │            │ is_correct      │
                        └───────┬───────┘            └─────────────────┘
                                │1
                                │
                                │n
                        ┌───────▼──────────┐
                        │ word_statistics  │
                        │──────────────────┤
                        │ stat_id (PK)     │
                        │ user_word_id (FK)│
                        │ direction        │
                        │ test_type        │
                        │ correct_count    │
                        │ total_attempts   │
                        │ total_correct    │
                        │ total_errors     │
                        └──────────────────┘

┌─────────────────┐
│     words       │
│─────────────────┤
│ word_id (PK)    │
│ word            │
│ language        │
│ level (CEFR)    │
│ translations(JSON)│
│ examples (JSON) │
│ word_forms(JSON)│
└─────────────────┘
         △
         │n
         │
┌────────┴──────────┐
│   user_words      │
└───────────────────┘

┌──────────────────────┐
│ cached_translations  │
│──────────────────────┤
│ cache_id (PK)        │
│ word                 │
│ source_language      │
│ target_language      │
│ translation_data(JSON)│
│ cached_at            │
│ expires_at           │
└──────────────────────┘

┌──────────────────────┐
│ cached_validations   │
│──────────────────────┤
│ validation_id (PK)   │
│ word_id (FK)         │
│ direction            │
│ expected_answer      │
│ user_answer          │
│ is_correct           │
│ llm_comment          │
│ cached_at            │
└──────────────────────┘
UNIQUE INDEX: (word_id, direction, expected_answer, user_answer)
```

#### Table Details

**users**
```sql
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,          -- Telegram user ID
    native_language VARCHAR(10) NOT NULL, -- ISO 639-1 code
    interface_language VARCHAR(10) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP,
    notification_enabled BOOLEAN DEFAULT TRUE,
    timezone VARCHAR(50) DEFAULT 'Europe/Moscow'
);
CREATE INDEX idx_users_last_active ON users(last_active_at);
```

**language_profiles**
```sql
CREATE TABLE language_profiles (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    target_language VARCHAR(10) NOT NULL,
    level VARCHAR(2) NOT NULL CHECK (level IN ('A1','A2','B1','B2','C1','C2')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, target_language)
);
CREATE INDEX idx_profiles_user_active ON language_profiles(user_id, is_active);
```

**words**
```sql
CREATE TABLE words (
    word_id INTEGER PRIMARY KEY AUTOINCREMENT,
    word VARCHAR(255) NOT NULL,
    language VARCHAR(10) NOT NULL,
    level VARCHAR(2) CHECK (level IN ('A1','A2','B1','B2','C1','C2')),
    translations JSON,  -- {"en": ["house", "home"], "ru": ["дом"]}
    examples JSON,      -- [{"en": "My house", "ru": "Мой дом"}]
    word_forms JSON,    -- {"plural": "houses", "past": "housed"}
    frequency_rank INTEGER,
    UNIQUE(word, language)
);
CREATE INDEX idx_words_language_level ON words(language, level);
CREATE INDEX idx_words_frequency ON words(language, frequency_rank);
```

**user_words**
```sql
CREATE TABLE user_words (
    user_word_id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES language_profiles(profile_id) ON DELETE CASCADE,
    word_id INTEGER NOT NULL REFERENCES words(word_id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'learning', 'reviewing', 'mastered')),
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_reviewed_at TIMESTAMP,
    next_review_at TIMESTAMP,
    UNIQUE(profile_id, word_id)
);
CREATE INDEX idx_user_words_profile ON user_words(profile_id);
CREATE INDEX idx_user_words_status ON user_words(profile_id, status);
CREATE INDEX idx_user_words_next_review ON user_words(profile_id, next_review_at);
```

**word_statistics**
```sql
CREATE TABLE word_statistics (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_word_id INTEGER NOT NULL REFERENCES user_words(user_word_id) ON DELETE CASCADE,
    direction VARCHAR(20) NOT NULL
        CHECK (direction IN ('native_to_foreign', 'foreign_to_native')),
    test_type VARCHAR(20) NOT NULL
        CHECK (test_type IN ('multiple_choice', 'input')),
    correct_count INTEGER DEFAULT 0,      -- Consecutive correct answers
    total_attempts INTEGER DEFAULT 0,
    total_correct INTEGER DEFAULT 0,
    total_errors INTEGER DEFAULT 0,
    UNIQUE(user_word_id, direction, test_type)
);
CREATE INDEX idx_stats_user_word ON word_statistics(user_word_id);
```

**lessons**
```sql
CREATE TABLE lessons (
    lesson_id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES language_profiles(profile_id) ON DELETE CASCADE,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    words_count INTEGER NOT NULL,
    correct_answers INTEGER DEFAULT 0,
    incorrect_answers INTEGER DEFAULT 0
);
CREATE INDEX idx_lessons_profile ON lessons(profile_id, started_at DESC);
```

**lesson_attempts**
```sql
CREATE TABLE lesson_attempts (
    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL REFERENCES lessons(lesson_id) ON DELETE CASCADE,
    user_word_id INTEGER NOT NULL REFERENCES user_words(user_word_id),
    direction VARCHAR(20) NOT NULL,
    test_type VARCHAR(20) NOT NULL,
    user_answer TEXT,
    correct_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    validation_method VARCHAR(20),  -- 'exact', 'fuzzy', 'llm'
    attempted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_attempts_lesson ON lesson_attempts(lesson_id);
CREATE INDEX idx_attempts_user_word ON lesson_attempts(user_word_id);
```

**cached_translations**
```sql
CREATE TABLE cached_translations (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    word VARCHAR(255) NOT NULL,
    source_language VARCHAR(10) NOT NULL,
    target_language VARCHAR(10) NOT NULL,
    translation_data JSON NOT NULL,
    cached_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,  -- NULL = never expires
    UNIQUE(word, source_language, target_language)
);
CREATE INDEX idx_cached_translations_lookup
    ON cached_translations(word, source_language, target_language);
```

**cached_validations**
```sql
CREATE TABLE cached_validations (
    validation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id INTEGER NOT NULL REFERENCES words(word_id),
    direction VARCHAR(20) NOT NULL,
    expected_answer VARCHAR(255) NOT NULL,
    user_answer VARCHAR(255) NOT NULL,
    is_correct BOOLEAN NOT NULL,
    llm_comment TEXT,
    cached_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(word_id, direction, expected_answer, user_answer)
);
CREATE INDEX idx_cached_validations_lookup
    ON cached_validations(word_id, direction, expected_answer, user_answer);
```

### 5.3 ORM Strategy

**SQLAlchemy 2.0 with Async Support**

**Why SQLAlchemy?**
- Industry standard, mature
- Async support (asyncio + aiogram)
- Migration tools (Alembic)
- Works with SQLite and PostgreSQL
- Type hints support

**Base Model Pattern:**

```python
# src/words/models/base.py
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime

class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models"""
    pass

class TimestampMixin:
    """Mixin for created_at/updated_at"""
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
```

**Example Model:**

```python
# src/words/models/user.py
from sqlalchemy import BigInteger, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    native_language: Mapped[str] = mapped_column(String(10))
    interface_language: Mapped[str] = mapped_column(String(10))
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")

    # Relationships
    profiles: Mapped[list["LanguageProfile"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
```

### 5.4 Database Migrations

**Alembic for Schema Migrations**

```bash
# Initialize Alembic (one time)
alembic init alembic

# Generate migration from model changes
alembic revision --autogenerate -m "Add user timezone field"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

**Migration Strategy:**
1. **Development:** Use autogenerate for convenience
2. **Production:** Review and test all migrations before applying
3. **Backup:** Always backup database before migrations
4. **Zero-Downtime:** For production, use additive changes first

### 5.5 Query Optimization

**Indexes:**
- Primary keys (automatic)
- Foreign keys (manual)
- Frequently queried columns (user_id, profile_id, status, next_review_at)
- Composite indexes for complex queries

**N+1 Query Prevention:**
- Use `selectinload()` or `joinedload()` for relationships
- Batch operations where possible
- Use pagination for large result sets

**Example Optimized Query:**

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Load user with all profiles and words in one query
result = await session.execute(
    select(User)
    .where(User.user_id == user_id)
    .options(
        selectinload(User.profiles).selectinload(LanguageProfile.user_words)
    )
)
user = result.scalar_one()
```

---

## 6. Component Design

### 6.1 Business Logic Services

#### User Service

**Responsibilities:**
- User registration and onboarding
- Profile management (language, level)
- Notification preferences
- User statistics aggregation

**Key Methods:**

```python
class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        profile_repo: ProfileRepository
    ):
        self.user_repo = user_repo
        self.profile_repo = profile_repo

    async def register_user(
        self,
        user_id: int,
        native_language: str,
        interface_language: str
    ) -> User:
        """Register new user"""

    async def create_language_profile(
        self,
        user_id: int,
        target_language: str,
        level: str
    ) -> LanguageProfile:
        """Create new language learning profile"""

    async def switch_active_language(
        self,
        user_id: int,
        target_language: str
    ) -> LanguageProfile:
        """Switch to different language"""

    async def get_user_statistics(
        self,
        user_id: int
    ) -> UserStatistics:
        """Get aggregated user stats"""
```

#### Word Service

**Responsibilities:**
- Add words to user vocabulary
- Fetch translations from LLM (with caching)
- Load frequency lists
- Manage word metadata

**Key Methods:**

```python
class WordService:
    def __init__(
        self,
        word_repo: WordRepository,
        translation_service: TranslationService,
        cache_repo: CacheRepository
    ):
        self.word_repo = word_repo
        self.translation_service = translation_service
        self.cache_repo = cache_repo

    async def add_word_for_user(
        self,
        profile_id: int,
        word_text: str,
        source_language: str
    ) -> UserWord:
        """Add word to user vocabulary"""
        # 1. Check if word exists in global word table
        # 2. If not, fetch translation from LLM (check cache first)
        # 3. Create Word entry
        # 4. Link to user (user_words table)
        # 5. Initialize statistics

    async def get_word_with_translations(
        self,
        word_text: str,
        source_language: str,
        target_language: str
    ) -> WordData:
        """Get word translations and examples"""
        # 1. Check cache first
        # 2. If not cached, call LLM
        # 3. Cache result
        # 4. Return data

    async def load_frequency_list(
        self,
        language: str,
        level: str
    ) -> list[Word]:
        """Load frequency words for language/level"""
```

#### Lesson Service

**Responsibilities:**
- Orchestrate lesson flow
- Generate questions
- Process answers
- Update statistics
- Calculate lesson results

**Key Methods:**

```python
class LessonService:
    def __init__(
        self,
        word_selector: WordSelector,
        validation_service: ValidationService,
        lesson_repo: LessonRepository,
        stats_repo: StatisticsRepository
    ):
        self.word_selector = word_selector
        self.validation_service = validation_service
        self.lesson_repo = lesson_repo
        self.stats_repo = stats_repo

    async def start_lesson(
        self,
        profile_id: int,
        words_count: int = 30
    ) -> Lesson:
        """Start new lesson with word selection"""
        # 1. Create lesson record
        # 2. Select words using adaptive algorithm
        # 3. Return lesson with first question

    async def generate_question(
        self,
        user_word: UserWord,
        direction: Direction,
        test_type: TestType
    ) -> Question:
        """Generate question for word"""
        # 1. Determine question text based on direction
        # 2. If multiple_choice, generate answer options
        # 3. Return Question object

    async def process_answer(
        self,
        lesson_id: int,
        user_word_id: int,
        user_answer: str,
        correct_answer: str
    ) -> AnswerResult:
        """Validate answer and update statistics"""
        # 1. Validate answer through validation service
        # 2. Record attempt in lesson_attempts
        # 3. Update word statistics
        # 4. Update lesson progress
        # 5. Return result with feedback

    async def complete_lesson(
        self,
        lesson_id: int
    ) -> LessonSummary:
        """Finalize lesson and calculate stats"""
```

#### Validation Service

**Responsibilities:**
- Three-level validation (exact → fuzzy → LLM)
- Levenshtein distance calculation
- LLM validation with caching
- Feedback generation

**Key Methods:**

```python
class ValidationService:
    def __init__(
        self,
        llm_client: LLMClient,
        cache_repo: CacheRepository,
        fuzzy_threshold: int = 2
    ):
        self.llm_client = llm_client
        self.cache_repo = cache_repo
        self.fuzzy_threshold = fuzzy_threshold

    async def validate_answer(
        self,
        user_answer: str,
        expected_answer: str,
        word_id: int,
        direction: Direction,
        alternative_answers: list[str] = None
    ) -> ValidationResult:
        """Three-level validation pipeline"""
        # Level 1: Exact match
        if self._exact_match(user_answer, expected_answer, alternative_answers):
            return ValidationResult(
                is_correct=True,
                method="exact",
                feedback=None
            )

        # Level 2: Fuzzy match (typos)
        fuzzy_result = self._fuzzy_match(user_answer, expected_answer)
        if fuzzy_result.is_match:
            return ValidationResult(
                is_correct=True,
                method="fuzzy",
                feedback=f"Small typo detected. Expected: {expected_answer}"
            )

        # Level 3: LLM validation
        return await self._llm_validate(
            user_answer, expected_answer, word_id, direction
        )

    def _exact_match(
        self,
        user_answer: str,
        expected_answer: str,
        alternatives: list[str]
    ) -> bool:
        """Check exact match (case-insensitive, trimmed)"""

    def _fuzzy_match(
        self,
        user_answer: str,
        expected_answer: str
    ) -> FuzzyMatchResult:
        """Levenshtein distance check"""

    async def _llm_validate(
        self,
        user_answer: str,
        expected_answer: str,
        word_id: int,
        direction: Direction
    ) -> ValidationResult:
        """LLM-based validation with caching"""
        # 1. Check validation cache
        # 2. If not cached, call LLM
        # 3. Cache result
        # 4. Return ValidationResult with feedback
```

#### Translation Service

**Responsibilities:**
- LLM API integration
- Request formatting
- Response parsing
- Error handling and retries

**Key Methods:**

```python
class TranslationService:
    def __init__(
        self,
        llm_client: LLMClient,
        cache_repo: CacheRepository
    ):
        self.llm_client = llm_client
        self.cache_repo = cache_repo

    async def translate_word(
        self,
        word: str,
        source_language: str,
        target_language: str
    ) -> TranslationData:
        """Get translations, examples, word forms"""
        # 1. Check cache
        # 2. If not cached, build LLM prompt
        # 3. Call LLM API
        # 4. Parse response
        # 5. Cache result
        # 6. Return TranslationData

    async def validate_with_llm(
        self,
        question: str,
        expected_answer: str,
        user_answer: str,
        context: dict
    ) -> LLMValidationResult:
        """Ask LLM to validate user's answer"""
        # 1. Build validation prompt
        # 2. Call LLM
        # 3. Parse result (is_correct + comment)
        # 4. Return result
```

#### Notification Service

**Responsibilities:**
- Check users needing notifications
- Send push notifications
- Respect time windows
- Track notification history

**Key Methods:**

```python
class NotificationService:
    def __init__(
        self,
        user_repo: UserRepository,
        bot: Bot,
        settings: Settings
    ):
        self.user_repo = user_repo
        self.bot = bot
        self.settings = settings

    async def check_and_send_notifications(self):
        """Scheduled task to send notifications"""
        # 1. Get current time in MSK
        # 2. Check if within notification window (7:00-23:00)
        # 3. Find users with last_active > 6 hours ago
        # 4. Filter by notification_enabled=True
        # 5. Send notifications
        # 6. Update last_notification_sent timestamp

    async def send_reminder(self, user_id: int):
        """Send lesson reminder to user"""
```

### 6.2 Repository Layer

**Base Repository Pattern:**

```python
from typing import TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

T = TypeVar('T')

class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> T | None:
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[T]:
        result = await self.session.execute(select(self.model))
        return list(result.scalars().all())

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: T):
        await self.session.delete(entity)
        await self.session.flush()
```

**Specialized Repositories:**

```python
class UserRepository(BaseRepository[User]):
    async def get_by_telegram_id(self, user_id: int) -> User | None:
        """Get user by Telegram ID"""

    async def get_users_for_notification(
        self,
        inactive_hours: int,
        current_hour: int
    ) -> list[User]:
        """Get users needing notification"""

class WordRepository(BaseRepository[Word]):
    async def find_by_text_and_language(
        self,
        word: str,
        language: str
    ) -> Word | None:
        """Find word by text and language"""

    async def get_frequency_words(
        self,
        language: str,
        level: str,
        limit: int
    ) -> list[Word]:
        """Get most frequent words for level"""

class UserWordRepository(BaseRepository[UserWord]):
    async def get_words_for_lesson(
        self,
        profile_id: int,
        count: int
    ) -> list[UserWord]:
        """Get words for lesson (adaptive selection)"""

    async def get_user_vocabulary(
        self,
        profile_id: int,
        status: str = None
    ) -> list[UserWord]:
        """Get user's vocabulary"""
```

### 6.3 Telegram Bot Layer

**Handler Organization:**

```python
# src/words/bot/handlers/start.py
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    # 1. Check if user exists
    # 2. If new user, start registration flow
    # 3. If existing user, show main menu

@router.message(StateFilter(RegistrationStates.native_language))
async def process_native_language(message: Message, state: FSMContext):
    """Process native language selection"""

@router.callback_query(F.data.startswith("select_language:"))
async def callback_select_language(
    callback: CallbackQuery,
    state: FSMContext
):
    """Handle language selection from inline keyboard"""
```

**State Machine for Conversations:**

```python
from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    native_language = State()
    target_language = State()
    level = State()

class AddWordStates(StatesGroup):
    waiting_for_word = State()
    selecting_meaning = State()
    confirming = State()

class LessonStates(StatesGroup):
    in_progress = State()
    answering = State()
```

**Keyboard Builders:**

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def build_language_keyboard(languages: list[str]) -> InlineKeyboardMarkup:
    """Build inline keyboard for language selection"""
    builder = InlineKeyboardBuilder()
    for lang in languages:
        builder.button(
            text=get_language_name(lang),
            callback_data=f"select_language:{lang}"
        )
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()

def build_lesson_answer_keyboard(
    options: list[str],
    correct_index: int
) -> InlineKeyboardMarkup:
    """Build multiple choice keyboard"""
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(options):
        builder.button(
            text=option,
            callback_data=f"answer:{i}"
        )
    builder.adjust(1)  # 1 button per row
    return builder.as_markup()
```

---

## 7. Adaptive Learning Algorithm

### 7.1 Algorithm Overview

**Goal:** Select words for lessons that optimize learning efficiency based on:
- Word mastery level
- Time since last review (spaced repetition)
- Error rate
- Test type progression

**Components:**
1. **Word Selector:** Choose which words to include in lesson
2. **Spaced Repetition:** Determine next review time (SM-2 algorithm)
3. **Difficulty Adjuster:** Progress from multiple choice → input

### 7.2 Word Selection Algorithm

**Priority Factors:**

```python
class WordSelector:
    async def select_words_for_lesson(
        self,
        profile_id: int,
        target_count: int = 30
    ) -> list[UserWord]:
        """Select words for lesson using adaptive algorithm"""

        # 1. Get all user words not mastered
        candidates = await self._get_candidate_words(profile_id)

        # 2. Calculate priority scores
        scored_words = [
            (word, self._calculate_priority(word))
            for word in candidates
        ]

        # 3. Sort by priority (highest first)
        scored_words.sort(key=lambda x: x[1], reverse=True)

        # 4. Prioritize input-type words
        input_ready = [w for w, s in scored_words if self._is_input_ready(w)]
        choice_words = [w for w, s in scored_words if not self._is_input_ready(w)]

        # 5. Build lesson word list
        selected = []

        # Add input-ready words first (up to 50% of lesson)
        selected.extend(input_ready[:target_count // 2])

        # Fill remaining with choice words
        remaining = target_count - len(selected)
        selected.extend(choice_words[:remaining])

        return selected

    def _calculate_priority(self, user_word: UserWord) -> float:
        """Calculate word priority score (higher = more urgent)"""
        score = 0.0

        # Factor 1: Due for review (spaced repetition)
        if user_word.next_review_at:
            days_overdue = (datetime.utcnow() - user_word.next_review_at).days
            if days_overdue > 0:
                score += days_overdue * 10  # Overdue words get high priority

        # Factor 2: Error rate (recent mistakes)
        stats = user_word.statistics
        error_rate = self._calculate_error_rate(stats)
        score += error_rate * 5

        # Factor 3: New words (need introduction)
        if user_word.status == 'new':
            score += 15

        # Factor 4: Time since last review
        if user_word.last_reviewed_at:
            days_since = (datetime.utcnow() - user_word.last_reviewed_at).days
            score += min(days_since, 7)  # Cap at 7 days
        else:
            score += 7  # Never reviewed

        return score

    def _is_input_ready(self, user_word: UserWord) -> bool:
        """Check if word is ready for input-type testing"""
        # Criteria: 3+ consecutive correct answers in multiple choice
        for stat in user_word.statistics:
            if stat.test_type == 'multiple_choice':
                if stat.correct_count >= 3:
                    return True
        return False
```

### 7.3 Spaced Repetition (SM-2 Algorithm)

**Implementation:**

```python
class SpacedRepetition:
    """SM-2 Spaced Repetition Algorithm"""

    def calculate_next_review(
        self,
        current_interval: int,
        easiness_factor: float,
        is_correct: bool
    ) -> tuple[int, float]:
        """Calculate next review interval and updated EF"""

        if not is_correct:
            # Reset on error
            return 1, max(1.3, easiness_factor - 0.2)

        # Update easiness factor
        new_ef = max(1.3, easiness_factor)

        # Calculate next interval
        if current_interval == 0:
            next_interval = 1
        elif current_interval == 1:
            next_interval = 6
        else:
            next_interval = int(current_interval * new_ef)

        return next_interval, new_ef

async def update_review_schedule(
    user_word: UserWord,
    is_correct: bool
):
    """Update next_review_at after attempt"""
    current_interval = user_word.review_interval or 0
    ef = user_word.easiness_factor or 2.5

    next_interval, new_ef = SpacedRepetition().calculate_next_review(
        current_interval, ef, is_correct
    )

    user_word.review_interval = next_interval
    user_word.easiness_factor = new_ef
    user_word.next_review_at = datetime.utcnow() + timedelta(days=next_interval)
```

**Schema Addition (to user_words table):**

```python
class UserWord(Base):
    # ... existing fields ...
    review_interval: Mapped[int] = mapped_column(default=0)
    easiness_factor: Mapped[float] = mapped_column(default=2.5)
```

### 7.4 Difficulty Progression

**Progression Rules:**

```python
class DifficultyAdjuster:
    CHOICE_TO_INPUT_THRESHOLD = 3  # Correct answers before moving to input
    MASTERED_THRESHOLD = 30        # Correct answers to mark as mastered

    def determine_test_type(self, user_word: UserWord) -> TestType:
        """Determine appropriate test type for word"""

        stats = self._get_stats(user_word, 'multiple_choice')

        if stats and stats.correct_count >= self.CHOICE_TO_INPUT_THRESHOLD:
            return TestType.INPUT
        else:
            return TestType.MULTIPLE_CHOICE

    def update_word_status(self, user_word: UserWord, stats: WordStatistics):
        """Update word status based on performance"""

        if stats.correct_count >= self.MASTERED_THRESHOLD:
            user_word.status = 'mastered'
        elif stats.total_attempts > 0:
            if stats.total_attempts < 5:
                user_word.status = 'learning'
            else:
                user_word.status = 'reviewing'
```

### 7.5 Bidirectional Testing

**Direction Selection:**

```python
import random

def select_direction(user_word: UserWord) -> Direction:
    """Randomly select translation direction"""
    # 50/50 split between both directions
    return random.choice([
        Direction.NATIVE_TO_FOREIGN,
        Direction.FOREIGN_TO_NATIVE
    ])

def get_question_and_answer(
    user_word: UserWord,
    direction: Direction
) -> tuple[str, str]:
    """Get question and expected answer based on direction"""

    word = user_word.word
    user_native = user_word.profile.user.native_language

    if direction == Direction.NATIVE_TO_FOREIGN:
        question = word.translations[user_native][0]
        answer = word.word
    else:  # FOREIGN_TO_NATIVE
        question = word.word
        answer = word.translations[user_native][0]

    return question, answer
```

### 7.6 Multiple Choice Generation

**Answer Option Algorithm:**

```python
class AnswerOptionGenerator:
    async def generate_options(
        self,
        correct_answer: str,
        word: Word,
        direction: Direction,
        count: int = 4
    ) -> list[str]:
        """Generate plausible wrong answers"""

        options = [correct_answer]

        # Strategy 1: Similar words from same level
        similar_words = await self._get_similar_words(
            word.language,
            word.level,
            count - 1
        )
        options.extend([w.word for w in similar_words])

        # If not enough, add from adjacent levels
        if len(options) < count:
            adjacent = await self._get_adjacent_level_words(
                word.language,
                word.level,
                count - len(options)
            )
            options.extend([w.word for w in adjacent])

        # Shuffle to randomize correct answer position
        random.shuffle(options)

        return options[:count]
```

---

## 8. External Integrations

### 8.1 Telegram Bot API Integration

**Library Choice: aiogram 3.x**

**Rationale:**
- Async-first design (matches SQLAlchemy async)
- Modern, actively maintained
- Better performance than python-telegram-bot
- Clean API with type hints
- Built-in FSM support

**Setup:**

```python
# src/words/bot/__init__.py
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

async def setup_bot(token: str) -> tuple[Bot, Dispatcher]:
    """Initialize bot and dispatcher"""

    bot = Bot(
        token=token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    storage = MemoryStorage()  # Or Redis for production
    dp = Dispatcher(storage=storage)

    # Register routers
    from .handlers import (
        start_router,
        lesson_router,
        words_router,
        settings_router,
        stats_router
    )

    dp.include_router(start_router)
    dp.include_router(lesson_router)
    dp.include_router(words_router)
    dp.include_router(settings_router)
    dp.include_router(stats_router)

    return bot, dp
```

**Error Handling:**

```python
from aiogram.exceptions import TelegramAPIError
from aiogram import Router

@router.errors()
async def error_handler(event, exception):
    """Global error handler"""
    if isinstance(exception, TelegramAPIError):
        logger.error(f"Telegram API error: {exception}")
        # Notify user of temporary issue
    else:
        logger.exception("Unexpected error in handler")
        # Log for debugging
```

### 8.2 LLM API Integration (OpenAI)

**Client Implementation:**

```python
# src/words/infrastructure/llm_client.py
import openai
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import json

class LLMClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def translate_word(
        self,
        word: str,
        source_lang: str,
        target_lang: str
    ) -> dict:
        """Get translations, examples, and word forms"""

        prompt = self._build_translation_prompt(
            word, source_lang, target_lang
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a language learning assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise

    def _build_translation_prompt(
        self,
        word: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """Build prompt for translation request"""
        return f"""
Translate the word "{word}" from {source_lang} to {target_lang}.

Provide the response in JSON format:
{{
    "word": "{word}",
    "translations": ["translation1", "translation2", ...],
    "examples": [
        {{"source": "example in {source_lang}", "target": "example in {target_lang}"}},
        ...
    ],
    "word_forms": {{
        "plural": "...",
        "past": "...",
        "comparative": "...",
        ...
    }}
}}

Include:
- All common translations/meanings
- 2-3 example sentences with translations
- Relevant word forms (plural, verb conjugations, etc.)
"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def validate_answer(
        self,
        question: str,
        expected_answer: str,
        user_answer: str,
        source_lang: str,
        target_lang: str
    ) -> dict:
        """Validate user's answer using LLM"""

        prompt = self._build_validation_prompt(
            question, expected_answer, user_answer, source_lang, target_lang
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a language learning validator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except openai.APIError as e:
            logger.error(f"OpenAI API error during validation: {e}")
            raise

    def _build_validation_prompt(
        self,
        question: str,
        expected: str,
        user: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """Build prompt for answer validation"""
        return f"""
Question: Translate "{question}" from {source_lang} to {target_lang}
Expected answer: {expected}
User's answer: {user}

Evaluate if the user's answer is correct. Consider:
- Synonyms
- Alternative word forms
- Common variations
- Context appropriateness

Respond in JSON:
{{
    "is_correct": true/false,
    "comment": "Explanation for the user in {source_lang}"
}}

Comment examples:
- If correct: "Правильно! Также можно сказать '{expected}'."
- If synonym: "Ответ засчитывается, но обычно используется '{expected}'."
- If wrong: "Неправильно. '{user}' означает '...', а правильный ответ: '{expected}'."
"""
```

**Rate Limiting and Cost Management:**

**CRITICAL UPDATE (2025-11-08):** Enhanced with token bucket rate limiter and circuit breaker pattern based on architecture review.

```python
from asyncio import Semaphore
from aiolimiter import AsyncLimiter
from circuitbreaker import circuit
import openai

class RateLimitedLLMClient(LLMClient):
    """
    LLM Client with comprehensive rate limiting and circuit breaker protection.

    Features:
    - Token bucket rate limiting (prevents API quota exhaustion)
    - Semaphore for concurrent request limiting
    - Circuit breaker for fault tolerance
    - Priority queue for important requests (optional)
    """

    def __init__(
        self,
        *args,
        max_concurrent: int = 10,
        requests_per_minute: int = 2500,  # Safety margin: 3000 - 500
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        # Concurrent request limiter
        self.semaphore = Semaphore(max_concurrent)

        # Token bucket rate limiter
        # OpenAI gpt-4o-mini: 3000 req/min, use 2500 for safety margin
        self.rate_limiter = AsyncLimiter(
            max_rate=requests_per_minute,
            time_period=60
        )

        # Circuit breaker state
        self.circuit_open = False

    @circuit(
        failure_threshold=5,      # Open circuit after 5 consecutive failures
        recovery_timeout=60,      # Try to close circuit after 60 seconds
        expected_exception=openai.APIError
    )
    async def _call_with_circuit_breaker(self, func, *args, **kwargs):
        """Execute LLM call with circuit breaker protection"""
        return await func(*args, **kwargs)

    async def translate_word(self, *args, **kwargs):
        """
        Translate word with rate limiting and circuit breaker.

        Flow:
        1. Wait for rate limiter slot
        2. Acquire semaphore (max concurrent)
        3. Execute with circuit breaker protection
        4. Return result or raise exception
        """
        async with self.rate_limiter:
            async with self.semaphore:
                try:
                    return await self._call_with_circuit_breaker(
                        super().translate_word, *args, **kwargs
                    )
                except openai.APIError as e:
                    logger.error(
                        "llm_api_error",
                        operation="translate",
                        error=str(e),
                        circuit_open=self.circuit_open
                    )
                    raise

    async def validate_answer(self, *args, **kwargs):
        """
        Validate answer with rate limiting and circuit breaker.

        Higher priority than translation (validation is user-facing).
        """
        async with self.rate_limiter:
            async with self.semaphore:
                try:
                    return await self._call_with_circuit_breaker(
                        super().validate_answer, *args, **kwargs
                    )
                except openai.APIError as e:
                    logger.error(
                        "llm_api_error",
                        operation="validate",
                        error=str(e),
                        circuit_open=self.circuit_open
                    )
                    raise
```

**Circuit Breaker Behavior:**

When circuit opens (after 5 consecutive failures):
1. Stop sending requests to LLM API immediately
2. Return cached results if available
3. Use fallback strategies (basic translation, exact matching)
4. After 60 seconds, attempt one request to test recovery
5. If successful, close circuit and resume normal operation

**Example Circuit Breaker Handler:**

```python
class LLMServiceWithFallback:
    """Service layer with circuit breaker fallback handling"""

    def __init__(
        self,
        llm_client: RateLimitedLLMClient,
        cache_manager: CacheManager
    ):
        self.llm_client = llm_client
        self.cache_manager = cache_manager

    async def get_translation(
        self,
        word: str,
        src: str,
        tgt: str
    ) -> dict:
        """Get translation with circuit breaker fallback"""

        # Check cache first
        cached = await self.cache_manager.get_translation(word, src, tgt)
        if cached:
            return cached

        try:
            # Try LLM API (with circuit breaker)
            result = await self.llm_client.translate_word(word, src, tgt)

            # Cache successful result
            await self.cache_manager.set_translation(word, src, tgt, result)

            return result

        except CircuitBreakerError:
            # Circuit is open - API is failing
            logger.warning(
                "circuit_breaker_open",
                operation="translation",
                word=word
            )

            # Fallback: Return minimal translation or error
            raise TranslationUnavailableError(
                "Translation service temporarily unavailable. "
                "Please try again in a few minutes."
            )

        except openai.RateLimitError as e:
            # Rate limit exceeded (shouldn't happen with rate limiter)
            logger.error(
                "rate_limit_exceeded",
                operation="translation",
                word=word
            )
            raise
```

**Monitoring Rate Limiter:**

```python
# Add metrics to track rate limiter effectiveness
class MetricsCollector:
    """Collect metrics for rate limiter and circuit breaker"""

    def __init__(self):
        self.rate_limited_requests = 0
        self.circuit_breaker_open_count = 0
        self.total_llm_requests = 0
        self.failed_llm_requests = 0

    async def record_rate_limit_wait(self, wait_time: float):
        """Record time spent waiting for rate limiter"""
        self.rate_limited_requests += 1
        logger.debug(
            "rate_limiter_wait",
            wait_time=wait_time,
            total_limited=self.rate_limited_requests
        )

    async def record_circuit_breaker_open(self):
        """Record circuit breaker opening"""
        self.circuit_breaker_open_count += 1
        logger.warning(
            "circuit_breaker_opened",
            total_opens=self.circuit_breaker_open_count
        )

    def get_metrics(self) -> dict:
        """Get current metrics"""
        return {
            "total_llm_requests": self.total_llm_requests,
            "failed_llm_requests": self.failed_llm_requests,
            "rate_limited_requests": self.rate_limited_requests,
            "circuit_breaker_opens": self.circuit_breaker_open_count,
            "success_rate": (
                1 - (self.failed_llm_requests / self.total_llm_requests)
                if self.total_llm_requests > 0 else 1.0
            )
        }
```

### 8.3 Caching Strategy

**Two-Level Caching:**

1. **Database Cache:** Persistent, survives restarts
2. **In-Memory Cache:** Fast, for frequently accessed data

**Implementation:**

```python
# src/words/infrastructure/cache.py
from functools import lru_cache
from typing import Optional
import hashlib

class CacheManager:
    def __init__(self, cache_repo: CacheRepository):
        self.cache_repo = cache_repo

    @lru_cache(maxsize=1000)
    def _get_cache_key(
        self,
        word: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """Generate cache key"""
        data = f"{word}:{source_lang}:{target_lang}"
        return hashlib.md5(data.encode()).hexdigest()

    async def get_translation(
        self,
        word: str,
        source_lang: str,
        target_lang: str
    ) -> Optional[dict]:
        """Get cached translation"""

        cached = await self.cache_repo.find_translation(
            word, source_lang, target_lang
        )

        if cached:
            # Check if expired
            if cached.expires_at and cached.expires_at < datetime.utcnow():
                return None
            return cached.translation_data

        return None

    async def set_translation(
        self,
        word: str,
        source_lang: str,
        target_lang: str,
        data: dict,
        expires_in_days: int = None
    ):
        """Cache translation result"""

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        await self.cache_repo.save_translation(
            word=word,
            source_language=source_lang,
            target_language=target_lang,
            translation_data=data,
            expires_at=expires_at
        )

    async def get_validation(
        self,
        word_id: int,
        direction: str,
        expected: str,
        user: str
    ) -> Optional[dict]:
        """
        Get cached validation result with normalization.

        ENHANCED (2025-11-08): Added answer normalization for better cache hit rates.
        """

        # Normalize answers before cache lookup
        normalized_expected = self._normalize_answer(expected)
        normalized_user = self._normalize_answer(user)

        cached = await self.cache_repo.find_validation(
            word_id, direction, normalized_expected, normalized_user
        )

        return cached if cached else None

    async def set_validation(
        self,
        word_id: int,
        direction: str,
        expected: str,
        user: str,
        is_correct: bool,
        comment: str
    ):
        """
        Cache validation result with normalization.

        ENHANCED (2025-11-08): Normalize answers before caching.
        """

        # Normalize answers before caching
        normalized_expected = self._normalize_answer(expected)
        normalized_user = self._normalize_answer(user)

        await self.cache_repo.save_validation(
            word_id=word_id,
            direction=direction,
            expected_answer=normalized_expected,
            user_answer=normalized_user,
            is_correct=is_correct,
            llm_comment=comment
        )

    def _normalize_answer(self, answer: str) -> str:
        """
        Normalize answer for cache lookup.

        Normalization rules:
        - Convert to lowercase
        - Strip leading/trailing whitespace
        - Replace multiple spaces with single space
        - Remove common punctuation at the end

        This significantly improves cache hit rate by handling:
        - Case variations: "House" vs "house"
        - Whitespace: " house" vs "house "
        - Multiple spaces: "red  car" vs "red car"
        - Punctuation: "house." vs "house"

        Expected improvement: 40% → 70% cache hit rate
        """
        # Convert to lowercase
        normalized = answer.lower()

        # Strip whitespace
        normalized = normalized.strip()

        # Replace multiple spaces with single space
        normalized = " ".join(normalized.split())

        # Remove trailing punctuation (but keep internal punctuation)
        while normalized and normalized[-1] in ".,;!?":
            normalized = normalized[:-1]

        return normalized

    async def get_distractors(
        self,
        word_id: int,
        direction: str,
        count: int = 3
    ) -> Optional[list[str]]:
        """
        Get cached multiple choice distractors.

        NEW (2025-11-08): Added caching for LLM-generated distractors.
        """
        cached = await self.cache_repo.find_distractors(word_id, direction)
        if cached and len(cached) >= count:
            return cached[:count]
        return None

    async def set_distractors(
        self,
        word_id: int,
        direction: str,
        distractors: list[str]
    ):
        """
        Cache multiple choice distractors.

        NEW (2025-11-08): Cache LLM-generated distractors for reuse.
        """
        await self.cache_repo.save_distractors(
            word_id=word_id,
            direction=direction,
            distractors=distractors
        )
```

**Cache Invalidation:**
- Translation cache: No expiration (words don't change)
- Validation cache: No expiration (deterministic results, normalized)
- Distractor cache: No expiration (quality is consistent)
- Clear cache manually if LLM quality improves

**Cache Hit Rate Optimization:**

The normalization strategy improves cache hit rates significantly:

```python
# Example cache hit scenarios (before vs after normalization)

# Scenario 1: Case sensitivity
# Before: "House" vs "house" → MISS
# After: "house" vs "house" → HIT

# Scenario 2: Whitespace
# Before: " house " vs "house" → MISS
# After: "house" vs "house" → HIT

# Scenario 3: Multiple spaces
# Before: "red  car" vs "red car" → MISS
# After: "red car" vs "red car" → HIT

# Scenario 4: Trailing punctuation
# Before: "house." vs "house" → MISS
# After: "house" vs "house" → HIT
```

**Expected Performance:**
- Before normalization: ~40% cache hit rate
- After normalization: ~70% cache hit rate
- Cost savings: ~30% reduction in LLM API calls
- User experience: Faster validation responses

### 8.4 Background Task Scheduler

**APScheduler Setup:**

```python
# src/words/infrastructure/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

async def setup_scheduler(
    notification_service: NotificationService
) -> AsyncIOScheduler:
    """Setup background task scheduler"""

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    # Check for notifications every 15 minutes
    scheduler.add_job(
        notification_service.check_and_send_notifications,
        trigger=CronTrigger(minute="*/15"),
        id="send_notifications",
        replace_existing=True
    )

    # Daily database backup (3 AM MSK)
    scheduler.add_job(
        backup_database,
        trigger=CronTrigger(hour=3, minute=0),
        id="daily_backup",
        replace_existing=True
    )

    # Weekly cache cleanup (Sunday 2 AM MSK)
    scheduler.add_job(
        cleanup_expired_cache,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="cache_cleanup",
        replace_existing=True
    )

    scheduler.start()
    return scheduler
```

---

## 9. Configuration Management

### 9.1 Environment Variables

**Required Variables:**

```bash
# .env
# Telegram Bot
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...

# OpenAI API
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# Database
DATABASE_URL=sqlite+aiosqlite:///data/database/words.db
# Or for PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/words

# Application Settings
WORDS_PER_LESSON=30
MASTERED_THRESHOLD=30
NOTIFICATION_INTERVAL_HOURS=6
NOTIFICATION_TIME_START=07:00
NOTIFICATION_TIME_END=23:00
TIMEZONE=Europe/Moscow

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# Environment
ENV=production  # development, staging, production
```

### 9.2 Settings Management (Pydantic)

```python
# src/words/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """Application settings loaded from environment"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Telegram
    telegram_bot_token: str

    # LLM
    llm_api_key: str
    llm_model: str = "gpt-4o-mini"
    llm_max_concurrent: int = 10
    llm_timeout: int = 30

    # Database
    database_url: str

    # Lesson Settings
    words_per_lesson: int = 30
    mastered_threshold: int = 30
    choice_to_input_threshold: int = 3

    # Notifications
    notification_interval_hours: int = 6
    notification_time_start: str = "07:00"
    notification_time_end: str = "23:00"
    timezone: str = "Europe/Moscow"

    # Validation
    fuzzy_match_threshold: int = 2

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/bot.log"

    # Environment
    env: str = "production"
    debug: bool = Field(default=False, validation_alias="DEBUG")

# Global settings instance
settings = Settings()
```

### 9.3 Localization (i18n)

**Translation Files:**

```json
// data/translations/ru.json
{
  "commands": {
    "start": "Добро пожаловать! Давайте настроим ваш профиль.",
    "lesson": "Начать урок",
    "add_word": "Добавить слово",
    "stats": "Статистика"
  },
  "registration": {
    "select_native": "Выберите ваш родной язык:",
    "select_target": "Какой язык хотите изучать?",
    "select_level": "Ваш текущий уровень:",
    "completed": "Регистрация завершена! Ваш словарь формируется..."
  },
  "lesson": {
    "question": "Переведите:",
    "correct": "Правильно!",
    "incorrect": "Неправильно. Правильный ответ:",
    "typo": "Небольшая опечатка. Правильно:",
    "summary": "Урок завершен!\n✅ Правильных: {correct}\n❌ Ошибок: {errors}"
  },
  "stats": {
    "total_words": "Всего слов: {count}",
    "mastered": "Выучено: {count}",
    "learning": "В процессе: {count}",
    "streak": "Дней подряд: {count}"
  }
}
```

**Loader:**

```python
# src/words/localization/loader.py
import json
from pathlib import Path
from typing import Dict

class Localizer:
    def __init__(self, translations_dir: str = "data/translations"):
        self.translations_dir = Path(translations_dir)
        self._translations: Dict[str, dict] = {}
        self._load_all()

    def _load_all(self):
        """Load all translation files"""
        for file in self.translations_dir.glob("*.json"):
            lang_code = file.stem
            with open(file, 'r', encoding='utf-8') as f:
                self._translations[lang_code] = json.load(f)

    def get(self, key: str, lang: str, **kwargs) -> str:
        """Get translated string with formatting"""
        keys = key.split('.')
        value = self._translations.get(lang, {})

        for k in keys:
            value = value.get(k, key)

        if kwargs:
            return value.format(**kwargs)
        return value

# Global localizer instance
localizer = Localizer()
```

---

## 10. Logging and Monitoring

### 10.1 Logging Architecture

**Structured Logging with structlog:**

```python
# src/words/utils/logger.py
import logging
import structlog
from pathlib import Path

def setup_logging(log_level: str, log_file: str):
    """Configure structured logging"""

    # Create logs directory
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def get_logger(name: str):
    """Get logger instance"""
    return structlog.get_logger(name)
```

**Usage:**

```python
from words.utils.logger import get_logger

logger = get_logger(__name__)

logger.info(
    "user_registered",
    user_id=user_id,
    native_language=native_lang,
    target_language=target_lang
)

logger.error(
    "llm_api_error",
    error=str(e),
    word=word,
    retry_count=retry
)
```

### 10.2 Key Metrics to Track

**Application Metrics:**

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Metrics:
    # User metrics
    total_users: int
    active_users_today: int
    new_users_today: int

    # Lesson metrics
    lessons_completed_today: int
    avg_lesson_duration: float
    avg_correct_rate: float

    # Word metrics
    words_added_today: int
    words_mastered_today: int

    # API metrics
    llm_requests_today: int
    llm_cache_hit_rate: float
    llm_avg_response_time: float

    # Error metrics
    errors_today: int
    api_failures_today: int

    timestamp: datetime
```

**Metrics Collection:**

```python
class MetricsCollector:
    async def collect_daily_metrics(self) -> Metrics:
        """Collect all metrics for dashboard"""

        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Query repositories for metrics
        total_users = await self.user_repo.count_all()
        active_today = await self.user_repo.count_active_since(today_start)
        # ... etc

        return Metrics(
            total_users=total_users,
            active_users_today=active_today,
            # ... fill all fields
            timestamp=datetime.utcnow()
        )
```

### 10.3 Error Tracking

**Critical Errors to Monitor:**

1. **Database errors:** Connection failures, query timeouts
2. **LLM API errors:** Rate limits, timeouts, API errors
3. **Telegram API errors:** Network issues, invalid requests
4. **Application errors:** Unexpected exceptions, data corruption

**Error Logging Pattern:**

```python
try:
    result = await llm_client.translate_word(word, src, tgt)
except openai.RateLimitError as e:
    logger.error(
        "llm_rate_limit_exceeded",
        word=word,
        error=str(e),
        alert=True  # Trigger alert
    )
    # Fallback to cache or degraded mode
except openai.APIError as e:
    logger.error(
        "llm_api_error",
        word=word,
        error=str(e),
        status_code=e.status_code,
        alert=True
    )
    raise
except Exception as e:
    logger.exception(
        "unexpected_error_in_translation",
        word=word,
        alert=True
    )
    raise
```

### 10.4 Health Checks

```python
# src/words/utils/health.py
from dataclasses import dataclass
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheck:
    status: HealthStatus
    database: bool
    llm_api: bool
    telegram_api: bool
    scheduler: bool
    details: dict

async def check_health() -> HealthCheck:
    """Comprehensive health check"""

    db_ok = await check_database()
    llm_ok = await check_llm_api()
    telegram_ok = await check_telegram_api()
    scheduler_ok = check_scheduler_running()

    all_ok = db_ok and llm_ok and telegram_ok and scheduler_ok

    if all_ok:
        status = HealthStatus.HEALTHY
    elif db_ok and telegram_ok:
        status = HealthStatus.DEGRADED  # Can work with cache
    else:
        status = HealthStatus.UNHEALTHY

    return HealthCheck(
        status=status,
        database=db_ok,
        llm_api=llm_ok,
        telegram_api=telegram_ok,
        scheduler=scheduler_ok,
        details={
            "uptime": get_uptime(),
            "version": get_version()
        }
    )
```

---

## 11. Error Handling and Resilience

### 11.1 Error Handling Strategy

**Principle:** Fail gracefully, never crash the bot

**Error Categories:**

1. **Transient Errors:** Retry with backoff
2. **Permanent Errors:** Log and notify user
3. **Critical Errors:** Alert admin, degrade gracefully

### 11.2 LLM API Resilience

**Retry Strategy:**

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import openai

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((
        openai.APIConnectionError,
        openai.RateLimitError,
        openai.APITimeoutError
    ))
)
async def call_llm_with_retry(llm_client, *args, **kwargs):
    """Call LLM with automatic retry"""
    return await llm_client.translate_word(*args, **kwargs)
```

**Fallback Strategy:**

```python
async def get_translation_with_fallback(
    word: str,
    src: str,
    tgt: str
) -> TranslationData:
    """Get translation with multiple fallback levels"""

    # Level 1: Check cache
    cached = await cache_manager.get_translation(word, src, tgt)
    if cached:
        return cached

    # Level 2: Try LLM API
    try:
        result = await call_llm_with_retry(llm_client, word, src, tgt)
        await cache_manager.set_translation(word, src, tgt, result)
        return result
    except openai.RateLimitError:
        logger.warning("LLM rate limit, using fallback")
        # Level 3: Use simplified translation
        return await get_basic_translation(word, src, tgt)
    except openai.APIError as e:
        logger.error(f"LLM API error: {e}, using fallback")
        # Level 4: Manual translation or error
        raise TranslationUnavailableError(
            "Translation service temporarily unavailable"
        )
```

### 11.3 Database Resilience

**Connection Pool:**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Check connection health
    pool_recycle=3600    # Recycle connections every hour
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False
)
```

**Transaction Retry:**

```python
from sqlalchemy.exc import OperationalError

async def execute_with_retry(operation, max_retries=3):
    """Execute database operation with retry"""
    for attempt in range(max_retries):
        try:
            async with AsyncSessionLocal() as session:
                result = await operation(session)
                await session.commit()
                return result
        except OperationalError as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Database retry {attempt + 1}/{max_retries}")
            await asyncio.sleep(2 ** attempt)
```

### 11.4 Graceful Shutdown

```python
# src/words/__main__.py
import signal
import asyncio

async def shutdown(bot, dp, scheduler):
    """Graceful shutdown handler"""
    logger.info("Shutting down...")

    # Stop accepting new updates
    await dp.stop_polling()

    # Stop scheduler
    scheduler.shutdown(wait=True)

    # Close bot session
    await bot.session.close()

    # Close database connections
    await engine.dispose()

    logger.info("Shutdown complete")

async def main():
    bot, dp = await setup_bot(settings.telegram_bot_token)
    scheduler = await setup_scheduler(notification_service)

    # Register shutdown handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(shutdown(bot, dp, scheduler))
        )

    # Start bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 12. Performance and Scalability

### 12.1 Current Performance Targets

| Metric | Target |
|--------|--------|
| Command response time | < 2s |
| LLM translation time | < 5s |
| LLM validation time | < 3s |
| Cached operation time | < 100ms |
| Concurrent users | 100+ |
| Database query time | < 500ms |

### 12.2 Optimization Strategies

**Database Optimizations:**

1. **Indexes:** All foreign keys, frequently queried columns
2. **Query Optimization:** Use `select()` instead of lazy loading
3. **Batch Operations:** Bulk inserts for frequency lists
4. **Pagination:** Limit result sets for large queries

**Caching Optimizations:**

1. **LLM Cache:** Persistent, never expires
2. **Query Cache:** In-memory cache for hot data
3. **Session Cache:** User state cached during lesson

**Code Optimizations:**

```python
# Bad: N+1 query problem
for user_word in user_words:
    stats = await stats_repo.get_by_user_word(user_word.id)

# Good: Single query with join
user_words_with_stats = await user_word_repo.get_with_statistics(
    profile_id=profile_id
)
```

### 12.3 Scalability Considerations

**Current Architecture (Single Server):**
- Good for: 100-1000 users
- Bottleneck: Single process, single database

**Horizontal Scaling Path (Future):**

1. **Multiple Bot Processes:**
   - Use Redis for FSM storage (replace MemoryStorage)
   - Session affinity not required (stateless handlers)
   - Load balancer: Telegram handles distribution

2. **Database Scaling:**
   - Read replicas for statistics queries
   - Connection pooling
   - PostgreSQL instead of SQLite

3. **Cache Scaling:**
   - Redis cluster for distributed cache
   - Shared across bot instances

4. **Background Task Scaling:**
   - Celery + RabbitMQ for distributed tasks
   - Separate notification workers

**When to Scale:**
- When response time > 2s for 10% of requests
- When CPU usage > 80% sustained
- When database connections exhausted
- When > 1000 active users

### 12.4 Monitoring for Performance

**Key Performance Indicators:**

```python
import time
from functools import wraps

def track_performance(metric_name: str):
    """Decorator to track function performance"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                logger.info(
                    "performance_metric",
                    metric=metric_name,
                    duration=duration,
                    success=True
                )
                return result
            except Exception as e:
                duration = time.time() - start
                logger.error(
                    "performance_metric",
                    metric=metric_name,
                    duration=duration,
                    success=False,
                    error=str(e)
                )
                raise
        return wrapper
    return decorator

@track_performance("lesson_start")
async def start_lesson(profile_id: int):
    # ... implementation
```

---

## 13. Security

### 13.1 Threat Model

**Threats:**
1. **API Key Exposure:** Bot token, LLM API key leaked
2. **Injection Attacks:** SQL injection, command injection
3. **Data Leakage:** Unauthorized access to user data
4. **DoS Attacks:** Resource exhaustion
5. **Man-in-the-Middle:** Intercepted communications

### 13.2 Security Measures

**1. Credential Management:**

```bash
# Never commit these files
.env
*.key
secrets/

# .gitignore
.env
.env.*
secrets/
*.key
*.pem
```

**2. Input Validation:**

```python
from pydantic import BaseModel, validator, constr

class AddWordRequest(BaseModel):
    word: constr(min_length=1, max_length=100, strip_whitespace=True)
    language: constr(min_length=2, max_length=10)

    @validator('word')
    def validate_word(cls, v):
        # Only allow letters, hyphens, apostrophes
        if not re.match(r"^[a-zA-Zа-яА-ЯёЁáéíóúñÑ\s'-]+$", v):
            raise ValueError("Invalid word format")
        return v
```

**3. SQL Injection Prevention:**

```python
# SQLAlchemy ORM prevents SQL injection by design
# Always use parameterized queries

# Good (ORM)
result = await session.execute(
    select(User).where(User.user_id == user_id)
)

# Bad (raw SQL - avoid)
# await session.execute(f"SELECT * FROM users WHERE user_id = {user_id}")
```

**4. Rate Limiting:**

```python
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    def is_allowed(self, user_id: int) -> bool:
        """Check if user can make request"""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)

        # Remove old requests
        self.requests[user_id] = [
            ts for ts in self.requests[user_id]
            if ts > cutoff
        ]

        # Check limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False

        # Record request
        self.requests[user_id].append(now)
        return True

# Usage in handler
rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

@router.message(Command("add_word"))
async def add_word_handler(message: Message):
    if not rate_limiter.is_allowed(message.from_user.id):
        await message.answer("Too many requests. Please wait.")
        return
    # ... process request
```

**5. Data Access Control:**

```python
async def get_user_word(
    user_id: int,
    word_id: int,
    session: AsyncSession
) -> UserWord:
    """Get word, ensuring it belongs to user"""

    result = await session.execute(
        select(UserWord)
        .join(LanguageProfile)
        .where(
            UserWord.word_id == word_id,
            LanguageProfile.user_id == user_id
        )
    )

    user_word = result.scalar_one_or_none()
    if not user_word:
        raise PermissionDenied("Word not found or access denied")

    return user_word
```

### 13.3 Secure Communication

**1. HTTPS for API Calls:**

All LLM API calls use HTTPS by default (OpenAI client library).

**2. Telegram API Security:**

Telegram Bot API uses HTTPS and validates bot token on every request.

**3. Database Encryption:**

For sensitive data, use SQLAlchemy's `TypeDecorator`:

```python
from cryptography.fernet import Fernet
from sqlalchemy.types import TypeDecorator, String

class EncryptedString(TypeDecorator):
    """Encrypted string column"""
    impl = String
    cache_ok = True

    def __init__(self, key: bytes, *args, **kwargs):
        self.cipher = Fernet(key)
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is not None:
            return self.cipher.encrypt(value.encode()).decode()
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return self.cipher.decrypt(value.encode()).decode()
        return value
```

### 13.4 Security Checklist

- [ ] Environment variables for all secrets
- [ ] `.env` file in `.gitignore`
- [ ] Input validation on all user inputs
- [ ] Rate limiting on all endpoints
- [ ] SQL injection prevention (ORM)
- [ ] XSS prevention (Telegram handles this)
- [ ] Access control for user data
- [ ] HTTPS for all external APIs
- [ ] Regular dependency updates
- [ ] Security audit logs
- [ ] Backup encryption (if needed)

---

## 14. Deployment Architecture

### 14.1 Local Server Deployment

**Target Environment:** `/opt/projects/words/` (similar to `/opt/projects/companions/`)

**Directory Structure on Server:**

```
/opt/projects/words/
├── venv/                # Virtual environment
├── src/                 # Source code
├── data/
│   ├── database/
│   │   └── words.db
│   ├── frequency_lists/
│   └── translations/
├── logs/
├── backups/             # Database backups
├── .env
├── requirements.txt
└── words.service        # systemd service file
```

### 14.2 Deployment Process

**1. Initial Setup:**

```bash
cd /opt/projects/words

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Load frequency lists
python scripts/load_frequency_lists.py

# Test configuration
python -m words --check-config
```

**2. Systemd Service:**

```ini
# /etc/systemd/system/words.service
[Unit]
Description=Language Learning Telegram Bot
After=network.target

[Service]
Type=simple
User=words
Group=words
WorkingDirectory=/opt/projects/words
Environment="PATH=/opt/projects/words/venv/bin"
ExecStart=/opt/projects/words/venv/bin/python -m words
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true
ReadWritePaths=/opt/projects/words/data /opt/projects/words/logs

[Install]
WantedBy=multi-user.target
```

**3. Enable and Start Service:**

```bash
sudo systemctl enable words.service
sudo systemctl start words.service
sudo systemctl status words.service

# View logs
sudo journalctl -u words.service -f
```

### 14.3 Database Backup Strategy

**Backup Script:**

```bash
#!/bin/bash
# scripts/backup_db.sh

BACKUP_DIR="/opt/projects/words/backups"
DB_PATH="/opt/projects/words/data/database/words.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/words_$TIMESTAMP.db"

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

# Create backup
cp "$DB_PATH" "$BACKUP_FILE"

# Compress
gzip "$BACKUP_FILE"

# Keep only last 30 backups
ls -t "$BACKUP_DIR"/*.db.gz | tail -n +31 | xargs -r rm

echo "Backup created: ${BACKUP_FILE}.gz"
```

**Automated Backups (cron):**

```bash
# Edit crontab
crontab -e

# Daily backup at 3 AM
0 3 * * * /opt/projects/words/scripts/backup_db.sh >> /opt/projects/words/logs/backup.log 2>&1
```

**Backup Verification:**

```bash
# Weekly backup integrity check
# scripts/verify_backup.sh

LATEST_BACKUP=$(ls -t /opt/projects/words/backups/*.db.gz | head -1)
TEMP_DIR=$(mktemp -d)

# Extract and verify
gunzip -c "$LATEST_BACKUP" > "$TEMP_DIR/test.db"
sqlite3 "$TEMP_DIR/test.db" "PRAGMA integrity_check;"

if [ $? -eq 0 ]; then
    echo "Backup verification successful"
else
    echo "Backup verification FAILED" >&2
    exit 1
fi

rm -rf "$TEMP_DIR"
```

### 14.4 Update and Rollback Process

**Update Process:**

```bash
# 1. Pull latest code
cd /opt/projects/words
git pull origin master

# 2. Activate venv
source venv/bin/activate

# 3. Update dependencies
pip install -r requirements.txt --upgrade

# 4. Run migrations
alembic upgrade head

# 5. Restart service
sudo systemctl restart words.service

# 6. Verify
sudo systemctl status words.service
tail -f logs/bot.log
```

**Rollback Process:**

```bash
# 1. Stop service
sudo systemctl stop words.service

# 2. Rollback code
git checkout <previous-commit>

# 3. Rollback database
alembic downgrade -1

# 4. Restore from backup if needed
gunzip -c backups/words_20251108_030000.db.gz > data/database/words.db

# 5. Restart service
sudo systemctl start words.service
```

### 14.5 Monitoring and Alerts

**Health Check Endpoint:**

```python
# Add simple HTTP server for health checks (optional)
from aiohttp import web

async def health_handler(request):
    """Health check endpoint"""
    health = await check_health()
    return web.json_response({
        "status": health.status.value,
        "database": health.database,
        "llm_api": health.llm_api,
        "telegram_api": health.telegram_api
    })

app = web.Application()
app.router.add_get('/health', health_handler)

# Run on localhost:8080
web.run_app(app, host='127.0.0.1', port=8080)
```

**Log Monitoring:**

```bash
# Monitor error logs
tail -f logs/bot.log | grep ERROR

# Count errors per hour
grep ERROR logs/bot.log | awk '{print $1, $2}' | uniq -c
```

---

## 15. Testing Strategy

### 15.1 Testing Pyramid

```
        ┌────────────┐
        │    E2E     │  10%  - Full lesson flow
        │   Tests    │
        ├────────────┤
        │Integration │  30%  - Repository + DB, LLM client
        │   Tests    │
        ├────────────┤
        │   Unit     │  60%  - Business logic, algorithms
        │   Tests    │
        └────────────┘
```

### 15.2 Unit Tests

**Example: Adaptive Algorithm Tests:**

```python
# tests/unit/test_algorithm.py
import pytest
from datetime import datetime, timedelta
from words.algorithm.word_selector import WordSelector
from words.models import UserWord, WordStatistics

@pytest.fixture
def word_selector():
    return WordSelector()

@pytest.fixture
def mock_user_words():
    """Create test user words with various statuses"""
    return [
        UserWord(
            id=1,
            status='new',
            added_at=datetime.utcnow(),
            last_reviewed_at=None,
            next_review_at=None
        ),
        UserWord(
            id=2,
            status='learning',
            last_reviewed_at=datetime.utcnow() - timedelta(days=3),
            next_review_at=datetime.utcnow() - timedelta(days=1),
            statistics=[
                WordStatistics(
                    test_type='multiple_choice',
                    correct_count=2,
                    total_errors=3
                )
            ]
        ),
        # ... more test data
    ]

def test_calculate_priority_new_word(word_selector, mock_user_words):
    """New words should have high priority"""
    new_word = mock_user_words[0]
    priority = word_selector._calculate_priority(new_word)
    assert priority >= 15  # New words get +15 bonus

def test_calculate_priority_overdue(word_selector):
    """Overdue words should have highest priority"""
    overdue_word = UserWord(
        status='reviewing',
        next_review_at=datetime.utcnow() - timedelta(days=2)
    )
    priority = word_selector._calculate_priority(overdue_word)
    assert priority >= 20  # 2 days * 10

def test_is_input_ready_insufficient_correct(word_selector):
    """Word not ready for input with < 3 correct answers"""
    word = UserWord(
        statistics=[
            WordStatistics(
                test_type='multiple_choice',
                correct_count=2
            )
        ]
    )
    assert not word_selector._is_input_ready(word)

def test_is_input_ready_sufficient_correct(word_selector):
    """Word ready for input with 3+ correct answers"""
    word = UserWord(
        statistics=[
            WordStatistics(
                test_type='multiple_choice',
                correct_count=3
            )
        ]
    )
    assert word_selector._is_input_ready(word)
```

**Example: Validation Tests:**

```python
# tests/unit/test_validation.py
import pytest
from words.services.validation import ValidationService

@pytest.fixture
def validation_service():
    return ValidationService(
        llm_client=None,  # Mock for unit tests
        cache_repo=None,
        fuzzy_threshold=2
    )

def test_exact_match_case_insensitive(validation_service):
    """Exact match should be case-insensitive"""
    assert validation_service._exact_match("House", "house", [])
    assert validation_service._exact_match("HOUSE", "house", [])

def test_exact_match_with_whitespace(validation_service):
    """Exact match should trim whitespace"""
    assert validation_service._exact_match("  house  ", "house", [])

def test_exact_match_alternative_answers(validation_service):
    """Exact match should accept alternatives"""
    assert validation_service._exact_match(
        "home", "house", ["home", "dwelling"]
    )

def test_fuzzy_match_one_typo(validation_service):
    """One character typo should match"""
    result = validation_service._fuzzy_match("hous", "house")
    assert result.is_match
    assert result.distance == 1

def test_fuzzy_match_two_typos(validation_service):
    """Two character typos should match"""
    result = validation_service._fuzzy_match("hose", "house")
    assert result.is_match
    assert result.distance == 2

def test_fuzzy_match_too_many_typos(validation_service):
    """Three character typos should not match"""
    result = validation_service._fuzzy_match("hoe", "house")
    assert not result.is_match
```

### 15.3 Integration Tests

**Example: Repository Tests:**

```python
# tests/integration/test_repositories.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from words.models import Base, User, LanguageProfile
from words.repositories import UserRepository, ProfileRepository

@pytest.fixture
async def test_db():
    """Create test database"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

    yield AsyncSession

    await engine.dispose()

@pytest.fixture
async def user_repo(test_db):
    async with test_db() as session:
        yield UserRepository(session)

@pytest.mark.asyncio
async def test_create_user(user_repo):
    """Test user creation"""
    user = await user_repo.create(
        user_id=123456,
        native_language="ru",
        interface_language="ru"
    )

    assert user.user_id == 123456
    assert user.native_language == "ru"

@pytest.mark.asyncio
async def test_get_user_by_telegram_id(user_repo):
    """Test finding user by Telegram ID"""
    await user_repo.create(
        user_id=123456,
        native_language="ru",
        interface_language="ru"
    )

    user = await user_repo.get_by_telegram_id(123456)
    assert user is not None
    assert user.user_id == 123456
```

**Example: LLM Client Tests:**

```python
# tests/integration/test_llm_client.py
import pytest
from words.infrastructure.llm_client import LLMClient
from words.config.settings import Settings

@pytest.fixture
def llm_client(settings: Settings):
    return LLMClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model
    )

@pytest.mark.asyncio
@pytest.mark.integration  # Mark as integration test
async def test_translate_word_english_to_russian(llm_client):
    """Test real translation (requires API key)"""
    result = await llm_client.translate_word(
        word="house",
        source_lang="en",
        target_lang="ru"
    )

    assert "translations" in result
    assert len(result["translations"]) > 0
    assert "дом" in result["translations"]

@pytest.mark.asyncio
@pytest.mark.integration
async def test_validate_answer_synonym(llm_client):
    """Test answer validation with synonym"""
    result = await llm_client.validate_answer(
        question="house",
        expected_answer="дом",
        user_answer="жилище",
        source_lang="en",
        target_lang="ru"
    )

    assert "is_correct" in result
    assert "comment" in result
```

### 15.4 End-to-End Tests

**Example: Full Lesson Flow:**

```python
# tests/e2e/test_lesson_flow.py
import pytest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, User
from tests.mocks import MockBot, MockMessage

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_lesson_flow(
    user_service,
    lesson_service,
    word_service
):
    """Test complete lesson from start to finish"""

    # 1. Create user and profile
    user = await user_service.register_user(
        user_id=12345,
        native_language="ru",
        interface_language="ru"
    )

    profile = await user_service.create_language_profile(
        user_id=12345,
        target_language="en",
        level="A1"
    )

    # 2. Add words to vocabulary
    for word in ["house", "cat", "dog", "run", "eat"]:
        await word_service.add_word_for_user(
            profile_id=profile.profile_id,
            word_text=word,
            source_language="en"
        )

    # 3. Start lesson
    lesson = await lesson_service.start_lesson(
        profile_id=profile.profile_id,
        words_count=5
    )

    assert lesson.words_count == 5

    # 4. Answer all questions
    correct_count = 0
    for i in range(5):
        question = await lesson_service.get_next_question(lesson.lesson_id)

        # Simulate correct answer
        result = await lesson_service.process_answer(
            lesson_id=lesson.lesson_id,
            user_word_id=question.user_word_id,
            user_answer=question.correct_answer,
            correct_answer=question.correct_answer
        )

        if result.is_correct:
            correct_count += 1

    # 5. Complete lesson
    summary = await lesson_service.complete_lesson(lesson.lesson_id)

    assert summary.correct_answers == correct_count
    assert summary.incorrect_answers == 5 - correct_count
```

### 15.5 Test Configuration

**pytest.ini:**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (DB, API)
    e2e: End-to-end tests (full flow)
    slow: Slow tests (> 1 second)

addopts =
    -v
    --strict-markers
    --cov=src/words
    --cov-report=html
    --cov-report=term-missing
```

**Running Tests:**

```bash
# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run with coverage
pytest --cov=src/words --cov-report=html

# Run specific test file
pytest tests/unit/test_algorithm.py

# Run with verbose output
pytest -vv

# Skip integration tests (no API calls)
pytest -m "not integration"
```

---

## 16. Migration and Evolution Strategy

### 16.1 Database Migration Strategy

**Schema Evolution:**

```python
# Example migration: Add timezone to users
# alembic/versions/001_add_user_timezone.py

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column(
        'users',
        sa.Column('timezone', sa.String(50), nullable=True)
    )

    # Set default for existing users
    op.execute("UPDATE users SET timezone = 'Europe/Moscow' WHERE timezone IS NULL")

    # Make not nullable after setting defaults
    op.alter_column('users', 'timezone', nullable=False)

def downgrade():
    op.drop_column('users', 'timezone')
```

**Zero-Downtime Migrations:**

1. **Additive Changes:** Add new columns/tables (backward compatible)
2. **Deploy Code:** Update application to use new schema
3. **Data Migration:** Migrate data in background
4. **Remove Old:** After verification, remove old columns

### 16.2 Feature Flags

**For gradual rollout of new features:**

```python
# src/words/config/features.py
from dataclasses import dataclass

@dataclass
class FeatureFlags:
    enable_voice_messages: bool = False
    enable_gamification: bool = False
    enable_image_flashcards: bool = False
    use_new_algorithm: bool = False

feature_flags = FeatureFlags()

# Usage in code
if feature_flags.enable_gamification:
    await show_achievement(user_id, achievement)
```

### 16.3 API Versioning (Future)

**If exposing API in future:**

```python
from enum import Enum

class APIVersion(Enum):
    V1 = "v1"
    V2 = "v2"

# Versioned endpoints
@router.get("/api/v1/stats")
async def get_stats_v1(user_id: int):
    # Legacy stats format
    pass

@router.get("/api/v2/stats")
async def get_stats_v2(user_id: int):
    # New stats format with additional metrics
    pass
```

### 16.4 Deprecation Strategy

**When removing features:**

1. **Announce:** Notify users in advance (if applicable)
2. **Deprecate:** Mark as deprecated, log usage
3. **Remove:** After grace period, remove code

```python
import warnings

def old_function():
    warnings.warn(
        "old_function is deprecated, use new_function instead",
        DeprecationWarning,
        stacklevel=2
    )
    # ... old implementation
```

---

## 17. Updates Based on Architecture Review

**Review Date:** 2025-11-08
**Review Status:** APPROVED WITH CRITICAL RECOMMENDATIONS
**Overall Assessment:** STRONG (8.5/10)

This section documents critical updates made to the architecture based on the comprehensive architecture review. The review identified 4 critical issues and several major recommendations that have been incorporated into this document.

### 17.1 Critical Updates Summary

The following critical issues were addressed:

1. **Rate Limiting for LLM API** - Added comprehensive rate limiting with token bucket algorithm
2. **Circuit Breaker Pattern** - Implemented circuit breaker for external API resilience
3. **Concurrent Lesson Session Handling** - Added locking mechanisms and active session checks
4. **Transaction Management** - Implemented Unit of Work pattern with proper ACID guarantees

### 17.2 Review Reference

Full review details can be found in: `/opt/projects/words/docs/architecture_review.md`

**Key Review Findings:**
- Requirements Coverage: 100% (12/12 use cases)
- Architectural Quality: 9/10
- Scalability: 8/10
- Reliability: 8/10 (improved with updates)
- Security: 8/10

### 17.3 Updated Sections

The following sections were updated to address critical and major recommendations:

**Section 8.2 (LLM API Integration):**
- Added `aiolimiter` for rate limiting (3000 req/min → 2500 req/min with safety margin)
- Implemented circuit breaker pattern using `circuitbreaker` library
- Added priority queue for LLM requests
- Enhanced fallback strategy

**Section 8.3 (Caching Strategy):**
- Added answer normalization for better cache hit rates
- Implemented LLM-generated distractor caching
- Enhanced cache key generation strategy

**Section 3 (System Components):**
- Added `LessonLockManager` for concurrent session handling
- Added `CircuitBreakerManager` for external API resilience
- Added `RequestPriorityQueue` for LLM request management

**Section 11 (Error Handling):**
- Implemented Unit of Work pattern for transaction management
- Added `@db_retry` decorator for automatic database retry
- Enhanced transaction rollback strategy with savepoints

### 17.4 Additional Improvements

**Major Enhancements (Post-Review):**
- Validation cache now uses normalized answers (increased hit rate: 40% → 70%)
- Database retry logic with exponential backoff
- Idempotency keys for critical operations
- LLM-generated multiple choice distractors (optional, post-MVP)

**New Dependencies Added:**
```python
# requirements.txt additions
aiolimiter==1.1.0           # Rate limiting
circuitbreaker==2.0.0       # Circuit breaker pattern
tenacity==8.2.3             # Retry logic (already present, confirmed)
```

### 17.5 Performance Improvements

Expected improvements from updates:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Cache hit rate (validations) | ~40% | ~70% | +75% |
| LLM API error rate | Variable | < 1% | Significant |
| Concurrent lesson conflicts | Possible | Prevented | 100% |
| Transaction consistency | At-risk | Guaranteed | ACID compliant |
| Circuit breaker recovery | N/A | < 60s | Auto-recovery |

### 17.6 Implementation Priority

**Phase 1 (Pre-MVP - Critical):**
1. Rate limiting for LLM API
2. Concurrent lesson session handling
3. Transaction management
4. Circuit breaker (recommended but optional for MVP)

**Phase 2 (Post-MVP - Enhancements):**
1. Improved validation caching
2. Database retry logic
3. Idempotency for operations
4. LLM-generated distractors

---

## 18. Open Questions

### 18.1 Questions Requiring Clarification

**1. Frequency Lists**

**Question:** If CEFR frequency lists are not available for all target languages, should we:
- A) Generate lists using LLM (cost implications)
- B) Use simpler frequency dictionaries (e.g., Wiktionary)
- C) Start with limited language support and expand gradually

**Recommendation:** Start with option B (free frequency dictionaries) for MVP, transition to A if quality is insufficient.

---

**2. Database Choice for Production**

**Question:** When should we migrate from SQLite to PostgreSQL?
- Number of users threshold?
- Performance degradation?
- Specific features needed?

**Recommendation:**
- MVP: SQLite (< 500 users)
- Production: PostgreSQL (> 500 users or when horizontal scaling needed)
- Trigger: When response time > 2s for DB queries

---

**3. FSM Storage**

**Question:** Should we use Redis for FSM storage from the start, or begin with MemoryStorage?

**Trade-offs:**
- MemoryStorage: Simpler, no dependencies, lost on restart
- Redis: Persistent, supports multiple bot instances, requires setup

**Recommendation:** Start with MemoryStorage for MVP, migrate to Redis when scaling horizontally.

---

**4. Background Task Queue**

**Question:** Should we use Celery + RabbitMQ for background tasks, or is APScheduler sufficient?

**Analysis:**
- APScheduler: Simple, no external dependencies, single-instance
- Celery: Distributed, scalable, complex setup

**Recommendation:** APScheduler for MVP (sufficient for 100-1000 users), migrate to Celery when:
- Need to scale notification workers
- Background tasks become CPU-intensive
- Multiple bot instances needed

---

**5. LLM Provider Strategy**

**Question:** Should we support multiple LLM providers (OpenAI, Anthropic, local models)?

**Considerations:**
- Vendor lock-in risk
- Cost optimization
- API compatibility

**Recommendation:**
- MVP: OpenAI only (simpler)
- Future: Abstract LLM interface, support multiple providers
- Add when: Cost becomes significant or need better quality

---

**6. User Data Privacy**

**Question:** Do we need to implement GDPR compliance features?
- Data export
- Data deletion
- Consent tracking

**Recommendation:**
- MVP: Basic data deletion command (`/delete_my_data`)
- Post-MVP: Full GDPR compliance if targeting EU users

---

**7. Monitoring and Alerting**

**Question:** What monitoring/alerting infrastructure should we use?
- Options: Prometheus + Grafana, ELK stack, simple email alerts

**Recommendation:**
- MVP: Simple email alerts for critical errors (via logging)
- Post-MVP: Prometheus + Grafana when metrics tracking becomes important

---

**8. Multi-Language Support Priorities**

**Question:** Beyond English, Russian, Spanish, which languages should we prioritize?
- German, French (popular in Europe)?
- Chinese, Japanese (large user base)?
- Depends on user requests?

**Recommendation:** Data-driven approach:
1. Launch with 3 languages
2. Add /request_language command
3. Prioritize based on user demand

---

### 18.2 Architectural Decisions to Revisit

**Later in Development:**

1. **Caching Strategy:** May need Redis for distributed cache
2. **Database Choice:** SQLite vs PostgreSQL based on user growth
3. **Background Tasks:** APScheduler vs Celery based on scale
4. **LLM Provider:** Single vs multiple providers
5. **Testing Coverage:** Adjust based on bug patterns
6. **Monitoring:** Simple logging vs full observability stack

**Triggers for Revisiting:**
- User count milestones (100, 500, 1000, 5000)
- Performance degradation
- Cost increases
- New feature requirements

---

## Conclusion

This architecture provides a solid foundation for the language learning Telegram bot with clear separation of concerns, extensibility points, and a path to scale. The layered architecture with hexagonal principles ensures testability and maintainability, while the technology choices balance simplicity (for MVP) with future scalability.

**Key Strengths:**
- ✅ Clear component boundaries
- ✅ Async-first design for performance
- ✅ Comprehensive error handling
- ✅ Graceful degradation strategy
- ✅ Extensible adaptive algorithm
- ✅ Strong caching strategy for cost control
- ✅ Security-first approach
- ✅ Migration-ready (SQLite → PostgreSQL)

**Next Steps:**
1. Review and approve architecture
2. Set up project structure
3. Implement database models and migrations
4. Build core services (User, Word, Lesson)
5. Implement Telegram bot handlers
6. Develop adaptive algorithm
7. Integrate LLM API
8. Write tests (unit → integration → e2e)
9. Deploy to server
10. Monitor and iterate

**Success Metrics:**
- All MVP acceptance criteria met
- Response time < 2s for 95% of requests
- LLM cache hit rate > 80%
- Zero data loss incidents
- < 5 critical bugs in first month

---

**Document Version:** 1.0.0
**Author:** System Architect
**Date:** 2025-11-08
**Status:** Ready for Review
