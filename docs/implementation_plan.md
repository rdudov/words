# Implementation Plan: Language Learning Telegram Bot

**Project:** Words - Telegram Bot for Language Learning
**Version:** 1.0.0
**Created:** 2025-11-08
**Status:** Ready for Implementation

---

## Table of Contents

1. [Overview](#overview)
2. [Implementation Phases](#implementation-phases)
3. [Phase 0: Project Setup](#phase-0-project-setup)
4. [Phase 1: Core Infrastructure](#phase-1-core-infrastructure)
5. [Phase 2: User Management](#phase-2-user-management)
6. [Phase 3: Word Management](#phase-3-word-management)
7. [Phase 4: Lesson System](#phase-4-lesson-system)
8. [Phase 5: Adaptive Algorithm](#phase-5-adaptive-algorithm)
9. [Phase 6: Notifications & Polish](#phase-6-notifications--polish)
10. [Phase 7: Testing & Deployment](#phase-7-testing--deployment)
11. [Task Dependencies](#task-dependencies)
12. [Timeline Estimates](#timeline-estimates)

---

## Overview

This implementation plan breaks down the development of the Language Learning Telegram Bot into 8 phases, from initial project setup to deployment. Each phase contains specific, actionable tasks with file-level details, dependencies, and complexity estimates.

### Key Principles

- **MVP-First:** Focus on core functionality before enhancements
- **Incremental Development:** Each phase builds on previous phases
- **Test-Driven:** Write tests alongside implementation
- **Modular Design:** Follow the layered architecture strictly
- **Dependency Management:** Respect task dependencies to avoid blockers

### Complexity Legend

- 🟢 **Simple:** 1-2 hours, straightforward implementation
- 🟡 **Medium:** 3-6 hours, moderate complexity, some decisions needed
- 🔴 **Complex:** 1-2 days, significant complexity, multiple components

### Priority Legend

- **P0:** Critical for MVP, blocking other tasks
- **P1:** Important for MVP, needed soon
- **P2:** Nice to have for MVP
- **P3:** Post-MVP enhancements

---

## Implementation Phases

```
Phase 0: Project Setup (1 day)
    ↓
Phase 1: Core Infrastructure (2-3 days)
    ↓
Phase 2: User Management (2 days)
    ↓
Phase 3: Word Management (3-4 days)
    ↓
Phase 4: Lesson System (4-5 days)
    ↓
Phase 5: Adaptive Algorithm (3-4 days)
    ↓
Phase 6: Notifications & Polish (2-3 days)
    ↓
Phase 7: Testing & Deployment (3-4 days)
```

**Total Estimated Time:** 20-27 working days (4-5 weeks)

---

## Phase 0: Project Setup

**Goal:** Initialize project structure, dependencies, and development environment

**Duration:** 1 day

### Task 0.1: Initialize Project Structure ✅ COMPLETED

**Files to Create:**
```
/opt/projects/words/
├── .env.example
├── .gitignore
├── requirements.txt
├── setup.py
├── pytest.ini
├── alembic.ini
├── data/
│   ├── frequency_lists/
│   └── translations/
├── logs/.gitkeep
├── src/words/
│   ├── __init__.py
│   └── __main__.py
└── tests/
    ├── __init__.py
    └── conftest.py
```

**Actions:**
1. Create directory structure as specified in architecture.md section 4.1
2. Initialize git repository (already done)
3. Create `.gitignore` with Python, venv, logs, database files
4. Create empty `__init__.py` files for all Python packages

**Acceptance Criteria:**
- All directories exist
- Git ignores appropriate files
- Project can be imported as a Python package

### Task 0.2: Setup Dependencies ✅ COMPLETED

**File to Create:** `requirements.txt`

**Dependencies to Include:**
```txt
# Core Framework
aiogram==3.4.1
python-telegram-bot==20.7  # Alternative, not used

# Database
sqlalchemy[asyncio]==2.0.25
alembic==1.13.1
aiosqlite==0.19.0
asyncpg==0.29.0  # For PostgreSQL (future)

# LLM Integration
openai==1.12.0
tenacity==8.2.3

# Rate Limiting & Circuit Breaker
aiolimiter==1.1.0
circuitbreaker==1.4.0

# String Matching
python-Levenshtein==0.25.0
rapidfuzz==3.6.1

# Scheduling
apscheduler==3.10.4

# Logging
structlog==24.1.0

# Configuration
pydantic==2.6.1
pydantic-settings==2.1.0
python-dotenv==1.0.1

# Utilities
pytz==2024.1

# Testing
pytest==8.0.0
pytest-asyncio==0.23.4
pytest-cov==4.1.0
pytest-mock==3.12.0
faker==22.6.0

# Code Quality
black==24.1.1
ruff==0.2.1
mypy==1.8.0
```

**Actions:**
1. Create `requirements.txt` with all dependencies
2. Create virtual environment: `python3 -m venv venv`
3. Activate venv: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`

**Acceptance Criteria:**
- Virtual environment created
- All dependencies installed without errors
- Can import key libraries (aiogram, sqlalchemy, openai)

### Task 0.3: Setup Configuration Files ✅ COMPLETED

**Files to Create:**
- `.env.example`
- `pytest.ini`
- `setup.py` (optional)

**.env.example:**
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# LLM API
LLM_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4o-mini

# Database
DATABASE_URL=sqlite+aiosqlite:///data/database/words.db
# For PostgreSQL: postgresql+asyncpg://user:pass@localhost/words

# Lesson Configuration
WORDS_PER_LESSON=30
MASTERED_THRESHOLD=30
CHOICE_TO_INPUT_THRESHOLD=3

# Notifications
NOTIFICATION_ENABLED=true
NOTIFICATION_INTERVAL_HOURS=6
NOTIFICATION_TIME_START=07:00
NOTIFICATION_TIME_END=23:00
TIMEZONE=Europe/Moscow

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# Development
DEBUG=false
```

**pytest.ini:**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts =
    -v
    --cov=src/words
    --cov-report=html
    --cov-report=term-missing
```

**Actions:**
1. Create configuration files
2. Copy `.env.example` to `.env` (not in git)
3. Fill in actual values in `.env`

**Acceptance Criteria:**
- Configuration files exist
- `.env` has real credentials (not committed)
- pytest configuration is valid

**Dependencies:** None

---

## Phase 1: Core Infrastructure

**Goal:** Implement foundational infrastructure components

**Duration:** 2-3 days

### Task 1.1: Configuration Management ✅ COMPLETED

**File to Create:** `src/words/config/settings.py`

**Implementation:**
```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")

    # LLM
    llm_api_key: str = Field(..., env="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", env="LLM_MODEL")

    # Database
    database_url: str = Field(..., env="DATABASE_URL")

    # Lesson Settings
    words_per_lesson: int = Field(default=30, env="WORDS_PER_LESSON")
    mastered_threshold: int = Field(default=30, env="MASTERED_THRESHOLD")
    choice_to_input_threshold: int = Field(default=3, env="CHOICE_TO_INPUT_THRESHOLD")

    # Notifications
    notification_enabled: bool = Field(default=True, env="NOTIFICATION_ENABLED")
    notification_interval_hours: int = Field(default=6, env="NOTIFICATION_INTERVAL_HOURS")
    notification_time_start: str = Field(default="07:00", env="NOTIFICATION_TIME_START")
    notification_time_end: str = Field(default="23:00", env="NOTIFICATION_TIME_END")
    timezone: str = Field(default="Europe/Moscow", env="TIMEZONE")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/bot.log", env="LOG_FILE")

    # Development
    debug: bool = Field(default=False, env="DEBUG")

    class Config:
        env_file = ".env"
        case_sensitive = False

# Singleton instance
settings = Settings()
```

**File to Create:** `src/words/config/constants.py`

**Constants:**
```python
# Word Status
class WordStatus:
    NEW = "new"
    LEARNING = "learning"
    REVIEWING = "reviewing"
    MASTERED = "mastered"

# Test Types
class TestType:
    MULTIPLE_CHOICE = "multiple_choice"
    INPUT = "input"

# Translation Directions
class Direction:
    NATIVE_TO_FOREIGN = "native_to_foreign"
    FOREIGN_TO_NATIVE = "foreign_to_native"

# CEFR Levels
CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

# Supported Languages (ISO 639-1 codes)
SUPPORTED_LANGUAGES = {
    "en": "English",
    "ru": "Русский",
    "es": "Español"
}

# Validation Methods
class ValidationMethod:
    EXACT = "exact"
    FUZZY = "fuzzy"
    LLM = "llm"

# Fuzzy Matching
FUZZY_MATCH_THRESHOLD = 2  # Levenshtein distance
```

**Acceptance Criteria:**
- Settings loaded from environment variables
- All configuration accessible via `settings` instance
- Constants defined and importable

**Dependencies:** Task 0.2

### Task 1.2: Database Setup ✅ COMPLETED

**File to Create:** `src/words/infrastructure/database.py`

**Implementation:**
```python
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
from src.words.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    poolclass=NullPool if "sqlite" in settings.database_url else None,
    pool_pre_ping=True
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@asynccontextmanager
async def get_session():
    """Provide database session with automatic cleanup"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """Initialize database (create tables)"""
    from src.words.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")

async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")
```

**Acceptance Criteria:**
- Database connection established
- Session management working
- Connection pool configured correctly

**Dependencies:** Task 1.1

### Task 1.3: ORM Models - Base ✅ COMPLETED

**File to Create:** `src/words/models/base.py`

**Implementation:**
```python
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime

class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all ORM models"""
    pass

class TimestampMixin:
    """Mixin for created_at/updated_at timestamps"""
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=True
    )
```

**Acceptance Criteria:**
- Base model can be imported
- TimestampMixin works correctly

**Dependencies:** Task 1.2

### Task 1.4: ORM Models - User & Profile ✅ COMPLETED

**Files to Create:**
- `src/words/models/user.py`
- `src/words/models/__init__.py` (export models)

**Implementation:** `user.py`
```python
from sqlalchemy import BigInteger, String, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin
from datetime import datetime
import enum

class User(Base, TimestampMixin):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    native_language: Mapped[str] = mapped_column(String(10), nullable=False)
    interface_language: Mapped[str] = mapped_column(String(10), nullable=False)
    last_active_at: Mapped[datetime | None] = mapped_column(nullable=True)
    notification_enabled: Mapped[bool] = mapped_column(default=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")

    # Relationships
    profiles: Mapped[list["LanguageProfile"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

class CEFRLevel(enum.Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"

class LanguageProfile(Base, TimestampMixin):
    __tablename__ = "language_profiles"

    profile_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    level: Mapped[CEFRLevel] = mapped_column(SQLEnum(CEFRLevel), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="profiles")
    user_words: Mapped[list["UserWord"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan"
    )
    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan"
    )
```

**Acceptance Criteria:**
- Models match database schema from architecture.md
- Relationships defined correctly
- Can create tables without errors

**Dependencies:** Task 1.3

### Task 1.5: ORM Models - Word & UserWord ✅ COMPLETED

**File to Create:** `src/words/models/word.py`

**Implementation:**
```python
from sqlalchemy import String, Integer, JSON, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin
from datetime import datetime
import enum

class Word(Base):
    __tablename__ = "words"

    word_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    level: Mapped[str | None] = mapped_column(String(2), nullable=True)
    translations: Mapped[dict] = mapped_column(JSON, nullable=True)
    examples: Mapped[list] = mapped_column(JSON, nullable=True)
    word_forms: Mapped[dict] = mapped_column(JSON, nullable=True)
    frequency_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint('word', 'language', name='uq_word_language'),
    )

class WordStatusEnum(enum.Enum):
    NEW = "new"
    LEARNING = "learning"
    REVIEWING = "reviewing"
    MASTERED = "mastered"

class UserWord(Base, TimestampMixin):
    __tablename__ = "user_words"

    user_word_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("language_profiles.profile_id", ondelete="CASCADE"),
        nullable=False
    )
    word_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("words.word_id", ondelete="CASCADE"),
        nullable=False
    )
    status: Mapped[WordStatusEnum] = mapped_column(
        SQLEnum(WordStatusEnum),
        default=WordStatusEnum.NEW
    )
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(nullable=True)
    review_interval: Mapped[int] = mapped_column(Integer, default=0)
    easiness_factor: Mapped[float] = mapped_column(default=2.5)

    # Relationships
    profile: Mapped["LanguageProfile"] = relationship(back_populates="user_words")
    word: Mapped["Word"] = relationship()
    statistics: Mapped[list["WordStatistics"]] = relationship(
        back_populates="user_word",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint('profile_id', 'word_id', name='uq_profile_word'),
    )
```

**Acceptance Criteria:**
- Word and UserWord models complete
- JSON fields for translations, examples, word_forms
- Spaced repetition fields included

**Dependencies:** Task 1.4

### Task 1.6: ORM Models - Lesson & Statistics ✅ COMPLETED

**Files to Create:**
- `src/words/models/lesson.py`
- `src/words/models/statistics.py`

**Implementation:** `lesson.py`
```python
from sqlalchemy import Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from datetime import datetime

class Lesson(Base):
    __tablename__ = "lessons"

    lesson_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("language_profiles.profile_id", ondelete="CASCADE"),
        nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    words_count: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_answers: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    profile: Mapped["LanguageProfile"] = relationship(back_populates="lessons")
    attempts: Mapped[list["LessonAttempt"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan"
    )

class LessonAttempt(Base):
    __tablename__ = "lesson_attempts"

    attempt_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lessons.lesson_id", ondelete="CASCADE"),
        nullable=False
    )
    user_word_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user_words.user_word_id"),
        nullable=False
    )
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    test_type: Mapped[str] = mapped_column(String(20), nullable=False)
    user_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(nullable=False)
    validation_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    lesson: Mapped["Lesson"] = relationship(back_populates="attempts")
    user_word: Mapped["UserWord"] = relationship()
```

**Implementation:** `statistics.py`
```python
from sqlalchemy import Integer, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class WordStatistics(Base):
    __tablename__ = "word_statistics"

    stat_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_word_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user_words.user_word_id", ondelete="CASCADE"),
        nullable=False
    )
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    test_type: Mapped[str] = mapped_column(String(20), nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)
    total_correct: Mapped[int] = mapped_column(Integer, default=0)
    total_errors: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user_word: Mapped["UserWord"] = relationship(back_populates="statistics")

    __table_args__ = (
        UniqueConstraint(
            'user_word_id', 'direction', 'test_type',
            name='uq_userword_direction_testtype'
        ),
    )
```

**Acceptance Criteria:**
- Lesson and statistics models complete
- Relationships properly defined
- Database tables can be created

**Dependencies:** Task 1.5

### Task 1.7: ORM Models - Cache Tables ✅ COMPLETED

**File to Create:** `src/words/models/cache.py`

**Implementation:**
```python
from sqlalchemy import String, JSON, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base
from datetime import datetime

class CachedTranslation(Base):
    __tablename__ = "cached_translations"

    cache_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(255), nullable=False)
    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    translation_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    cached_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint(
            'word', 'source_language', 'target_language',
            name='uq_word_src_tgt'
        ),
    )

class CachedValidation(Base):
    __tablename__ = "cached_validations"

    validation_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("words.word_id"),
        nullable=False
    )
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    expected_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    user_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    is_correct: Mapped[bool] = mapped_column(nullable=False)
    llm_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    cached_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            'word_id', 'direction', 'expected_answer', 'user_answer',
            name='uq_validation_lookup'
        ),
    )
```

**Acceptance Criteria:**
- Cache models defined
- Unique constraints for efficient lookups

**Dependencies:** Task 1.5

### Task 1.8: Logging Setup ✅ COMPLETED

**File to Create:** `src/words/utils/logger.py`

**Implementation:**
```python
import logging
import structlog
from pathlib import Path
from src.words.config.settings import settings

def setup_logging():
    """Configure structured logging"""

    # Create logs directory if not exists
    log_dir = Path(settings.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure standard logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(message)s",
        handlers=[
            logging.FileHandler(settings.log_file),
            logging.StreamHandler()
        ]
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if settings.debug
                else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False
    )

    return structlog.get_logger()

# Module-level logger
logger = setup_logging()
```

**Acceptance Criteria:**
- Logging configured and working
- Logs written to file and console
- Structured logging for easy parsing

**Dependencies:** Task 1.1

### Task 1.9: Initialize Database Script ✅ COMPLETED

**File to Create:** `scripts/init_db.py`

**Implementation:**
```python
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.words.infrastructure.database import init_db, engine
from src.words.utils.logger import logger

async def main():
    """Initialize database schema"""
    logger.info("Initializing database...")

    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
```

**Usage:**
```bash
python scripts/init_db.py
```

**Acceptance Criteria:**
- Script creates all database tables
- Can be run multiple times safely (idempotent)
- Proper error handling

**Dependencies:** Tasks 1.2-1.7

---

## Phase 2: User Management

**Goal:** Implement user registration, profile management, and basic bot handlers

**Duration:** 2 days

### Task 2.1: Base Repository Pattern 🟢 P0 ✅ COMPLETED

**File to Create:** `src/words/repositories/base.py`

**Implementation:**
```python
from typing import TypeVar, Generic, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations"""

    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> T | None:
        """Get entity by ID"""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """Get all entities with pagination"""
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def add(self, entity: T) -> T:
        """Add new entity"""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: T) -> None:
        """Delete entity"""
        await self.session.delete(entity)
        await self.session.flush()

    async def commit(self) -> None:
        """Commit transaction"""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback transaction"""
        await self.session.rollback()
```

**Acceptance Criteria:**
- Base repository provides common CRUD
- Generic type hints working
- Can be extended by specific repositories

**Dependencies:** Task 1.2

### Task 2.2: User Repository 🟡 P0 ✅ COMPLETED

**File to Create:** `src/words/repositories/user.py`

**Implementation:**
```python
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from .base import BaseRepository
from src.words.models.user import User, LanguageProfile

class UserRepository(BaseRepository[User]):
    """User-specific database operations"""

    def __init__(self, session):
        super().__init__(session, User)

    async def get_by_telegram_id(self, user_id: int) -> User | None:
        """Get user by Telegram ID with profiles"""
        result = await self.session.execute(
            select(User)
            .where(User.user_id == user_id)
            .options(selectinload(User.profiles))
        )
        return result.scalar_one_or_none()

    async def get_users_for_notification(
        self,
        inactive_hours: int,
        current_hour: int
    ) -> list[User]:
        """Get users needing notification"""
        cutoff_time = datetime.utcnow() - timedelta(hours=inactive_hours)

        result = await self.session.execute(
            select(User).where(
                and_(
                    User.notification_enabled == True,
                    User.last_active_at < cutoff_time
                )
            )
        )
        return list(result.scalars().all())

    async def update_last_active(self, user_id: int) -> None:
        """Update user's last active timestamp"""
        user = await self.get_by_telegram_id(user_id)
        if user:
            user.last_active_at = datetime.utcnow()
            await self.session.flush()

class ProfileRepository(BaseRepository[LanguageProfile]):
    """Language profile operations"""

    def __init__(self, session):
        super().__init__(session, LanguageProfile)

    async def get_active_profile(self, user_id: int) -> LanguageProfile | None:
        """Get user's active language profile"""
        result = await self.session.execute(
            select(LanguageProfile).where(
                and_(
                    LanguageProfile.user_id == user_id,
                    LanguageProfile.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_user_profiles(self, user_id: int) -> list[LanguageProfile]:
        """Get all profiles for user"""
        result = await self.session.execute(
            select(LanguageProfile).where(
                LanguageProfile.user_id == user_id
            )
        )
        return list(result.scalars().all())

    async def switch_active_language(
        self,
        user_id: int,
        target_language: str
    ) -> LanguageProfile:
        """Switch active language profile"""
        # Deactivate all profiles
        profiles = await self.get_user_profiles(user_id)
        for profile in profiles:
            profile.is_active = False

        # Activate target profile
        target = next(
            (p for p in profiles if p.target_language == target_language),
            None
        )
        if target:
            target.is_active = True
            await self.session.flush()

        return target
```

**Acceptance Criteria:**
- User CRUD operations working
- Profile management implemented
- Notification query optimized

**Dependencies:** Task 2.1, Task 1.4

### Task 2.3: User Service 🟡 P0 ✅ COMPLETED

**File to Create:** `src/words/services/user.py`

**Implementation:**
```python
from src.words.repositories.user import UserRepository, ProfileRepository
from src.words.models.user import User, LanguageProfile, CEFRLevel
from src.words.utils.logger import logger
from datetime import datetime

class UserService:
    """Business logic for user management"""

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
        user = User(
            user_id=user_id,
            native_language=native_language,
            interface_language=interface_language,
            last_active_at=datetime.utcnow()
        )

        user = await self.user_repo.add(user)
        await self.user_repo.commit()

        logger.info(
            "user_registered",
            user_id=user_id,
            native_language=native_language
        )

        return user

    async def create_language_profile(
        self,
        user_id: int,
        target_language: str,
        level: str
    ) -> LanguageProfile:
        """Create new language learning profile"""
        # Deactivate other profiles
        profiles = await self.profile_repo.get_user_profiles(user_id)
        for profile in profiles:
            profile.is_active = False

        # Create new profile
        profile = LanguageProfile(
            user_id=user_id,
            target_language=target_language,
            level=CEFRLevel[level],
            is_active=True
        )

        profile = await self.profile_repo.add(profile)
        await self.profile_repo.commit()

        logger.info(
            "profile_created",
            user_id=user_id,
            language=target_language,
            level=level
        )

        return profile

    async def get_or_create_user(self, user_id: int) -> User | None:
        """Get existing user or return None if not registered"""
        return await self.user_repo.get_by_telegram_id(user_id)

    async def switch_active_language(
        self,
        user_id: int,
        target_language: str
    ) -> LanguageProfile:
        """Switch to different language"""
        profile = await self.profile_repo.switch_active_language(
            user_id,
            target_language
        )
        await self.profile_repo.commit()

        logger.info(
            "language_switched",
            user_id=user_id,
            language=target_language
        )

        return profile

    async def update_last_active(self, user_id: int) -> None:
        """Update user activity timestamp"""
        await self.user_repo.update_last_active(user_id)
        await self.user_repo.commit()
```

**Acceptance Criteria:**
- User registration flow working
- Profile creation and switching implemented
- Activity tracking functional

**Dependencies:** Task 2.2

### Task 2.4: Bot State Machine 🟢 P0

**Files to Create:**
- `src/words/bot/states/registration.py`
- `src/words/bot/states/__init__.py`

**Implementation:** `registration.py`
```python
from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    """States for user registration flow"""
    native_language = State()
    target_language = State()
    level = State()
    confirming = State()

class AddWordStates(StatesGroup):
    """States for adding new word"""
    waiting_for_word = State()
    selecting_meaning = State()
    confirming = State()

class LessonStates(StatesGroup):
    """States for lesson flow"""
    in_progress = State()
    answering_question = State()
    viewing_result = State()
```

**Acceptance Criteria:**
- State machines defined for all flows
- States are importable and usable

**Dependencies:** None

### Task 2.5: Telegram Keyboards 🟢 P1

**Files to Create:**
- `src/words/bot/keyboards/common.py`
- `src/words/bot/keyboards/__init__.py`

**Implementation:**
```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from src.words.config.constants import SUPPORTED_LANGUAGES, CEFR_LEVELS

def build_language_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for language selection"""
    builder = InlineKeyboardBuilder()

    for code, name in SUPPORTED_LANGUAGES.items():
        builder.button(
            text=name,
            callback_data=f"select_language:{code}"
        )

    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()

def build_level_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for CEFR level selection"""
    builder = InlineKeyboardBuilder()

    for level in CEFR_LEVELS:
        builder.button(
            text=level,
            callback_data=f"select_level:{level}"
        )

    builder.adjust(3)  # 3 buttons per row
    return builder.as_markup()

def build_main_menu() -> ReplyKeyboardMarkup:
    """Build main menu keyboard"""
    builder = ReplyKeyboardBuilder()

    builder.button(text="📚 Start Lesson")
    builder.button(text="➕ Add Word")
    builder.button(text="📊 Statistics")
    builder.button(text="⚙️ Settings")

    builder.adjust(2, 2)  # 2 rows with 2 buttons each
    return builder.as_markup(resize_keyboard=True)

def build_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Build Yes/No confirmation keyboard"""
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Yes", callback_data="confirm:yes")
    builder.button(text="❌ No", callback_data="confirm:no")

    builder.adjust(2)
    return builder.as_markup()
```

**Acceptance Criteria:**
- Keyboards render correctly in Telegram
- Callback data properly formatted
- Responsive layout

**Dependencies:** Task 1.1

### Task 2.6: Registration Handler 🟡 P0

**Files to Create:**
- `src/words/bot/handlers/start.py`
- `src/words/bot/handlers/__init__.py`

**Implementation:**
```python
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from src.words.bot.states.registration import RegistrationStates
from src.words.bot.keyboards.common import (
    build_language_keyboard,
    build_level_keyboard,
    build_main_menu
)
from src.words.services.user import UserService
from src.words.infrastructure.database import get_session
from src.words.repositories.user import UserRepository, ProfileRepository
from src.words.config.constants import SUPPORTED_LANGUAGES, CEFR_LEVELS

router = Router(name="start")

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    user_id = message.from_user.id

    # Check if user exists
    async with get_session() as session:
        user_service = UserService(
            UserRepository(session),
            ProfileRepository(session)
        )

        user = await user_service.get_or_create_user(user_id)

    if user:
        # Existing user - show main menu
        await message.answer(
            f"Welcome back! Ready to practice?",
            reply_markup=build_main_menu()
        )
    else:
        # New user - start registration
        await message.answer(
            "Welcome to the Language Learning Bot! 🎓\n\n"
            "I'll help you learn foreign words using adaptive algorithms.\n\n"
            "First, let's set up your profile.\n"
            "What is your native language?",
            reply_markup=build_language_keyboard()
        )
        await state.set_state(RegistrationStates.native_language)

@router.callback_query(
    StateFilter(RegistrationStates.native_language),
    F.data.startswith("select_language:")
)
async def process_native_language(
    callback: CallbackQuery,
    state: FSMContext
):
    """Process native language selection"""
    language_code = callback.data.split(":")[1]

    await state.update_data(native_language=language_code)

    await callback.message.edit_text(
        f"Great! Your native language: {SUPPORTED_LANGUAGES[language_code]}\n\n"
        "Which language do you want to learn?",
        reply_markup=build_language_keyboard()
    )

    await state.set_state(RegistrationStates.target_language)
    await callback.answer()

@router.callback_query(
    StateFilter(RegistrationStates.target_language),
    F.data.startswith("select_language:")
)
async def process_target_language(
    callback: CallbackQuery,
    state: FSMContext
):
    """Process target language selection"""
    language_code = callback.data.split(":")[1]
    data = await state.get_data()

    # Check if same as native
    if language_code == data["native_language"]:
        await callback.answer(
            "Please select a different language from your native language!",
            show_alert=True
        )
        return

    await state.update_data(target_language=language_code)

    await callback.message.edit_text(
        f"Excellent! You're learning: {SUPPORTED_LANGUAGES[language_code]}\n\n"
        "What's your current level? (CEFR scale)",
        reply_markup=build_level_keyboard()
    )

    await state.set_state(RegistrationStates.level)
    await callback.answer()

@router.callback_query(
    StateFilter(RegistrationStates.level),
    F.data.startswith("select_level:")
)
async def process_level(
    callback: CallbackQuery,
    state: FSMContext
):
    """Process level selection and complete registration"""
    level = callback.data.split(":")[1]
    data = await state.get_data()

    user_id = callback.from_user.id

    # Create user and profile
    async with get_session() as session:
        user_service = UserService(
            UserRepository(session),
            ProfileRepository(session)
        )

        # Register user
        await user_service.register_user(
            user_id=user_id,
            native_language=data["native_language"],
            interface_language=data["native_language"]  # Use native as interface
        )

        # Create language profile
        await user_service.create_language_profile(
            user_id=user_id,
            target_language=data["target_language"],
            level=level
        )

    await callback.message.delete()
    await callback.message.answer(
        "✅ Registration complete!\n\n"
        f"Learning: {SUPPORTED_LANGUAGES[data['target_language']]}\n"
        f"Level: {level}\n\n"
        "Ready to start learning? Choose an action below:",
        reply_markup=build_main_menu()
    )

    await state.clear()
    await callback.answer()
```

**Acceptance Criteria:**
- Registration flow works end-to-end
- User and profile created in database
- State machine transitions correctly

**Dependencies:** Tasks 2.3, 2.4, 2.5

### Task 2.7: Main Bot Setup 🟢 P0

**Files to Create:**
- `src/words/bot/__init__.py`
- `src/words/__main__.py`

**Implementation:** `bot/__init__.py`
```python
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from src.words.config.settings import settings
from src.words.utils.logger import logger

async def setup_bot() -> tuple[Bot, Dispatcher]:
    """Initialize bot and dispatcher"""

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register handlers
    from src.words.bot.handlers import start

    dp.include_router(start.router)

    logger.info("Bot initialized")

    return bot, dp
```

**Implementation:** `__main__.py`
```python
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.words.bot import setup_bot
from src.words.infrastructure.database import init_db, close_db
from src.words.utils.logger import logger

async def main():
    """Main entry point"""
    logger.info("Starting bot...")

    # Initialize database
    await init_db()

    # Setup bot
    bot, dp = await setup_bot()

    try:
        # Start polling
        logger.info("Bot is running. Press Ctrl+C to stop.")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await close_db()
        logger.info("Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
```

**Usage:**
```bash
python -m src.words
```

**Acceptance Criteria:**
- Bot starts and connects to Telegram
- Registration flow works
- Can stop gracefully with Ctrl+C

**Dependencies:** Task 2.6

---

## Phase 3: Word Management

**Goal:** Implement word addition, translation service, LLM integration, and caching

**Duration:** 3-4 days

### Task 3.1: LLM Client 🟡 P0

**File to Create:** `src/words/infrastructure/llm_client.py`

**Implementation:**
(See detailed implementation in Task 1 of architecture.md section 8.2)

**Key Features:**
- OpenAI async client
- Retry logic with tenacity
- Translation and validation methods
- Proper error handling
- JSON response parsing

**Acceptance Criteria:**
- Can call OpenAI API successfully
- Retries on transient failures
- Returns structured data
- Handles rate limits gracefully

**Dependencies:** Task 1.1

### Task 3.2: Cache Repository 🟡 P1

**File to Create:** `src/words/repositories/cache.py`

**Implementation:**
```python
from sqlalchemy import select, and_
from datetime import datetime
from .base import BaseRepository
from src.words.models.cache import CachedTranslation, CachedValidation

class CacheRepository:
    """Cache management for LLM results"""

    def __init__(self, session):
        self.session = session

    async def get_translation(
        self,
        word: str,
        source_lang: str,
        target_lang: str
    ) -> dict | None:
        """Get cached translation"""
        result = await self.session.execute(
            select(CachedTranslation).where(
                and_(
                    CachedTranslation.word == word.lower(),
                    CachedTranslation.source_language == source_lang,
                    CachedTranslation.target_language == target_lang,
                    # Check expiration
                    (CachedTranslation.expires_at.is_(None)) |
                    (CachedTranslation.expires_at > datetime.utcnow())
                )
            )
        )

        cached = result.scalar_one_or_none()
        return cached.translation_data if cached else None

    async def set_translation(
        self,
        word: str,
        source_lang: str,
        target_lang: str,
        data: dict,
        expires_at: datetime | None = None
    ) -> None:
        """Cache translation result"""
        cached = CachedTranslation(
            word=word.lower(),
            source_language=source_lang,
            target_language=target_lang,
            translation_data=data,
            expires_at=expires_at
        )

        # Upsert logic
        existing = await self.session.execute(
            select(CachedTranslation).where(
                and_(
                    CachedTranslation.word == word.lower(),
                    CachedTranslation.source_language == source_lang,
                    CachedTranslation.target_language == target_lang
                )
            )
        )

        if existing_record := existing.scalar_one_or_none():
            existing_record.translation_data = data
            existing_record.cached_at = datetime.utcnow()
            existing_record.expires_at = expires_at
        else:
            self.session.add(cached)

        await self.session.flush()

    async def get_validation(
        self,
        word_id: int,
        direction: str,
        expected: str,
        user_answer: str
    ) -> tuple[bool, str] | None:
        """Get cached validation result"""
        result = await self.session.execute(
            select(CachedValidation).where(
                and_(
                    CachedValidation.word_id == word_id,
                    CachedValidation.direction == direction,
                    CachedValidation.expected_answer == expected.lower(),
                    CachedValidation.user_answer == user_answer.lower()
                )
            )
        )

        cached = result.scalar_one_or_none()
        if cached:
            return (cached.is_correct, cached.llm_comment)
        return None

    async def set_validation(
        self,
        word_id: int,
        direction: str,
        expected: str,
        user_answer: str,
        is_correct: bool,
        comment: str
    ) -> None:
        """Cache validation result"""
        cached = CachedValidation(
            word_id=word_id,
            direction=direction,
            expected_answer=expected.lower(),
            user_answer=user_answer.lower(),
            is_correct=is_correct,
            llm_comment=comment
        )

        self.session.add(cached)
        await self.session.flush()
```

**Acceptance Criteria:**
- Translation caching works
- Validation caching works
- Cache lookups are fast
- Expiration handled correctly

**Dependencies:** Task 1.7

### Task 3.3: Translation Service 🟡 P0

**File to Create:** `src/words/services/translation.py`

**Implementation:**
```python
from src.words.infrastructure.llm_client import LLMClient
from src.words.repositories.cache import CacheRepository
from src.words.utils.logger import logger
from tenacity import retry, stop_after_attempt, wait_exponential

class TranslationService:
    """Service for word translations using LLM"""

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
        source_lang: str,
        target_lang: str
    ) -> dict:
        """
        Get word translation with caching

        Returns:
        {
            "word": str,
            "translations": list[str],
            "examples": list[dict],
            "word_forms": dict
        }
        """
        # Check cache first
        cached = await self.cache_repo.get_translation(
            word, source_lang, target_lang
        )

        if cached:
            logger.debug(
                "translation_cache_hit",
                word=word,
                source=source_lang,
                target=target_lang
            )
            return cached

        # Call LLM
        logger.info(
            "translation_llm_call",
            word=word,
            source=source_lang,
            target=target_lang
        )

        try:
            result = await self.llm_client.translate_word(
                word, source_lang, target_lang
            )

            # Cache result (never expires)
            await self.cache_repo.set_translation(
                word, source_lang, target_lang, result
            )

            return result

        except Exception as e:
            logger.error(
                "translation_failed",
                word=word,
                error=str(e)
            )
            raise

    async def validate_answer_with_llm(
        self,
        question: str,
        expected: str,
        user_answer: str,
        source_lang: str,
        target_lang: str,
        word_id: int,
        direction: str
    ) -> tuple[bool, str]:
        """
        Validate answer using LLM

        Returns: (is_correct, comment)
        """
        # Check cache first
        cached = await self.cache_repo.get_validation(
            word_id, direction, expected, user_answer
        )

        if cached:
            logger.debug(
                "validation_cache_hit",
                word_id=word_id,
                user_answer=user_answer
            )
            return cached

        # Call LLM
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

            is_correct = result["is_correct"]
            comment = result["comment"]

            # Cache result
            await self.cache_repo.set_validation(
                word_id, direction, expected, user_answer, is_correct, comment
            )

            return (is_correct, comment)

        except Exception as e:
            logger.error(
                "validation_failed",
                word_id=word_id,
                error=str(e)
            )
            # Fallback: reject answer
            return (False, "Validation service unavailable. Please try again.")
```

**Acceptance Criteria:**
- Translation works with caching
- Validation works with caching
- Fallback on errors
- Logs all LLM calls

**Dependencies:** Tasks 3.1, 3.2

### Task 3.4: Word Repository 🟡 P0

**File to Create:** `src/words/repositories/word.py`

**Implementation:**
```python
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from .base import BaseRepository
from src.words.models.word import Word, UserWord, WordStatusEnum

class WordRepository(BaseRepository[Word]):
    """Word database operations"""

    def __init__(self, session):
        super().__init__(session, Word)

    async def find_by_text_and_language(
        self,
        word: str,
        language: str
    ) -> Word | None:
        """Find word by text and language"""
        result = await self.session.execute(
            select(Word).where(
                and_(
                    Word.word == word.lower(),
                    Word.language == language
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_frequency_words(
        self,
        language: str,
        level: str,
        limit: int = 50
    ) -> list[Word]:
        """Get most frequent words for level"""
        result = await self.session.execute(
            select(Word).where(
                and_(
                    Word.language == language,
                    Word.level == level
                )
            ).order_by(Word.frequency_rank).limit(limit)
        )
        return list(result.scalars().all())

class UserWordRepository(BaseRepository[UserWord]):
    """User word operations"""

    def __init__(self, session):
        super().__init__(session, UserWord)

    async def get_user_word(
        self,
        profile_id: int,
        word_id: int
    ) -> UserWord | None:
        """Get user's word with statistics"""
        result = await self.session.execute(
            select(UserWord).where(
                and_(
                    UserWord.profile_id == profile_id,
                    UserWord.word_id == word_id
                )
            ).options(
                selectinload(UserWord.word),
                selectinload(UserWord.statistics)
            )
        )
        return result.scalar_one_or_none()

    async def get_user_vocabulary(
        self,
        profile_id: int,
        status: WordStatusEnum | None = None
    ) -> list[UserWord]:
        """Get user's vocabulary"""
        query = select(UserWord).where(
            UserWord.profile_id == profile_id
        )

        if status:
            query = query.where(UserWord.status == status)

        result = await self.session.execute(
            query.options(
                selectinload(UserWord.word),
                selectinload(UserWord.statistics)
            )
        )
        return list(result.scalars().all())

    async def count_by_status(
        self,
        profile_id: int
    ) -> dict[str, int]:
        """Count words by status"""
        from sqlalchemy import func

        result = await self.session.execute(
            select(
                UserWord.status,
                func.count(UserWord.user_word_id)
            ).where(
                UserWord.profile_id == profile_id
            ).group_by(UserWord.status)
        )

        return {
            status.value: count
            for status, count in result.all()
        }
```

**Acceptance Criteria:**
- Word CRUD operations working
- User word management implemented
- Statistics eager loading works

**Dependencies:** Task 1.5

### Task 3.5: Word Service 🔴 P0

**File to Create:** `src/words/services/word.py`

**Implementation:**
```python
from src.words.repositories.word import WordRepository, UserWordRepository
from src.words.services.translation import TranslationService
from src.words.models.word import Word, UserWord, WordStatusEnum
from src.words.utils.logger import logger

class WordService:
    """Business logic for word management"""

    def __init__(
        self,
        word_repo: WordRepository,
        user_word_repo: UserWordRepository,
        translation_service: TranslationService
    ):
        self.word_repo = word_repo
        self.user_word_repo = user_word_repo
        self.translation_service = translation_service

    async def add_word_for_user(
        self,
        profile_id: int,
        word_text: str,
        source_language: str,
        target_language: str
    ) -> UserWord:
        """
        Add word to user vocabulary

        Flow:
        1. Get translation from LLM (or cache)
        2. Create/get Word entity
        3. Link to user (UserWord)
        4. Initialize statistics
        """
        # Get translation
        translation_data = await self.translation_service.translate_word(
            word_text, source_language, target_language
        )

        # Check if word exists
        word = await self.word_repo.find_by_text_and_language(
            word_text, target_language
        )

        if not word:
            # Create new word
            word = Word(
                word=word_text.lower(),
                language=target_language,
                translations=translation_data.get("translations", {}),
                examples=translation_data.get("examples", []),
                word_forms=translation_data.get("word_forms", {})
            )
            word = await self.word_repo.add(word)

        # Check if user already has this word
        user_word = await self.user_word_repo.get_user_word(
            profile_id, word.word_id
        )

        if user_word:
            logger.warning(
                "word_already_exists",
                profile_id=profile_id,
                word_id=word.word_id
            )
            return user_word

        # Create user word
        user_word = UserWord(
            profile_id=profile_id,
            word_id=word.word_id,
            status=WordStatusEnum.NEW
        )

        user_word = await self.user_word_repo.add(user_word)
        await self.user_word_repo.commit()

        logger.info(
            "word_added",
            profile_id=profile_id,
            word=word_text,
            word_id=word.word_id
        )

        return user_word

    async def get_word_with_translations(
        self,
        word_text: str,
        source_language: str,
        target_language: str
    ) -> dict:
        """Get word translations and examples"""
        return await self.translation_service.translate_word(
            word_text, source_language, target_language
        )

    async def get_user_vocabulary_stats(
        self,
        profile_id: int
    ) -> dict:
        """Get vocabulary statistics"""
        counts = await self.user_word_repo.count_by_status(profile_id)

        total = sum(counts.values())

        return {
            "total": total,
            "new": counts.get("new", 0),
            "learning": counts.get("learning", 0),
            "reviewing": counts.get("reviewing", 0),
            "mastered": counts.get("mastered", 0)
        }
```

**Acceptance Criteria:**
- Can add words to user vocabulary
- Translation fetched and cached
- Word deduplication works
- Statistics tracked

**Dependencies:** Tasks 3.3, 3.4

### Task 3.6: Add Word Handler 🟡 P1

**File to Create:** `src/words/bot/handlers/words.py`

**Implementation:**
```python
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from src.words.bot.states.registration import AddWordStates
from src.words.services.word import WordService
from src.words.services.user import UserService
from src.words.services.translation import TranslationService
from src.words.repositories.word import WordRepository, UserWordRepository
from src.words.repositories.user import UserRepository, ProfileRepository
from src.words.repositories.cache import CacheRepository
from src.words.infrastructure.llm_client import LLMClient
from src.words.infrastructure.database import get_session
from src.words.config.settings import settings
from src.words.utils.logger import logger

router = Router(name="words")

@router.message(F.text == "➕ Add Word")
async def cmd_add_word(message: Message, state: FSMContext):
    """Start add word flow"""
    await message.answer(
        "📝 Send me the word you want to add.\n"
        "You can send it in your native language or in the language you're learning."
    )
    await state.set_state(AddWordStates.waiting_for_word)

@router.message(StateFilter(AddWordStates.waiting_for_word))
async def process_word_input(message: Message, state: FSMContext):
    """Process word input"""
    word_text = message.text.strip()
    user_id = message.from_user.id

    if not word_text:
        await message.answer("Please send a valid word.")
        return

    # Show processing message
    processing_msg = await message.answer("🔍 Looking up translations...")

    try:
        async with get_session() as session:
            # Get user's active profile
            profile_repo = ProfileRepository(session)
            profile = await profile_repo.get_active_profile(user_id)

            if not profile:
                await message.answer("Please complete registration first using /start")
                await state.clear()
                return

            # Setup services
            llm_client = LLMClient(settings.llm_api_key, settings.llm_model)
            cache_repo = CacheRepository(session)
            translation_service = TranslationService(llm_client, cache_repo)
            word_service = WordService(
                WordRepository(session),
                UserWordRepository(session),
                translation_service
            )

            # Try to get translation (detect language)
            # First try: word is in target language
            try:
                translation_data = await word_service.get_word_with_translations(
                    word_text,
                    profile.target_language,
                    profile.user.native_language
                )
                source_lang = profile.target_language
                target_lang = profile.user.native_language
            except:
                # Second try: word is in native language
                translation_data = await word_service.get_word_with_translations(
                    word_text,
                    profile.user.native_language,
                    profile.target_language
                )
                source_lang = profile.user.native_language
                target_lang = profile.target_language

            # Add word to vocabulary
            user_word = await word_service.add_word_for_user(
                profile_id=profile.profile_id,
                word_text=word_text,
                source_language=source_lang,
                target_language=target_lang
            )

            # Format response
            translations = ", ".join(translation_data.get("translations", []))
            examples = "\n".join([
                f"• {ex.get('source', '')} → {ex.get('target', '')}"
                for ex in translation_data.get("examples", [])[:2]
            ])

            await processing_msg.delete()
            await message.answer(
                f"✅ Word added to your vocabulary!\n\n"
                f"<b>{word_text}</b>\n"
                f"Translations: {translations}\n\n"
                f"Examples:\n{examples}"
            )

    except Exception as e:
        logger.error("add_word_failed", error=str(e))
        await processing_msg.delete()
        await message.answer(
            "❌ Failed to add word. Please try again later."
        )

    await state.clear()
```

**Acceptance Criteria:**
- User can add words
- Translation fetched and displayed
- Word saved to vocabulary
- Errors handled gracefully

**Dependencies:** Task 3.5, Task 2.6

---

## Phase 4: Lesson System

**Goal:** Implement lesson orchestration, question generation, answer validation

**Duration:** 4-5 days

### Task 4.1: String Utilities (Fuzzy Matching) 🟢 P0

**File to Create:** `src/words/utils/string_utils.py`

**Implementation:**
```python
import Levenshtein
from rapidfuzz import fuzz

class FuzzyMatcher:
    """Fuzzy string matching utilities"""

    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance"""
        return Levenshtein.distance(s1.lower(), s2.lower())

    @staticmethod
    def is_typo(s1: str, s2: str, threshold: int = 2) -> bool:
        """Check if strings differ by small typo"""
        distance = FuzzyMatcher.levenshtein_distance(s1, s2)
        return 0 < distance <= threshold

    @staticmethod
    def similarity_ratio(s1: str, s2: str) -> float:
        """Calculate similarity ratio (0-100)"""
        return fuzz.ratio(s1.lower(), s2.lower())

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for comparison"""
        return text.strip().lower()
```

**Acceptance Criteria:**
- Levenshtein distance calculated correctly
- Typo detection works
- Normalization handles edge cases

**Dependencies:** Task 0.2

### Task 4.2: Validation Service 🔴 P0

**File to Create:** `src/words/services/validation.py`

**Implementation:**
```python
from src.words.services.translation import TranslationService
from src.words.utils.string_utils import FuzzyMatcher
from src.words.utils.logger import logger
from src.words.config.constants import ValidationMethod
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Answer validation result"""
    is_correct: bool
    method: str  # exact, fuzzy, llm
    feedback: str | None = None

class ValidationService:
    """Three-level answer validation"""

    def __init__(
        self,
        translation_service: TranslationService,
        fuzzy_threshold: int = 2
    ):
        self.translation_service = translation_service
        self.fuzzy_threshold = fuzzy_threshold

    async def validate_answer(
        self,
        user_answer: str,
        expected_answer: str,
        alternative_answers: list[str] | None = None,
        word_id: int | None = None,
        direction: str | None = None,
        question: str | None = None,
        source_lang: str | None = None,
        target_lang: str | None = None
    ) -> ValidationResult:
        """
        Three-level validation pipeline:
        1. Exact match
        2. Fuzzy match (typos)
        3. LLM validation (synonyms, alternative forms)
        """
        user = FuzzyMatcher.normalize_text(user_answer)
        expected = FuzzyMatcher.normalize_text(expected_answer)
        alternatives = [
            FuzzyMatcher.normalize_text(a)
            for a in (alternative_answers or [])
        ]

        # Level 1: Exact match
        if self._exact_match(user, expected, alternatives):
            logger.debug(
                "validation_exact_match",
                user_answer=user_answer,
                expected=expected_answer
            )
            return ValidationResult(
                is_correct=True,
                method=ValidationMethod.EXACT
            )

        # Level 2: Fuzzy match (typo)
        fuzzy_result = self._fuzzy_match(user, expected)
        if fuzzy_result:
            logger.debug(
                "validation_fuzzy_match",
                user_answer=user_answer,
                expected=expected_answer,
                distance=FuzzyMatcher.levenshtein_distance(user, expected)
            )
            return ValidationResult(
                is_correct=True,
                method=ValidationMethod.FUZZY,
                feedback=f"Small typo detected. Expected: {expected_answer}"
            )

        # Level 3: LLM validation
        if word_id and direction and question and source_lang and target_lang:
            return await self._llm_validate(
                question=question,
                expected_answer=expected_answer,
                user_answer=user_answer,
                source_lang=source_lang,
                target_lang=target_lang,
                word_id=word_id,
                direction=direction
            )
        else:
            # No LLM validation possible - reject
            return ValidationResult(
                is_correct=False,
                method=ValidationMethod.EXACT,
                feedback=f"Incorrect. Expected: {expected_answer}"
            )

    def _exact_match(
        self,
        user: str,
        expected: str,
        alternatives: list[str]
    ) -> bool:
        """Check exact match"""
        return user == expected or user in alternatives

    def _fuzzy_match(self, user: str, expected: str) -> bool:
        """Check fuzzy match (typo)"""
        return FuzzyMatcher.is_typo(user, expected, self.fuzzy_threshold)

    async def _llm_validate(
        self,
        question: str,
        expected_answer: str,
        user_answer: str,
        source_lang: str,
        target_lang: str,
        word_id: int,
        direction: str
    ) -> ValidationResult:
        """LLM-based validation"""
        logger.info(
            "validation_llm_call",
            word_id=word_id,
            user_answer=user_answer,
            expected=expected_answer
        )

        try:
            is_correct, comment = await self.translation_service.validate_answer_with_llm(
                question=question,
                expected=expected_answer,
                user_answer=user_answer,
                source_lang=source_lang,
                target_lang=target_lang,
                word_id=word_id,
                direction=direction
            )

            return ValidationResult(
                is_correct=is_correct,
                method=ValidationMethod.LLM,
                feedback=comment
            )

        except Exception as e:
            logger.error("llm_validation_failed", error=str(e))
            # Fallback: reject answer
            return ValidationResult(
                is_correct=False,
                method=ValidationMethod.EXACT,
                feedback=f"Incorrect. Expected: {expected_answer}"
            )
```

**Acceptance Criteria:**
- Three-level validation working
- Exact matches pass immediately
- Typos detected and accepted
- LLM fallback works
- All validations logged

**Dependencies:** Tasks 3.3, 4.1

### Task 4.3: Lesson Repositories 🟡 P0

**File to Create:** `src/words/repositories/lesson.py`

**Implementation:**
```python
from sqlalchemy import select, and_, desc
from datetime import datetime, timedelta
from .base import BaseRepository
from src.words.models.lesson import Lesson, LessonAttempt

class LessonRepository(BaseRepository[Lesson]):
    """Lesson database operations"""

    def __init__(self, session):
        super().__init__(session, Lesson)

    async def get_active_lesson(self, profile_id: int) -> Lesson | None:
        """Get active (incomplete) lesson"""
        result = await self.session.execute(
            select(Lesson).where(
                and_(
                    Lesson.profile_id == profile_id,
                    Lesson.completed_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_recent_lessons(
        self,
        profile_id: int,
        limit: int = 10
    ) -> list[Lesson]:
        """Get recent completed lessons"""
        result = await self.session.execute(
            select(Lesson).where(
                and_(
                    Lesson.profile_id == profile_id,
                    Lesson.completed_at.is_not(None)
                )
            ).order_by(desc(Lesson.completed_at)).limit(limit)
        )
        return list(result.scalars().all())

    async def count_lessons_today(self, profile_id: int) -> int:
        """Count lessons completed today"""
        from sqlalchemy import func

        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        result = await self.session.execute(
            select(func.count(Lesson.lesson_id)).where(
                and_(
                    Lesson.profile_id == profile_id,
                    Lesson.completed_at >= today_start
                )
            )
        )
        return result.scalar_one()

class LessonAttemptRepository(BaseRepository[LessonAttempt]):
    """Lesson attempt operations"""

    def __init__(self, session):
        super().__init__(session, LessonAttempt)

    async def get_lesson_attempts(
        self,
        lesson_id: int
    ) -> list[LessonAttempt]:
        """Get all attempts for a lesson"""
        result = await self.session.execute(
            select(LessonAttempt).where(
                LessonAttempt.lesson_id == lesson_id
            ).order_by(LessonAttempt.attempted_at)
        )
        return list(result.scalars().all())
```

**Acceptance Criteria:**
- Lesson CRUD working
- Can track active lessons
- Statistics queries optimized

**Dependencies:** Task 1.6

### Task 4.4: Statistics Repository 🟢 P1

**File to Create:** `src/words/repositories/statistics.py`

**Implementation:**
```python
from sqlalchemy import select, and_
from .base import BaseRepository
from src.words.models.statistics import WordStatistics

class StatisticsRepository(BaseRepository[WordStatistics]):
    """Word statistics operations"""

    def __init__(self, session):
        super().__init__(session, WordStatistics)

    async def get_or_create_stat(
        self,
        user_word_id: int,
        direction: str,
        test_type: str
    ) -> WordStatistics:
        """Get existing stat or create new one"""
        result = await self.session.execute(
            select(WordStatistics).where(
                and_(
                    WordStatistics.user_word_id == user_word_id,
                    WordStatistics.direction == direction,
                    WordStatistics.test_type == test_type
                )
            )
        )

        stat = result.scalar_one_or_none()

        if not stat:
            stat = WordStatistics(
                user_word_id=user_word_id,
                direction=direction,
                test_type=test_type
            )
            self.session.add(stat)
            await self.session.flush()

        return stat

    async def update_stat(
        self,
        user_word_id: int,
        direction: str,
        test_type: str,
        is_correct: bool
    ) -> WordStatistics:
        """Update statistics after attempt"""
        stat = await self.get_or_create_stat(
            user_word_id, direction, test_type
        )

        stat.total_attempts += 1

        if is_correct:
            stat.correct_count += 1
            stat.total_correct += 1
        else:
            stat.correct_count = 0  # Reset streak
            stat.total_errors += 1

        await self.session.flush()
        return stat
```

**Acceptance Criteria:**
- Statistics tracking working
- Correct count (streak) calculated
- Total counters accurate

**Dependencies:** Task 1.6

### Task 4.5: Lesson Service (Core) 🔴 P0

**File to Create:** `src/words/services/lesson.py`

**Implementation:**
(This is a long implementation - see next task for full details)

**Key Components:**
- `start_lesson()` - Create lesson, select words
- `generate_question()` - Create question for word
- `process_answer()` - Validate and record answer
- `complete_lesson()` - Finalize and show summary
- Multiple choice option generation

**Acceptance Criteria:**
- Lesson creation working
- Questions generated correctly
- Answers validated and recorded
- Statistics updated
- Lesson completion functional

**Dependencies:** Tasks 4.2, 4.3, 4.4

### Task 4.6: Lesson Service Implementation (Detailed) 🔴 P0

**File:** `src/words/services/lesson.py` (continued)

**Full Implementation:**
```python
from src.words.repositories.lesson import LessonRepository, LessonAttemptRepository
from src.words.repositories.statistics import StatisticsRepository
from src.words.repositories.word import UserWordRepository, WordRepository
from src.words.services.validation import ValidationService, ValidationResult
from src.words.models.lesson import Lesson, LessonAttempt
from src.words.models.word import UserWord, WordStatusEnum
from src.words.config.constants import Direction, TestType
from src.words.utils.logger import logger
from dataclasses import dataclass
from datetime import datetime
import random

@dataclass
class Question:
    """Lesson question"""
    user_word_id: int
    word_id: int
    question_text: str
    expected_answer: str
    alternative_answers: list[str]
    direction: str
    test_type: str
    options: list[str] | None = None  # For multiple choice

@dataclass
class AnswerResult:
    """Answer processing result"""
    is_correct: bool
    validation_method: str
    feedback: str | None
    correct_answer: str

class LessonService:
    """Lesson orchestration and management"""

    def __init__(
        self,
        lesson_repo: LessonRepository,
        attempt_repo: LessonAttemptRepository,
        user_word_repo: UserWordRepository,
        word_repo: WordRepository,
        stats_repo: StatisticsRepository,
        validation_service: ValidationService
    ):
        self.lesson_repo = lesson_repo
        self.attempt_repo = attempt_repo
        self.user_word_repo = user_word_repo
        self.word_repo = word_repo
        self.stats_repo = stats_repo
        self.validation_service = validation_service

    async def get_or_create_active_lesson(
        self,
        profile_id: int,
        words_count: int = 30
    ) -> Lesson:
        """Get active lesson or create new one"""
        # Check for active lesson
        active = await self.lesson_repo.get_active_lesson(profile_id)
        if active:
            return active

        # Create new lesson
        lesson = Lesson(
            profile_id=profile_id,
            words_count=words_count
        )

        lesson = await self.lesson_repo.add(lesson)
        await self.lesson_repo.commit()

        logger.info(
            "lesson_created",
            lesson_id=lesson.lesson_id,
            profile_id=profile_id
        )

        return lesson

    async def generate_next_question(
        self,
        lesson: Lesson,
        selected_words: list[UserWord]
    ) -> Question | None:
        """Generate next question for lesson"""
        # Get already attempted words
        attempts = await self.attempt_repo.get_lesson_attempts(lesson.lesson_id)
        attempted_ids = {a.user_word_id for a in attempts}

        # Find next word
        for user_word in selected_words:
            if user_word.user_word_id not in attempted_ids:
                return await self._create_question(user_word)

        # No more questions
        return None

    async def _create_question(self, user_word: UserWord) -> Question:
        """Create question from user word"""
        # Determine test type
        test_type = self._determine_test_type(user_word)

        # Select direction
        direction = random.choice([
            Direction.NATIVE_TO_FOREIGN,
            Direction.FOREIGN_TO_NATIVE
        ])

        # Build question and answer
        word = user_word.word
        native_lang = user_word.profile.user.native_language

        if direction == Direction.NATIVE_TO_FOREIGN:
            # Translate from native to foreign
            question_text = word.translations[native_lang][0]
            expected_answer = word.word
            alternatives = word.translations[native_lang][1:]
        else:
            # Translate from foreign to native
            question_text = word.word
            expected_answer = word.translations[native_lang][0]
            alternatives = word.translations[native_lang][1:]

        # Generate options for multiple choice
        options = None
        if test_type == TestType.MULTIPLE_CHOICE:
            options = await self._generate_options(
                expected_answer,
                word,
                direction,
                count=4
            )

        return Question(
            user_word_id=user_word.user_word_id,
            word_id=word.word_id,
            question_text=question_text,
            expected_answer=expected_answer,
            alternative_answers=alternatives,
            direction=direction,
            test_type=test_type,
            options=options
        )

    def _determine_test_type(self, user_word: UserWord) -> str:
        """Determine appropriate test type based on word statistics"""
        # Check if word is ready for input testing
        for stat in user_word.statistics:
            if (stat.test_type == TestType.MULTIPLE_CHOICE and
                stat.correct_count >= 3):
                return TestType.INPUT

        return TestType.MULTIPLE_CHOICE

    async def _generate_options(
        self,
        correct_answer: str,
        word: Word,
        direction: str,
        count: int = 4
    ) -> list[str]:
        """Generate answer options for multiple choice"""
        options = [correct_answer]

        # Get similar words from same level
        similar_words = await self.word_repo.get_frequency_words(
            language=word.language,
            level=word.level,
            limit=10
        )

        # Extract answers
        native_lang = "en"  # TODO: Get from context
        for similar_word in similar_words:
            if similar_word.word_id == word.word_id:
                continue

            if direction == Direction.NATIVE_TO_FOREIGN:
                option = similar_word.word
            else:
                option = similar_word.translations.get(native_lang, [""])[0]

            if option and option not in options:
                options.append(option)

            if len(options) >= count:
                break

        # Shuffle
        random.shuffle(options)

        return options[:count]

    async def process_answer(
        self,
        lesson_id: int,
        question: Question,
        user_answer: str
    ) -> AnswerResult:
        """Process user's answer"""
        # Validate answer
        validation = await self.validation_service.validate_answer(
            user_answer=user_answer,
            expected_answer=question.expected_answer,
            alternative_answers=question.alternative_answers,
            word_id=question.word_id,
            direction=question.direction,
            question=question.question_text,
            source_lang="en",  # TODO: Get from context
            target_lang="ru"   # TODO: Get from context
        )

        # Record attempt
        attempt = LessonAttempt(
            lesson_id=lesson_id,
            user_word_id=question.user_word_id,
            direction=question.direction,
            test_type=question.test_type,
            user_answer=user_answer,
            correct_answer=question.expected_answer,
            is_correct=validation.is_correct,
            validation_method=validation.method
        )

        await self.attempt_repo.add(attempt)

        # Update statistics
        await self.stats_repo.update_stat(
            user_word_id=question.user_word_id,
            direction=question.direction,
            test_type=question.test_type,
            is_correct=validation.is_correct
        )

        # Update lesson counters
        lesson = await self.lesson_repo.get_by_id(lesson_id)
        if validation.is_correct:
            lesson.correct_answers += 1
        else:
            lesson.incorrect_answers += 1

        # Update user word
        user_word = await self.user_word_repo.get_by_id(question.user_word_id)
        user_word.last_reviewed_at = datetime.utcnow()

        # Check if word is mastered
        await self._update_word_status(user_word)

        await self.lesson_repo.commit()

        logger.info(
            "answer_processed",
            lesson_id=lesson_id,
            user_word_id=question.user_word_id,
            is_correct=validation.is_correct,
            method=validation.method
        )

        return AnswerResult(
            is_correct=validation.is_correct,
            validation_method=validation.method,
            feedback=validation.feedback,
            correct_answer=question.expected_answer
        )

    async def _update_word_status(self, user_word: UserWord):
        """Update word status based on performance"""
        # Check if mastered (30 correct in a row)
        for stat in user_word.statistics:
            if stat.correct_count >= 30:
                user_word.status = WordStatusEnum.MASTERED
                logger.info(
                    "word_mastered",
                    user_word_id=user_word.user_word_id
                )
                return

        # Update status
        if user_word.status == WordStatusEnum.NEW:
            # Check if any attempts
            if any(s.total_attempts > 0 for s in user_word.statistics):
                user_word.status = WordStatusEnum.LEARNING

        elif user_word.status == WordStatusEnum.LEARNING:
            # Check if ready for reviewing (5+ correct answers)
            if any(s.total_correct >= 5 for s in user_word.statistics):
                user_word.status = WordStatusEnum.REVIEWING

    async def complete_lesson(self, lesson_id: int) -> dict:
        """Complete lesson and return summary"""
        lesson = await self.lesson_repo.get_by_id(lesson_id)
        lesson.completed_at = datetime.utcnow()

        await self.lesson_repo.commit()

        # Calculate duration
        duration = (lesson.completed_at - lesson.started_at).seconds

        logger.info(
            "lesson_completed",
            lesson_id=lesson_id,
            correct=lesson.correct_answers,
            incorrect=lesson.incorrect_answers,
            duration=duration
        )

        return {
            "lesson_id": lesson_id,
            "words_count": lesson.words_count,
            "correct_answers": lesson.correct_answers,
            "incorrect_answers": lesson.incorrect_answers,
            "accuracy": lesson.correct_answers / lesson.words_count * 100,
            "duration_seconds": duration
        }
```

**Acceptance Criteria:**
- Full lesson flow working
- Questions generated based on word status
- Answers validated correctly
- Statistics updated after each attempt
- Word status progresses correctly

**Dependencies:** Tasks 4.2, 4.3, 4.4

**Dependencies:** Task 4.5

---

## Phase 5: Adaptive Algorithm

**Goal:** Implement word selection algorithm, spaced repetition, and difficulty adjustment

**Duration:** 3-4 days

### Task 5.1: Spaced Repetition Algorithm 🟡 P0

**File to Create:** `src/words/algorithm/spaced_repetition.py`

**Implementation:**
```python
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class SpacedRepetitionResult:
    """Result of spaced repetition calculation"""
    next_interval_days: int
    next_review_at: datetime
    easiness_factor: float

class SpacedRepetition:
    """
    SM-2 Spaced Repetition Algorithm

    Based on SuperMemo 2 algorithm
    https://www.supermemo.com/en/archives1990-2015/english/ol/sm2
    """

    MIN_EASINESS_FACTOR = 1.3
    DEFAULT_EASINESS_FACTOR = 2.5

    def calculate_next_review(
        self,
        current_interval_days: int,
        easiness_factor: float,
        is_correct: bool,
        quality: int = 3  # 0-5 scale (3 = barely correct)
    ) -> SpacedRepetitionResult:
        """
        Calculate next review interval and updated easiness factor

        Args:
            current_interval_days: Current interval in days (0 for new words)
            easiness_factor: Current easiness factor (2.5 default)
            is_correct: Whether answer was correct
            quality: Quality of recall (0-5, where 3+ is correct)

        Returns:
            SpacedRepetitionResult with next interval and EF
        """

        if not is_correct or quality < 3:
            # Reset on error
            next_interval = 1
            new_ef = max(
                self.MIN_EASINESS_FACTOR,
                easiness_factor - 0.2
            )
        else:
            # Update easiness factor
            new_ef = self._calculate_new_ef(easiness_factor, quality)

            # Calculate next interval
            if current_interval_days == 0:
                next_interval = 1
            elif current_interval_days == 1:
                next_interval = 6
            else:
                next_interval = int(current_interval_days * new_ef)

        next_review_at = datetime.utcnow() + timedelta(days=next_interval)

        return SpacedRepetitionResult(
            next_interval_days=next_interval,
            next_review_at=next_review_at,
            easiness_factor=new_ef
        )

    def _calculate_new_ef(self, current_ef: float, quality: int) -> float:
        """
        Calculate new easiness factor

        Formula: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        """
        new_ef = current_ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

        return max(self.MIN_EASINESS_FACTOR, new_ef)

    def quality_from_correctness(
        self,
        is_correct: bool,
        validation_method: str
    ) -> int:
        """
        Convert validation result to quality score (0-5)

        - Exact match: 5
        - Fuzzy match (typo): 4
        - LLM accepted: 3
        - Wrong: 0
        """
        if not is_correct:
            return 0

        if validation_method == "exact":
            return 5
        elif validation_method == "fuzzy":
            return 4
        elif validation_method == "llm":
            return 3
        else:
            return 3  # Default for correct answers

async def update_review_schedule(
    user_word,
    is_correct: bool,
    validation_method: str,
    sr_algorithm: SpacedRepetition = None
):
    """
    Update user word review schedule after attempt

    Args:
        user_word: UserWord instance
        is_correct: Whether answer was correct
        validation_method: Method used for validation
        sr_algorithm: Optional custom SR algorithm
    """
    if sr_algorithm is None:
        sr_algorithm = SpacedRepetition()

    current_interval = user_word.review_interval or 0
    ef = user_word.easiness_factor or SpacedRepetition.DEFAULT_EASINESS_FACTOR
    quality = sr_algorithm.quality_from_correctness(is_correct, validation_method)

    result = sr_algorithm.calculate_next_review(
        current_interval_days=current_interval,
        easiness_factor=ef,
        is_correct=is_correct,
        quality=quality
    )

    user_word.review_interval = result.next_interval_days
    user_word.easiness_factor = result.easiness_factor
    user_word.next_review_at = result.next_review_at
```

**Acceptance Criteria:**
- SM-2 algorithm implemented correctly
- Next review intervals calculated
- Easiness factor adjusts properly
- Errors reset interval to 1 day

**Dependencies:** Task 1.5

### Task 5.2: Word Selector Algorithm 🔴 P0

**File to Create:** `src/words/algorithm/word_selector.py`

**Implementation:**
```python
from src.words.models.word import UserWord, WordStatusEnum
from src.words.config.constants import TestType
from datetime import datetime
from dataclasses import dataclass
import random

@dataclass
class ScoredWord:
    """Word with calculated priority score"""
    user_word: UserWord
    priority_score: float

class WordSelector:
    """
    Adaptive word selection algorithm

    Selects words for lessons based on:
    - Spaced repetition (due for review)
    - Error rate (struggling words)
    - Word status (new, learning, reviewing)
    - Test type readiness (multiple choice → input)
    """

    def __init__(
        self,
        words_per_lesson: int = 30,
        input_ratio: float = 0.5
    ):
        self.words_per_lesson = words_per_lesson
        self.input_ratio = input_ratio

    async def select_words_for_lesson(
        self,
        candidate_words: list[UserWord]
    ) -> list[UserWord]:
        """
        Select words for lesson using adaptive algorithm

        Args:
            candidate_words: All available words (excluding mastered)

        Returns:
            Selected words sorted by priority
        """

        # Calculate priority scores
        scored_words = [
            ScoredWord(word, self._calculate_priority(word))
            for word in candidate_words
        ]

        # Sort by priority (highest first)
        scored_words.sort(key=lambda x: x.priority_score, reverse=True)

        # Separate input-ready and choice words
        input_ready = [
            sw.user_word for sw in scored_words
            if self._is_input_ready(sw.user_word)
        ]
        choice_words = [
            sw.user_word for sw in scored_words
            if not self._is_input_ready(sw.user_word)
        ]

        # Build selection
        selected = []

        # Add input-ready words (up to input_ratio of lesson)
        input_target = int(self.words_per_lesson * self.input_ratio)
        selected.extend(input_ready[:input_target])

        # Fill remaining with choice words
        remaining = self.words_per_lesson - len(selected)
        selected.extend(choice_words[:remaining])

        # If not enough, add more input words
        if len(selected) < self.words_per_lesson:
            additional = self.words_per_lesson - len(selected)
            selected.extend(input_ready[input_target:input_target + additional])

        return selected[:self.words_per_lesson]

    def _calculate_priority(self, user_word: UserWord) -> float:
        """
        Calculate priority score for word

        Higher score = higher priority = should be shown sooner

        Factors:
        - Overdue for review (spaced repetition)
        - High error rate
        - New words (need introduction)
        - Time since last review
        """
        score = 0.0

        # Factor 1: Due for review (spaced repetition) - HIGH PRIORITY
        if user_word.next_review_at:
            days_overdue = (datetime.utcnow() - user_word.next_review_at).days
            if days_overdue > 0:
                score += days_overdue * 10  # 10 points per day overdue

        # Factor 2: Error rate - MEDIUM PRIORITY
        error_rate = self._calculate_error_rate(user_word)
        score += error_rate * 5  # Up to 5 points for high error rate

        # Factor 3: New words - HIGH PRIORITY
        if user_word.status == WordStatusEnum.NEW:
            score += 15

        # Factor 4: Time since last review - LOW PRIORITY
        if user_word.last_reviewed_at:
            days_since = (datetime.utcnow() - user_word.last_reviewed_at).days
            score += min(days_since, 7)  # Cap at 7 days
        else:
            score += 7  # Never reviewed

        # Factor 5: Word status progression
        if user_word.status == WordStatusEnum.LEARNING:
            score += 3  # Moderate priority
        elif user_word.status == WordStatusEnum.REVIEWING:
            score += 1  # Lower priority

        return score

    def _calculate_error_rate(self, user_word: UserWord) -> float:
        """
        Calculate error rate for word (0.0 - 1.0)

        Considers all statistics across directions and test types
        """
        if not user_word.statistics:
            return 0.0

        total_attempts = sum(s.total_attempts for s in user_word.statistics)
        total_errors = sum(s.total_errors for s in user_word.statistics)

        if total_attempts == 0:
            return 0.0

        return total_errors / total_attempts

    def _is_input_ready(self, user_word: UserWord) -> bool:
        """
        Check if word is ready for input-type testing

        Criteria: 3+ consecutive correct answers in multiple choice
        """
        for stat in user_word.statistics:
            if (stat.test_type == TestType.MULTIPLE_CHOICE and
                stat.correct_count >= 3):
                return True

        return False
```

**Acceptance Criteria:**
- Word selection prioritizes overdue words
- New words get high priority
- Error-prone words selected more often
- Input/choice ratio maintained
- Words sorted by priority

**Dependencies:** Task 1.5

### Task 5.3: Difficulty Adjuster 🟢 P1

**File to Create:** `src/words/algorithm/difficulty.py`

**Implementation:**
```python
from src.words.models.word import UserWord, WordStatusEnum
from src.words.config.constants import TestType
from src.words.utils.logger import logger

class DifficultyAdjuster:
    """
    Manages word difficulty progression

    Controls:
    - Test type progression (multiple choice → input)
    - Word status transitions
    - Mastery detection
    """

    def __init__(
        self,
        choice_to_input_threshold: int = 3,
        mastered_threshold: int = 30
    ):
        self.choice_to_input_threshold = choice_to_input_threshold
        self.mastered_threshold = mastered_threshold

    def determine_test_type(self, user_word: UserWord) -> str:
        """
        Determine appropriate test type for word

        Returns: TestType.MULTIPLE_CHOICE or TestType.INPUT
        """
        stats = self._get_choice_stats(user_word)

        if stats and stats.correct_count >= self.choice_to_input_threshold:
            return TestType.INPUT
        else:
            return TestType.MULTIPLE_CHOICE

    def should_update_status(self, user_word: UserWord) -> bool:
        """Check if word status should be updated"""
        # Check for mastery
        if self._is_mastered(user_word):
            return True

        # Check for status progression
        if user_word.status == WordStatusEnum.NEW:
            # Has any attempts?
            return any(s.total_attempts > 0 for s in user_word.statistics)

        elif user_word.status == WordStatusEnum.LEARNING:
            # Ready for reviewing? (5+ correct answers)
            return any(s.total_correct >= 5 for s in user_word.statistics)

        return False

    def update_word_status(self, user_word: UserWord) -> str:
        """
        Update word status based on performance

        Returns: New status
        """
        old_status = user_word.status

        # Check mastery first
        if self._is_mastered(user_word):
            user_word.status = WordStatusEnum.MASTERED
            logger.info(
                "word_status_updated",
                user_word_id=user_word.user_word_id,
                old_status=old_status.value,
                new_status="mastered"
            )
            return user_word.status.value

        # Progress through statuses
        if user_word.status == WordStatusEnum.NEW:
            if any(s.total_attempts > 0 for s in user_word.statistics):
                user_word.status = WordStatusEnum.LEARNING

        elif user_word.status == WordStatusEnum.LEARNING:
            if any(s.total_correct >= 5 for s in user_word.statistics):
                user_word.status = WordStatusEnum.REVIEWING

        if old_status != user_word.status:
            logger.info(
                "word_status_updated",
                user_word_id=user_word.user_word_id,
                old_status=old_status.value,
                new_status=user_word.status.value
            )

        return user_word.status.value

    def _is_mastered(self, user_word: UserWord) -> bool:
        """
        Check if word is mastered

        Criteria: 30+ consecutive correct answers in ANY direction/test_type
        """
        for stat in user_word.statistics:
            if stat.correct_count >= self.mastered_threshold:
                return True

        return False

    def _get_choice_stats(self, user_word: UserWord):
        """Get multiple choice statistics for word"""
        for stat in user_word.statistics:
            if stat.test_type == TestType.MULTIPLE_CHOICE:
                return stat

        return None
```

**Acceptance Criteria:**
- Test type progression working
- Status transitions correct
- Mastery detection accurate
- Logging of status changes

**Dependencies:** Task 1.5

### Task 5.4: Integrate Algorithm into Lesson Service 🟡 P0

**File to Modify:** `src/words/services/lesson.py`

**Changes:**
1. Add word selection using `WordSelector`
2. Integrate spaced repetition updates
3. Use `DifficultyAdjuster` for test type determination

**New Methods to Add:**
```python
async def get_words_for_lesson(
    self,
    profile_id: int,
    count: int = 30
) -> list[UserWord]:
    """
    Get words for lesson using adaptive selection

    Uses WordSelector algorithm
    """
    # Get candidate words (not mastered)
    candidates = await self.user_word_repo.get_user_vocabulary(
        profile_id=profile_id,
        status=None  # All non-mastered
    )

    # Filter out mastered
    candidates = [
        w for w in candidates
        if w.status != WordStatusEnum.MASTERED
    ]

    # Select using algorithm
    from src.words.algorithm.word_selector import WordSelector

    selector = WordSelector(words_per_lesson=count)
    selected = await selector.select_words_for_lesson(candidates)

    return selected

# Update process_answer to use spaced repetition
async def process_answer(self, lesson_id, question, user_answer):
    # ... existing validation code ...

    # Update spaced repetition schedule
    from src.words.algorithm.spaced_repetition import update_review_schedule

    user_word = await self.user_word_repo.get_by_id(question.user_word_id)
    await update_review_schedule(
        user_word,
        validation.is_correct,
        validation.method
    )

    # ... rest of existing code ...
```

**Acceptance Criteria:**
- Lesson service uses word selector
- Spaced repetition integrated
- Difficulty adjuster used for test types
- All algorithm components working together

**Dependencies:** Tasks 5.1, 5.2, 5.3, Task 4.5

### Task 5.5: Lesson Handler 🔴 P0

**File to Create:** `src/words/bot/handlers/lesson.py`

**Implementation:**
```python
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from src.words.bot.states.registration import LessonStates
from src.words.bot.keyboards.common import build_main_menu
from src.words.services.lesson import LessonService
from src.words.services.validation import ValidationService
from src.words.services.translation import TranslationService
from src.words.repositories.lesson import LessonRepository, LessonAttemptRepository
from src.words.repositories.statistics import StatisticsRepository
from src.words.repositories.word import UserWordRepository, WordRepository
from src.words.repositories.user import ProfileRepository
from src.words.repositories.cache import CacheRepository
from src.words.infrastructure.llm_client import LLMClient
from src.words.infrastructure.database import get_session
from src.words.config.settings import settings
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router(name="lesson")

@router.message(F.text == "📚 Start Lesson")
async def cmd_start_lesson(message: Message, state: FSMContext):
    """Start new lesson"""
    user_id = message.from_user.id

    processing_msg = await message.answer("🔄 Preparing your lesson...")

    try:
        async with get_session() as session:
            # Get active profile
            profile_repo = ProfileRepository(session)
            profile = await profile_repo.get_active_profile(user_id)

            if not profile:
                await message.answer("Please complete registration first using /start")
                return

            # Setup services
            llm_client = LLMClient(settings.llm_api_key, settings.llm_model)
            cache_repo = CacheRepository(session)
            translation_service = TranslationService(llm_client, cache_repo)
            validation_service = ValidationService(translation_service)

            lesson_service = LessonService(
                LessonRepository(session),
                LessonAttemptRepository(session),
                UserWordRepository(session),
                WordRepository(session),
                StatisticsRepository(session),
                validation_service
            )

            # Get or create lesson
            lesson = await lesson_service.get_or_create_active_lesson(
                profile_id=profile.profile_id,
                words_count=settings.words_per_lesson
            )

            # Get words for lesson
            selected_words = await lesson_service.get_words_for_lesson(
                profile_id=profile.profile_id,
                count=settings.words_per_lesson
            )

            if not selected_words:
                await processing_msg.delete()
                await message.answer(
                    "You don't have any words to practice!\n"
                    "Add some words first using ➕ Add Word",
                    reply_markup=build_main_menu()
                )
                return

            # Generate first question
            question = await lesson_service.generate_next_question(
                lesson, selected_words
            )

            # Store in state
            await state.update_data(
                lesson_id=lesson.lesson_id,
                selected_words=[w.user_word_id for w in selected_words],
                current_question=question.__dict__
            )

            await processing_msg.delete()

            # Send question
            await send_question(message, question, state)

            await state.set_state(LessonStates.answering_question)

    except Exception as e:
        logger.error("start_lesson_failed", error=str(e))
        await processing_msg.delete()
        await message.answer("❌ Failed to start lesson. Please try again.")

async def send_question(message: Message, question, state: FSMContext):
    """Send question to user"""
    from src.words.config.constants import TestType

    if question.test_type == TestType.MULTIPLE_CHOICE:
        # Multiple choice - send options
        builder = InlineKeyboardBuilder()

        for i, option in enumerate(question.options):
            builder.button(
                text=option,
                callback_data=f"answer:{i}:{option}"
            )

        builder.adjust(1)  # One button per row

        await message.answer(
            f"❓ <b>Question:</b> {question.question_text}\n\n"
            "Choose the correct translation:",
            reply_markup=builder.as_markup()
        )
    else:
        # Input - ask for text
        await message.answer(
            f"❓ <b>Question:</b> {question.question_text}\n\n"
            "Type your answer:"
        )

@router.callback_query(
    StateFilter(LessonStates.answering_question),
    F.data.startswith("answer:")
)
async def process_multiple_choice_answer(
    callback: CallbackQuery,
    state: FSMContext
):
    """Process multiple choice answer"""
    # Extract answer
    _, index, answer = callback.data.split(":", 2)

    await process_answer(callback.message, answer, state, callback)

@router.message(StateFilter(LessonStates.answering_question))
async def process_input_answer(message: Message, state: FSMContext):
    """Process text input answer"""
    answer = message.text.strip()

    await process_answer(message, answer, state)

async def process_answer(message, answer: str, state: FSMContext, callback=None):
    """Process answer and show result"""
    data = await state.get_data()
    lesson_id = data["lesson_id"]
    question_dict = data["current_question"]

    # Reconstruct question
    from src.words.services.lesson import Question
    question = Question(**question_dict)

    processing_msg = await message.answer("⏳ Checking your answer...")

    try:
        async with get_session() as session:
            # Setup services
            llm_client = LLMClient(settings.llm_api_key, settings.llm_model)
            cache_repo = CacheRepository(session)
            translation_service = TranslationService(llm_client, cache_repo)
            validation_service = ValidationService(translation_service)

            lesson_service = LessonService(
                LessonRepository(session),
                LessonAttemptRepository(session),
                UserWordRepository(session),
                WordRepository(session),
                StatisticsRepository(session),
                validation_service
            )

            # Process answer
            result = await lesson_service.process_answer(
                lesson_id=lesson_id,
                question=question,
                user_answer=answer
            )

            # Show result
            await processing_msg.delete()

            if result.is_correct:
                result_text = f"✅ <b>Correct!</b>"
                if result.feedback:
                    result_text += f"\n\n{result.feedback}"
            else:
                result_text = (
                    f"❌ <b>Incorrect</b>\n\n"
                    f"Your answer: {answer}\n"
                    f"Correct answer: {result.correct_answer}"
                )
                if result.feedback:
                    result_text += f"\n\n{result.feedback}"

            # Get lesson
            lesson = await lesson_service.lesson_repo.get_by_id(lesson_id)
            selected_word_ids = data["selected_words"]
            selected_words = []
            for word_id in selected_word_ids:
                word = await lesson_service.user_word_repo.get_by_id(word_id)
                selected_words.append(word)

            # Check if lesson complete
            attempts = await lesson_service.attempt_repo.get_lesson_attempts(lesson_id)

            if len(attempts) >= len(selected_words):
                # Lesson complete
                summary = await lesson_service.complete_lesson(lesson_id)

                await message.answer(result_text)
                await message.answer(
                    f"🎉 <b>Lesson Complete!</b>\n\n"
                    f"Words practiced: {summary['words_count']}\n"
                    f"✅ Correct: {summary['correct_answers']}\n"
                    f"❌ Incorrect: {summary['incorrect_answers']}\n"
                    f"📊 Accuracy: {summary['accuracy']:.1f}%\n"
                    f"⏱ Duration: {summary['duration_seconds']}s",
                    reply_markup=build_main_menu()
                )

                await state.clear()
            else:
                # Continue lesson
                next_question = await lesson_service.generate_next_question(
                    lesson, selected_words
                )

                if next_question:
                    await state.update_data(
                        current_question=next_question.__dict__
                    )

                    await message.answer(result_text)
                    await send_question(message, next_question, state)

    except Exception as e:
        logger.error("process_answer_failed", error=str(e))
        await processing_msg.delete()
        await message.answer("❌ Error processing answer. Please try again.")

    if callback:
        await callback.answer()
```

**Acceptance Criteria:**
- Lesson flow works end-to-end
- Multiple choice and input questions
- Answer validation working
- Progress tracked
- Lesson completion shows summary

**Dependencies:** Tasks 5.4, 4.5, 4.2

---

## Phase 6: Notifications & Polish

**Goal:** Implement push notifications, statistics display, settings management

**Duration:** 2-3 days

### Task 6.1: Notification Service 🟡 P1

**File to Create:** `src/words/services/notification.py`

**Implementation:**
```python
from src.words.repositories.user import UserRepository
from src.words.utils.logger import logger
from aiogram import Bot
from datetime import datetime
import pytz

class NotificationService:
    """Push notification management"""

    def __init__(
        self,
        user_repo: UserRepository,
        bot: Bot,
        inactive_hours: int = 6,
        time_start: str = "07:00",
        time_end: str = "23:00",
        timezone: str = "Europe/Moscow"
    ):
        self.user_repo = user_repo
        self.bot = bot
        self.inactive_hours = inactive_hours
        self.time_start = time_start
        self.time_end = time_end
        self.timezone = pytz.timezone(timezone)

    async def check_and_send_notifications(self):
        """
        Check users and send notifications

        Called by scheduler every 15 minutes
        """
        # Get current time in configured timezone
        now = datetime.now(self.timezone)
        current_hour = now.hour
        current_minute = now.minute

        # Check if within notification window
        start_hour = int(self.time_start.split(":")[0])
        end_hour = int(self.time_end.split(":")[0])

        if not (start_hour <= current_hour < end_hour):
            logger.debug(
                "notification_outside_window",
                current_hour=current_hour,
                window=f"{start_hour}-{end_hour}"
            )
            return

        # Get users needing notifications
        users = await self.user_repo.get_users_for_notification(
            inactive_hours=self.inactive_hours,
            current_hour=current_hour
        )

        logger.info(
            "notification_check",
            users_count=len(users),
            current_hour=current_hour
        )

        # Send notifications
        sent_count = 0
        for user in users:
            try:
                await self._send_reminder(user.user_id)
                sent_count += 1
            except Exception as e:
                logger.error(
                    "notification_send_failed",
                    user_id=user.user_id,
                    error=str(e)
                )

        logger.info("notifications_sent", count=sent_count)

    async def _send_reminder(self, user_id: int):
        """Send reminder notification to user"""
        await self.bot.send_message(
            chat_id=user_id,
            text=(
                "👋 Time to practice!\n\n"
                "Keep your learning streak going.\n"
                "Start a lesson now? 📚"
            )
        )

        logger.info("notification_sent", user_id=user_id)
```

**Acceptance Criteria:**
- Notifications sent within time window
- Inactive users detected correctly
- Error handling for failed sends
- Logging of notification activity

**Dependencies:** Task 2.2

### Task 6.2: Scheduler Setup 🟡 P1

**File to Create:** `src/words/infrastructure/scheduler.py`

**Implementation:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from src.words.services.notification import NotificationService
from src.words.repositories.user import UserRepository
from src.words.infrastructure.database import get_session
from src.words.utils.logger import logger
from aiogram import Bot

class NotificationScheduler:
    """APScheduler setup for notifications"""

    def __init__(self, bot: Bot, settings):
        self.bot = bot
        self.settings = settings
        self.scheduler = AsyncIOScheduler()

    def setup(self):
        """Setup scheduled tasks"""
        # Notification task - every 15 minutes
        self.scheduler.add_job(
            self._send_notifications,
            trigger=IntervalTrigger(minutes=15),
            id="send_notifications",
            name="Send push notifications",
            replace_existing=True
        )

        logger.info("Scheduler configured")

    def start(self):
        """Start scheduler"""
        self.scheduler.start()
        logger.info("Scheduler started")

    def shutdown(self):
        """Stop scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    async def _send_notifications(self):
        """Notification job"""
        try:
            async with get_session() as session:
                notification_service = NotificationService(
                    user_repo=UserRepository(session),
                    bot=self.bot,
                    inactive_hours=self.settings.notification_interval_hours,
                    time_start=self.settings.notification_time_start,
                    time_end=self.settings.notification_time_end,
                    timezone=self.settings.timezone
                )

                await notification_service.check_and_send_notifications()

        except Exception as e:
            logger.error("notification_job_failed", error=str(e))
```

**Acceptance Criteria:**
- Scheduler starts with bot
- Notifications run every 15 minutes
- Errors don't crash scheduler
- Graceful shutdown

**Dependencies:** Task 6.1

### Task 6.3: Statistics Handler 🟢 P1

**File to Create:** `src/words/bot/handlers/stats.py`

**Implementation:**
```python
from aiogram import Router, F
from aiogram.types import Message
from src.words.services.word import WordService
from src.words.services.user import UserService
from src.words.repositories.word import WordRepository, UserWordRepository
from src.words.repositories.user import UserRepository, ProfileRepository
from src.words.repositories.lesson import LessonRepository
from src.words.repositories.cache import CacheRepository
from src.words.services.translation import TranslationService
from src.words.infrastructure.llm_client import LLMClient
from src.words.infrastructure.database import get_session
from src.words.config.settings import settings

router = Router(name="stats")

@router.message(F.text == "📊 Statistics")
async def cmd_statistics(message: Message):
    """Show user statistics"""
    user_id = message.from_user.id

    try:
        async with get_session() as session:
            # Get profile
            profile_repo = ProfileRepository(session)
            profile = await profile_repo.get_active_profile(user_id)

            if not profile:
                await message.answer("Please complete registration first using /start")
                return

            # Get vocabulary stats
            llm_client = LLMClient(settings.llm_api_key, settings.llm_model)
            cache_repo = CacheRepository(session)
            translation_service = TranslationService(llm_client, cache_repo)

            word_service = WordService(
                WordRepository(session),
                UserWordRepository(session),
                translation_service
            )

            vocab_stats = await word_service.get_user_vocabulary_stats(
                profile_id=profile.profile_id
            )

            # Get lesson stats
            lesson_repo = LessonRepository(session)
            recent_lessons = await lesson_repo.get_recent_lessons(
                profile_id=profile.profile_id,
                limit=10
            )
            lessons_today = await lesson_repo.count_lessons_today(
                profile_id=profile.profile_id
            )

            # Format message
            stats_text = (
                "📊 <b>Your Statistics</b>\n\n"
                f"<b>Vocabulary</b>\n"
                f"📚 Total words: {vocab_stats['total']}\n"
                f"🆕 New: {vocab_stats['new']}\n"
                f"📖 Learning: {vocab_stats['learning']}\n"
                f"🔄 Reviewing: {vocab_stats['reviewing']}\n"
                f"✅ Mastered: {vocab_stats['mastered']}\n\n"
                f"<b>Lessons</b>\n"
                f"📅 Today: {lessons_today}\n"
                f"📈 Total completed: {len(recent_lessons)}\n"
            )

            if recent_lessons:
                last_lesson = recent_lessons[0]
                accuracy = (last_lesson.correct_answers / last_lesson.words_count * 100)
                stats_text += (
                    f"\n<b>Last Lesson</b>\n"
                    f"✅ Correct: {last_lesson.correct_answers}/{last_lesson.words_count}\n"
                    f"📊 Accuracy: {accuracy:.1f}%"
                )

            await message.answer(stats_text)

    except Exception as e:
        logger.error("statistics_failed", error=str(e))
        await message.answer("❌ Failed to load statistics.")
```

**Acceptance Criteria:**
- Shows vocabulary breakdown
- Displays lesson statistics
- Formatted nicely
- Error handling

**Dependencies:** Task 3.5, Task 4.3

### Task 6.4: Settings Handler 🟢 P2

**File to Create:** `src/words/bot/handlers/settings.py`

**Implementation:**
```python
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.words.services.user import UserService
from src.words.repositories.user import UserRepository, ProfileRepository
from src.words.infrastructure.database import get_session
from src.words.config.constants import SUPPORTED_LANGUAGES, CEFR_LEVELS

router = Router(name="settings")

@router.message(F.text == "⚙️ Settings")
async def cmd_settings(message: Message):
    """Show settings menu"""
    builder = InlineKeyboardBuilder()

    builder.button(text="🔔 Notifications", callback_data="settings:notifications")
    builder.button(text="🌍 Change Language", callback_data="settings:language")
    builder.button(text="📊 Change Level", callback_data="settings:level")

    builder.adjust(1)

    await message.answer(
        "⚙️ <b>Settings</b>\n\n"
        "What would you like to change?",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "settings:notifications")
async def toggle_notifications(callback: CallbackQuery):
    """Toggle notifications on/off"""
    user_id = callback.from_user.id

    async with get_session() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(user_id)

        if user:
            user.notification_enabled = not user.notification_enabled
            await user_repo.commit()

            status = "enabled" if user.notification_enabled else "disabled"
            await callback.message.edit_text(
                f"🔔 Notifications {status}!"
            )

        await callback.answer()

# ... additional settings handlers ...
```

**Acceptance Criteria:**
- Settings menu functional
- Notification toggle working
- Language/level changes possible

**Dependencies:** Task 2.3

### Task 6.5: Update Main Bot with Scheduler 🟡 P1

**File to Modify:** `src/words/__main__.py`

**Add scheduler initialization:**
```python
from src.words.infrastructure.scheduler import NotificationScheduler

async def main():
    logger.info("Starting bot...")

    await init_db()
    bot, dp = await setup_bot()

    # Setup scheduler
    scheduler = NotificationScheduler(bot, settings)
    scheduler.setup()
    scheduler.start()

    try:
        logger.info("Bot is running. Press Ctrl+C to stop.")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()
        await close_db()
        logger.info("Bot stopped")
```

**Acceptance Criteria:**
- Scheduler starts with bot
- Notifications sent automatically
- Graceful shutdown

**Dependencies:** Task 6.2

---

## Phase 7: Testing & Deployment

**Goal:** Write tests, prepare for deployment, create documentation

**Duration:** 3-4 days

### Task 7.1: Unit Tests - Services 🟡 P1

**Files to Create:**
- `tests/unit/test_validation_service.py`
- `tests/unit/test_word_selector.py`
- `tests/unit/test_spaced_repetition.py`

**Example:** `test_validation_service.py`
```python
import pytest
from src.words.services.validation import ValidationService, ValidationResult
from src.words.config.constants import ValidationMethod

@pytest.mark.asyncio
async def test_exact_match():
    """Test exact match validation"""
    validation_service = ValidationService(None)

    result = await validation_service.validate_answer(
        user_answer="house",
        expected_answer="house",
        alternative_answers=[]
    )

    assert result.is_correct
    assert result.method == ValidationMethod.EXACT

@pytest.mark.asyncio
async def test_fuzzy_match_typo():
    """Test fuzzy matching with typo"""
    validation_service = ValidationService(None)

    result = await validation_service.validate_answer(
        user_answer="hous",  # Missing 'e'
        expected_answer="house",
        alternative_answers=[]
    )

    assert result.is_correct
    assert result.method == ValidationMethod.FUZZY
    assert "typo" in result.feedback.lower()

# ... more tests ...
```

**Acceptance Criteria:**
- Core services tested
- Edge cases covered
- 80%+ code coverage

**Dependencies:** Tasks 4.2, 5.1, 5.2

### Task 7.2: Integration Tests 🟡 P2

**Files to Create:**
- `tests/integration/test_lesson_flow.py`
- `tests/integration/test_word_addition.py`

**Example:** `test_lesson_flow.py`
```python
import pytest
from src.words.services.lesson import LessonService
from src.words.models.lesson import Lesson

@pytest.mark.asyncio
async def test_complete_lesson_flow(
    session,
    sample_profile,
    sample_words
):
    """Test full lesson flow"""
    # Setup
    lesson_service = create_lesson_service(session)

    # Start lesson
    lesson = await lesson_service.get_or_create_active_lesson(
        profile_id=sample_profile.profile_id,
        words_count=5
    )

    assert lesson.lesson_id is not None
    assert lesson.completed_at is None

    # ... complete lesson flow ...

    # Verify completion
    summary = await lesson_service.complete_lesson(lesson.lesson_id)
    assert summary["words_count"] == 5
```

**Acceptance Criteria:**
- End-to-end flows tested
- Database interactions verified
- Async operations handled

**Dependencies:** Task 7.1

### Task 7.3: Load Frequency Lists 🟡 P1

**File to Create:** `scripts/load_frequency_lists.py`

**Implementation:**
```python
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.words.infrastructure.database import get_session
from src.words.repositories.word import WordRepository
from src.words.models.word import Word
from src.words.utils.logger import logger

async def load_frequency_list(file_path: Path, language: str, level: str):
    """Load frequency list from JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        words_data = json.load(f)

    async with get_session() as session:
        word_repo = WordRepository(session)

        for rank, word_data in enumerate(words_data, 1):
            word = Word(
                word=word_data['word'].lower(),
                language=language,
                level=level,
                frequency_rank=rank,
                translations=word_data.get('translations', {}),
                examples=word_data.get('examples', []),
                word_forms=word_data.get('word_forms', {})
            )

            # Check if exists
            existing = await word_repo.find_by_text_and_language(
                word.word, language
            )

            if not existing:
                await word_repo.add(word)

        await word_repo.commit()
        logger.info(f"Loaded {len(words_data)} words for {language}/{level}")

async def main():
    """Load all frequency lists"""
    data_dir = Path(__file__).parent.parent / "data" / "frequency_lists"

    # Define files to load
    files_to_load = [
        ("english_a1.json", "en", "A1"),
        ("english_a2.json", "en", "A2"),
        ("spanish_a1.json", "es", "A1"),
        # Add more files...
    ]

    for filename, language, level in files_to_load:
        file_path = data_dir / filename
        if file_path.exists():
            await load_frequency_list(file_path, language, level)
        else:
            logger.warning(f"File not found: {file_path}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Acceptance Criteria:**
- Frequency lists loaded to database
- No duplicates created
- Proper error handling

**Dependencies:** Task 1.5

### Task 7.4: Deployment Documentation 🟢 P1

**File to Create:** `docs/deployment.md`

**Contents:**
- Environment setup instructions
- Database initialization
- Configuration guide
- Systemd service file
- Backup procedures
- Monitoring setup

**Acceptance Criteria:**
- Clear deployment steps
- Examples provided
- Troubleshooting section

**Dependencies:** None

### Task 7.5: README Update 🟢 P1

**File to Update:** `README.md`

**Contents:**
- Project overview
- Features list
- Installation instructions
- Usage guide
- Development setup
- Contributing guidelines
- License

**Acceptance Criteria:**
- Complete and accurate
- Examples included
- Links to docs

**Dependencies:** None

### Task 7.6: Systemd Service Setup 🟢 P2

**File to Create:** `systemd/words-bot.service`

**Implementation:**
```ini
[Unit]
Description=Words Language Learning Telegram Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/opt/projects/words
Environment="PATH=/opt/projects/words/venv/bin"
ExecStart=/opt/projects/words/venv/bin/python -m src.words
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Acceptance Criteria:**
- Service starts on boot
- Auto-restarts on failure
- Logs to systemd journal

**Dependencies:** Task 2.7

---

## Task Dependencies

### Critical Path (Must Complete in Order)

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7
```

### Detailed Dependencies

**Phase 1 Dependencies:**
- 1.1 → 1.2 → 1.3 → 1.4, 1.5, 1.6, 1.7 → 1.9

**Phase 2 Dependencies:**
- 2.1 → 2.2 → 2.3
- 2.4, 2.5 (parallel)
- 2.6 requires 2.3, 2.4, 2.5
- 2.7 requires 2.6

**Phase 3 Dependencies:**
- 3.1, 3.2 (parallel)
- 3.3 requires 3.1, 3.2
- 3.4 → 3.5 requires 3.3, 3.4
- 3.6 requires 3.5

**Phase 4 Dependencies:**
- 4.1 (standalone)
- 4.2 requires 3.3, 4.1
- 4.3, 4.4 (parallel)
- 4.5 requires 4.2, 4.3, 4.4
- 4.6 same as 4.5 (detailed implementation)

**Phase 5 Dependencies:**
- 5.1, 5.2, 5.3 (parallel)
- 5.4 requires 5.1, 5.2, 5.3, 4.5
- 5.5 requires 5.4

**Phase 6 Dependencies:**
- 6.1 → 6.2
- 6.3, 6.4 (parallel, require Phase 3)
- 6.5 requires 6.2

**Phase 7 Dependencies:**
- 7.1, 7.2, 7.3 (parallel)
- 7.4, 7.5, 7.6 (parallel)

---

## Timeline Estimates

### Detailed Breakdown

**Phase 0: Project Setup**
- Total: 1 day
- Can be completed quickly by experienced developer

**Phase 1: Core Infrastructure**
- Task 1.1: 1 hour
- Task 1.2: 2 hours
- Task 1.3: 1 hour
- Task 1.4: 3 hours
- Task 1.5: 3 hours
- Task 1.6: 3 hours
- Task 1.7: 2 hours
- Task 1.8: 1 hour
- Task 1.9: 1 hour
- **Total: 17 hours (2-3 days)**

**Phase 2: User Management**
- Task 2.1: 1 hour
- Task 2.2: 3 hours
- Task 2.3: 3 hours
- Task 2.4: 1 hour
- Task 2.5: 2 hours
- Task 2.6: 4 hours
- Task 2.7: 2 hours
- **Total: 16 hours (2 days)**

**Phase 3: Word Management**
- Task 3.1: 4 hours
- Task 3.2: 3 hours
- Task 3.3: 3 hours
- Task 3.4: 3 hours
- Task 3.5: 6 hours
- Task 3.6: 4 hours
- **Total: 23 hours (3-4 days)**

**Phase 4: Lesson System**
- Task 4.1: 1 hour
- Task 4.2: 6 hours
- Task 4.3: 3 hours
- Task 4.4: 2 hours
- Task 4.5/4.6: 12 hours
- **Total: 24 hours (4-5 days)**

**Phase 5: Adaptive Algorithm**
- Task 5.1: 4 hours
- Task 5.2: 8 hours
- Task 5.3: 2 hours
- Task 5.4: 4 hours
- Task 5.5: 8 hours
- **Total: 26 hours (3-4 days)**

**Phase 6: Notifications & Polish**
- Task 6.1: 3 hours
- Task 6.2: 3 hours
- Task 6.3: 2 hours
- Task 6.4: 2 hours
- Task 6.5: 1 hour
- **Total: 11 hours (2-3 days)**

**Phase 7: Testing & Deployment**
- Task 7.1: 6 hours
- Task 7.2: 4 hours
- Task 7.3: 3 hours
- Task 7.4: 2 hours
- Task 7.5: 1 hour
- Task 7.6: 1 hour
- **Total: 17 hours (3-4 days)**

### Summary

- **Total Estimated Hours:** 134 hours
- **Total Estimated Days:** 20-27 working days
- **Calendar Time:** 4-5 weeks (with buffer for testing and iterations)

### Risk Buffer

Add 20-30% buffer for:
- Unexpected bugs
- Integration issues
- LLM API adjustments
- Testing iterations
- Code reviews

**Realistic Timeline: 5-7 weeks**

---

## Implementation Notes

### Best Practices

1. **Commit Often:** Commit after each task completion
2. **Test Continuously:** Run tests after each change
3. **Log Everything:** Use structured logging for debugging
4. **Review Code:** Self-review before moving to next task
5. **Document Decisions:** Update docs with architectural decisions

### Common Pitfalls to Avoid

1. **Skipping Tests:** Don't skip unit tests - they save time later
2. **Hardcoding Values:** Use configuration for all settings
3. **Ignoring Errors:** Handle all edge cases properly
4. **Poor Logging:** Add logs at key decision points
5. **Database Migrations:** Always backup before migrations

### Success Criteria

**MVP Complete When:**
- ✅ User registration works
- ✅ Words can be added and translated
- ✅ Lessons run end-to-end
- ✅ Adaptive algorithm selects words
- ✅ Validation works (3 levels)
- ✅ Statistics display correctly
- ✅ Notifications sent automatically
- ✅ Tests pass (>80% coverage)
- ✅ Documentation complete

---

**End of Implementation Plan**

This plan provides a clear roadmap for implementing the Language Learning Telegram Bot. Follow the phases sequentially, respect dependencies, and maintain code quality throughout development.

Good luck! 🚀
