# Implementation Plan: Language Learning Telegram Bot

**Project:** Words - Telegram Bot for Language Learning
**Version:** 1.0.1
**Created:** 2025-11-08
**Updated:** 2025-11-09
**Status:** Phase 3 in Progress

---

## Table of Contents

1. [Overview](#overview)
2. [Use Cases Coverage](#use-cases-coverage)
3. [Implementation Phases](#implementation-phases)
4. [Phase 0: Project Setup](#phase-0-project-setup)
5. [Phase 1: Core Infrastructure](#phase-1-core-infrastructure)
6. [Phase 2: User Management](#phase-2-user-management)
7. [Phase 3: Word Management](#phase-3-word-management)
8. [Phase 4: Lesson System](#phase-4-lesson-system)
9. [Phase 5: Adaptive Algorithm](#phase-5-adaptive-algorithm)
10. [Phase 6: Notifications & Polish](#phase-6-notifications--polish)
11. [Phase 7: Testing & Deployment](#phase-7-testing--deployment)
12. [Task Details Location](#task-details-location)

---

## Overview

This implementation plan breaks down the development of the Language Learning Telegram Bot into 8 phases, from initial project setup to deployment. Each task is presented in simplified format with links to detailed technical documentation.

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

## Use Cases Coverage

| Use Case | Description | Tasks | Status |
|----------|-------------|-------|--------|
| UC1 | Регистрация и выбор языка | 2.6, 3.7 | 🟡 Partially (3.7 pending) |
| UC2 | Смена/добавление языка | 6.4 | 🔴 Pending (P2) |
| UC3 | Автоматическое формирование списка | **3.7** | 🔴 **NEW - PENDING** |
| UC4 | Ручное добавление слова | 3.6 | ✅ Completed |
| UC5 | Прохождение урока (native→foreign) | 5.5 | 🔴 Pending |
| UC6 | Получение уведомлений | 6.1, 6.2 | 🔴 Pending (P1) |
| UC7 | Прохождение урока (foreign→native) | 5.5 | 🔴 Pending |
| UC8 | Продолжение незавершенного урока | 5.5 | 🔴 Pending |
| UC9 | Валидация ответа с LLM | 4.1, 4.2 | 🔴 Pending |
| UC10 | Адаптивный выбор слов | 5.1, 5.2 | 🔴 Pending |
| UC11 | Просмотр статистики | 6.3 | 🔴 Pending (P1) |

---

## Implementation Phases

```
Phase 0: Project Setup (1 day) ✅ COMPLETED
    ↓
Phase 1: Core Infrastructure (2-3 days) ✅ COMPLETED
    ↓
Phase 2: User Management (2 days) ✅ COMPLETED
    ↓
Phase 3: Word Management (3-4 days) ⏳ IN PROGRESS
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
**Status:** ✅ COMPLETED

### Task 0.1: Initialize Project Structure ✅ COMPLETED

**What:** Create directory structure and initialize git repository

**Why:** Foundation for organized development

**Key Points:**
- Standard Python project layout
- Separation of source code, tests, data, and logs
- Git repository with proper .gitignore

**Dependencies:** None

**Acceptance Criteria:**
- [ ] All directories exist
- [ ] Git ignores appropriate files
- [ ] Project can be imported as a Python package

---

### Task 0.2: Setup Dependencies ✅ COMPLETED

**What:** Define and install all project dependencies

**Why:** Establish development environment with required libraries

**Key Points:**
- aiogram for Telegram bot framework
- SQLAlchemy for async database operations
- OpenAI client for LLM integration
- pytest for testing

**Dependencies:** None

**Acceptance Criteria:**
- [ ] Virtual environment created
- [ ] All dependencies installed without errors
- [ ] Can import key libraries

---

### Task 0.3: Setup Configuration Files ✅ COMPLETED

**What:** Create configuration files for environment, testing, and deployment

**Why:** Centralized configuration management

**Key Points:**
- .env.example with all required variables
- pytest.ini for test configuration
- Clear documentation of configuration options

**Dependencies:** Task 0.2

**Acceptance Criteria:**
- [ ] Configuration files exist
- [ ] .env has real credentials (not committed)
- [ ] pytest configuration is valid

---

## Phase 1: Core Infrastructure

**Goal:** Implement foundational infrastructure components
**Duration:** 2-3 days
**Status:** ✅ COMPLETED

### Task 1.1: Configuration Management ✅ COMPLETED

**What:** Pydantic-based settings management from environment variables

**Why:** Type-safe configuration with validation

**Key Points:**
- Pydantic Settings for .env loading
- Constants file for application-wide values
- Singleton pattern for settings access

**Dependencies:** Task 0.2

**Acceptance Criteria:**
- [ ] Settings loaded from environment variables
- [ ] All configuration accessible via settings instance
- [ ] Constants defined and importable

**Details:** [tasks/phase-1/task-1.1-configuration-management-completed.md](tasks/phase-1/task-1.1-configuration-management-completed.md)

---

### Task 1.2: Database Setup ✅ COMPLETED

**What:** Async SQLAlchemy engine and session management

**Why:** Database connectivity foundation

**Key Points:**
- Async engine with proper pooling
- Session factory with context manager
- Database initialization and cleanup functions

**Dependencies:** Task 1.1

**Acceptance Criteria:**
- [ ] Database connection established
- [ ] Session management working
- [ ] Connection pool configured correctly

---

### Task 1.3: ORM Models - Base ✅ COMPLETED

**What:** Base declarative model and timestamp mixin

**Why:** Foundation for all ORM models

**Key Points:**
- AsyncAttrs for async relationship loading
- TimestampMixin for created_at/updated_at
- Consistent base for all models

**Dependencies:** Task 1.2

**Acceptance Criteria:**
- [ ] Base model can be imported
- [ ] TimestampMixin works correctly

---

### Task 1.4: ORM Models - User & Profile ✅ COMPLETED

**What:** User and LanguageProfile models with relationships

**Why:** Core user data structure

**Key Points:**
- User table with telegram_id and settings
- LanguageProfile for multi-language support
- One-to-many relationship with cascade delete

**Dependencies:** Task 1.3

**Acceptance Criteria:**
- [ ] Models defined with proper types
- [ ] Relationships work correctly
- [ ] Can create and query users

---

### Task 1.5: ORM Models - Word & UserWord ✅ COMPLETED

**What:** Word dictionary and user vocabulary models

**Why:** Core vocabulary management

**Key Points:**
- Word table with translations and metadata
- UserWord linking users to words
- Status tracking (new, learning, mastered)

**Dependencies:** Task 1.3

**Acceptance Criteria:**
- [ ] Word model with JSON fields
- [ ] UserWord with status enum
- [ ] Foreign key relationships work

---

### Task 1.6: ORM Models - Lesson & Statistics ✅ COMPLETED

**What:** Lesson sessions and performance statistics

**Why:** Track learning progress

**Key Points:**
- Lesson with questions and answers
- LessonAttempt for question-level tracking
- LessonStatistics for aggregated metrics

**Dependencies:** Task 1.3

**Acceptance Criteria:**
- [ ] Lesson model with JSON structure
- [ ] Statistics track attempts and performance
- [ ] Relationships to users and words

---

### Task 1.7: ORM Models - Cache Tables ✅ COMPLETED

**What:** Cache tables for LLM API results

**Why:** Reduce API costs and improve performance

**Key Points:**
- CachedTranslation for word translations
- CachedValidation for answer checks
- Optional expiration dates

**Dependencies:** Task 1.3

**Acceptance Criteria:**
- [ ] Cache models defined
- [ ] Unique constraints on cache keys
- [ ] Expiration handling

---

### Task 1.8: Logging Setup ✅ COMPLETED

**What:** Centralized logging configuration with rotation

**Why:** Production-ready logging without external dependencies

**Key Points:**
- Standard logging module (not structlog)
- Rotating file handler for log management
- Dual output (console + file)

**Dependencies:** Task 1.1

**Acceptance Criteria:**
- [ ] Logging configured and working
- [ ] Log rotation functioning
- [ ] Console and file output

---

### Task 1.9: Initialize Database Script ✅ COMPLETED

**What:** Script to create all database tables

**Why:** Database schema initialization

**Key Points:**
- Async table creation
- Imports all models
- Can be run independently

**Dependencies:** Tasks 1.2-1.7

**Acceptance Criteria:**
- [ ] Script creates all tables
- [ ] Can run multiple times safely
- [ ] Logs initialization status

---

## Phase 2: User Management

**Goal:** Implement user registration and profile management
**Duration:** 2 days
**Status:** ✅ COMPLETED

### Task 2.1: Base Repository Pattern 🟢 P0 ✅ COMPLETED

**What:** Generic repository base class for database operations

**Why:** DRY principle for data access layer

**Key Points:**
- Generic type parameter for model
- Common CRUD operations
- Async/await pattern

**Dependencies:** Task 1.2

**Acceptance Criteria:**
- [ ] Base repository with CRUD methods
- [ ] Type hints working
- [ ] Can be extended by specific repositories

---

### Task 2.2: User Repository 🟡 P0 ✅ COMPLETED

**Related Use Cases:** UC1

**What:** User and LanguageProfile data access layer

**Why:** Encapsulate user database operations

**Key Points:**
- UserRepository for user CRUD
- ProfileRepository for language profiles
- Eager loading for relationships

**Dependencies:** Task 2.1

**Acceptance Criteria:**
- [ ] User CRUD operations
- [ ] Profile management methods
- [ ] Relationships eagerly loaded

---

### Task 2.3: User Service 🟡 P0 ✅ COMPLETED

**Related Use Cases:** UC1

**What:** User business logic and orchestration

**Why:** Coordinate registration and profile management

**Key Points:**
- User registration flow
- Profile creation and activation
- Multi-language profile support

**Dependencies:** Task 2.2

**Acceptance Criteria:**
- [ ] Can register new users
- [ ] Profile activation works
- [ ] Business logic properly encapsulated

---

### Task 2.4: Bot State Machine 🟢 P0 ✅ COMPLETED

**What:** FSM states for registration and other flows

**Why:** Track multi-step interactions

**Key Points:**
- RegistrationStates for sign-up flow
- AddWordStates for word addition
- Extensible for future flows

**Dependencies:** Task 0.2

**Acceptance Criteria:**
- [ ] States defined as StatesGroup
- [ ] Can transition between states
- [ ] State cleared after completion

---

### Task 2.5: Telegram Keyboards 🟢 P1 ✅ COMPLETED

**What:** Reusable keyboard builders for common UI elements

**Why:** Consistent bot interface

**Key Points:**
- Language selection keyboards
- CEFR level selection
- Main menu keyboard

**Dependencies:** Task 0.2

**Acceptance Criteria:**
- [ ] Keyboards render correctly
- [ ] Callback data properly structured
- [ ] Responsive to user selections

---

### Task 2.6: Registration Handler 🟡 P0 ✅ COMPLETED

**Related Use Cases:** UC1

**What:** Multi-step registration conversation handler

**Why:** Onboard new users

**Key Points:**
- /start command handler
- Step-by-step state management
- Profile creation on completion

**Dependencies:** Tasks 2.3, 2.4, 2.5

**Acceptance Criteria:**
- [ ] Complete registration flow works
- [ ] User created in database
- [ ] Profile activated

---

### Task 2.7: Main Bot Setup 🟢 P0 ✅ COMPLETED

**What:** Bot initialization and dispatcher setup

**Why:** Entry point for bot application

**Key Points:**
- Bot and Dispatcher initialization
- Router registration
- Graceful shutdown handling

**Dependencies:** Task 2.6

**Acceptance Criteria:**
- [ ] Bot starts successfully
- [ ] Handlers registered
- [ ] Shutdown cleanup works

---

## Phase 3: Word Management

**Goal:** Implement word addition, translation service, LLM integration, and caching
**Duration:** 3-4 days
**Status:** ⏳ IN PROGRESS (Tasks 3.1-3.6 completed, 3.7 pending)

### Task 3.1: LLM Client 🟡 P0 ✅ COMPLETED

**What:** OpenAI async client with retry logic

**Why:** LLM API integration foundation

**Key Points:**
- Async OpenAI client wrapper
- Retry logic with exponential backoff
- Translation and validation methods

**Dependencies:** Task 1.1

**Acceptance Criteria:**
- [ ] Can call OpenAI API successfully
- [ ] Retries on transient failures
- [ ] Returns structured data

---

### Task 3.2: Cache Repository 🟡 P1 ✅ COMPLETED

**What:** Repository for translation and validation cache

**Why:** Reduce API costs and latency

**Key Points:**
- Translation cache lookup and storage
- Validation cache with compound keys
- Expiration handling

**Dependencies:** Task 1.7

**Acceptance Criteria:**
- [ ] Translation caching works
- [ ] Validation caching works
- [ ] Cache lookups are fast

---

### Task 3.3: Translation Service 🟡 P0 ✅ COMPLETED

**What:** Service layer for word translation with caching

**Why:** Coordinate LLM calls and cache management

**Key Points:**
- Cache-first translation lookups
- LLM fallback on cache miss
- Validation caching

**Dependencies:** Tasks 3.1, 3.2

**Acceptance Criteria:**
- [ ] Translation works with caching
- [ ] Validation works with caching
- [ ] Logs all LLM calls

---

### Task 3.4: Word Repository 🟡 P0 ✅ COMPLETED

**What:** Data access layer for Word and UserWord

**Why:** Encapsulate vocabulary database operations

**Key Points:**
- Word lookup by text and language
- UserWord CRUD operations
- Vocabulary queries with filtering

**Dependencies:** Task 1.5

**Acceptance Criteria:**
- [ ] Word CRUD operations working
- [ ] User word management implemented
- [ ] Statistics eager loading works

---

### Task 3.5: Word Service 🔴 P0 ✅ COMPLETED

**What:** Business logic for word management

**Why:** Orchestrate word addition flow

**Key Points:**
- Add word to user vocabulary
- Translation fetching
- Word deduplication
- Statistics initialization

**Dependencies:** Tasks 3.3, 3.4

**Acceptance Criteria:**
- [ ] Can add words to user vocabulary
- [ ] Translation fetched and cached
- [ ] Word deduplication works

---

### Task 3.6: Add Word Handler 🟡 P1 ✅ COMPLETED

**Related Use Cases:** UC4

**What:** Telegram handler for manual word addition

**Why:** Allow users to build custom vocabulary

**Key Points:**
- /add_word command or button
- FSM for word input
- Translation display

**Dependencies:** Tasks 3.5, 2.6

**Acceptance Criteria:**
- [ ] User can add words
- [ ] Translation fetched and displayed
- [ ] Word saved to vocabulary

---

### Task 3.7: Auto Word Selection Service 🟡 P0 🔴 PENDING

**Related Use Cases:** UC1, UC3

**What:** Автоматический подбор слов при регистрации на основе уровня CEFR

**Why:** Новым пользователям нужен стартовый набор слов для начала обучения

**Key Points:**
- Загрузка частотных списков по уровню
- Автоматическое добавление 50 слов через Word Service
- Вызов из Registration Handler после создания профиля
- Интеграция с существующими сервисами

**Dependencies:** Task 3.5 (Word Service), Task 7.3 (Frequency Lists)

**Acceptance Criteria:**
- [ ] Auto Word Selection Service создан
- [ ] Интеграция с Registration Handler
- [ ] При регистрации автоматически добавляются слова
- [ ] Обработка ошибок (отсутствие частотных списков)

**Details:** [tasks/phase-3/task-3.7-auto-word-selection-pending.md](tasks/phase-3/task-3.7-auto-word-selection-pending.md)

---

## Phase 4: Lesson System

**Goal:** Implement lesson orchestration, question generation, answer validation
**Duration:** 4-5 days
**Status:** 🔴 PENDING

### Task 4.1: String Utilities (Fuzzy Matching) 🟢 P0

**Related Use Cases:** UC9

**What:** Fuzzy string matching utilities for answer validation

**Why:** Detect typos and minor differences

**Key Points:**
- Levenshtein distance calculation
- Typo detection threshold
- String normalization

**Dependencies:** Task 0.2

**Acceptance Criteria:**
- [ ] Levenshtein distance calculated correctly
- [ ] Typo detection works
- [ ] Normalization handles edge cases

**Details:** [tasks/phase-4/task-4.1-string-utilities-pending.md](tasks/phase-4/task-4.1-string-utilities-pending.md)

---

### Task 4.2: Validation Service 🔴 P0

**Related Use Cases:** UC9

**What:** Three-level answer validation (exact, fuzzy, LLM)

**Why:** Flexible answer checking with fallbacks

**Key Points:**
- Level 1: Exact match
- Level 2: Fuzzy match (typos)
- Level 3: LLM validation (synonyms)
- Structured validation results

**Dependencies:** Tasks 3.3, 4.1

**Acceptance Criteria:**
- [ ] Three-level validation working
- [ ] Exact matches pass immediately
- [ ] Typos detected and accepted
- [ ] LLM fallback works

---

### Task 4.3: Lesson Repositories 🟡 P0

**What:** Data access layer for Lesson and LessonAttempt

**Why:** Encapsulate lesson database operations

**Key Points:**
- Lesson CRUD operations
- Active lesson retrieval
- Lesson history queries

**Dependencies:** Task 1.6

**Acceptance Criteria:**
- [ ] Lesson CRUD working
- [ ] Can find active lessons
- [ ] History queries work

---

### Task 4.4: Statistics Repository 🟢 P1

**What:** Repository for lesson statistics

**Why:** Track performance metrics

**Key Points:**
- Statistics CRUD
- Aggregation queries
- Performance metrics

**Dependencies:** Task 1.6

**Acceptance Criteria:**
- [ ] Statistics stored correctly
- [ ] Aggregations work
- [ ] Metrics calculation

---

### Task 4.5: Lesson Service (Core) 🔴 P0

**What:** Core lesson business logic structure

**Why:** Orchestrate lesson flow

**Key Points:**
- Lesson creation and management
- Question generation
- Answer processing
- Score calculation

**Dependencies:** Tasks 4.2, 4.3, 4.4

**Acceptance Criteria:**
- [ ] Lesson lifecycle management
- [ ] Question generation works
- [ ] Answer validation integrated
- [ ] Scores calculated correctly

---

### Task 4.6: Lesson Service Implementation (Detailed) 🔴 P0

**What:** Complete lesson service implementation

**Why:** Full lesson functionality

**Key Points:**
- Multiple choice question generation
- Input question handling
- Progress tracking
- Lesson completion logic

**Dependencies:** Task 4.5

**Acceptance Criteria:**
- [ ] Both question types work
- [ ] Progress tracked correctly
- [ ] Completion triggers properly
- [ ] Statistics updated

---

## Phase 5: Adaptive Algorithm

**Goal:** Implement spaced repetition and adaptive word selection
**Duration:** 3-4 days
**Status:** 🔴 PENDING

### Task 5.1: Spaced Repetition Algorithm 🟡 P0

**Related Use Cases:** UC10

**What:** SM-2 algorithm for word scheduling

**Why:** Optimize learning intervals

**Key Points:**
- SM-2 easiness factor calculation
- Next review date scheduling
- Difficulty adjustment

**Dependencies:** Task 1.5

**Acceptance Criteria:**
- [ ] SM-2 algorithm implemented
- [ ] Review intervals calculated
- [ ] Difficulty factors tracked

---

### Task 5.2: Word Selector Algorithm 🔴 P0

**Related Use Cases:** UC10

**What:** Smart word selection for lessons

**Why:** Balance new words and reviews

**Key Points:**
- Due word prioritization
- New word introduction
- Status-based selection
- Randomization for variety

**Dependencies:** Task 3.4

**Acceptance Criteria:**
- [ ] Selects due words first
- [ ] Introduces new words appropriately
- [ ] Balances word types
- [ ] Respects lesson size limits

---

### Task 5.3: Difficulty Adjuster 🟢 P1

**What:** Dynamic test type selection based on performance

**Why:** Adapt to user skill level

**Key Points:**
- Multiple choice for new words
- Input for confident words
- Threshold-based transitions

**Dependencies:** Task 4.4

**Acceptance Criteria:**
- [ ] Test type selection works
- [ ] Transitions at thresholds
- [ ] Performance tracked

---

### Task 5.4: Integrate Algorithm into Lesson Service 🟡 P0

**What:** Wire adaptive algorithms into lesson creation

**Why:** Make lessons adaptive

**Key Points:**
- Word selection integration
- SM-2 scheduling integration
- Difficulty adjustment hook

**Dependencies:** Tasks 5.1, 5.2, 5.3

**Acceptance Criteria:**
- [ ] Lessons use word selector
- [ ] SM-2 updates on answers
- [ ] Difficulty adjusts dynamically

---

### Task 5.5: Lesson Handler 🔴 P0

**Related Use Cases:** UC5, UC7, UC8

**What:** Telegram handlers for lesson flow

**Why:** User interface for lessons

**Key Points:**
- Start lesson command
- Question display
- Answer processing
- Progress display
- Lesson completion

**Dependencies:** Task 5.4

**Acceptance Criteria:**
- [ ] Lesson start works
- [ ] Questions display correctly
- [ ] Answers validated
- [ ] Progress shown
- [ ] Completion handled

---

## Phase 6: Notifications & Polish

**Goal:** Add notifications, statistics, and user settings
**Duration:** 2-3 days
**Status:** 🔴 PENDING

### Task 6.1: Notification Service 🟡 P1

**Related Use Cases:** UC6

**What:** Service for sending lesson reminders

**Why:** Encourage regular practice

**Key Points:**
- Reminder message generation
- User notification settings
- Timezone handling

**Dependencies:** Task 2.3

**Acceptance Criteria:**
- [ ] Can send notifications
- [ ] Respects user preferences
- [ ] Timezone-aware

---

### Task 6.2: Scheduler Setup 🟡 P1

**Related Use Cases:** UC6

**What:** APScheduler integration for periodic tasks

**Why:** Automated notification delivery

**Key Points:**
- Scheduler initialization
- Periodic notification job
- Graceful shutdown

**Dependencies:** Task 6.1

**Acceptance Criteria:**
- [ ] Scheduler runs
- [ ] Notifications sent on schedule
- [ ] Shutdown clean

---

### Task 6.3: Statistics Handler 🟢 P1

**Related Use Cases:** UC11

**What:** Telegram handler for user statistics

**Why:** Show learning progress

**Key Points:**
- Vocabulary statistics
- Lesson history
- Performance metrics
- Formatted display

**Dependencies:** Tasks 4.4, 3.5

**Acceptance Criteria:**
- [ ] Statistics command works
- [ ] Data displayed correctly
- [ ] Charts/visualizations

---

### Task 6.4: Settings Handler 🟢 P2

**Related Use Cases:** UC2

**What:** User settings management

**Why:** Allow preference customization

**Key Points:**
- Notification toggle
- Language profile management
- Timezone selection

**Dependencies:** Task 2.3

**Acceptance Criteria:**
- [ ] Settings command works
- [ ] Preferences saved
- [ ] Changes applied

---

### Task 6.5: Update Main Bot with Scheduler 🟡 P1

**What:** Integrate scheduler into bot lifecycle

**Why:** Enable periodic tasks

**Key Points:**
- Scheduler startup on bot start
- Scheduler shutdown on bot stop
- Error handling

**Dependencies:** Task 6.2

**Acceptance Criteria:**
- [ ] Scheduler starts with bot
- [ ] Scheduler stops cleanly
- [ ] Jobs execute

---

## Phase 7: Testing & Deployment

**Goal:** Comprehensive testing and production readiness
**Duration:** 3-4 days
**Status:** 🔴 PENDING

### Task 7.1: Unit Tests - Services 🟡 P1

**What:** Unit tests for service layer

**Why:** Ensure business logic correctness

**Key Points:**
- WordService tests
- UserService tests
- LessonService tests
- ValidationService tests

**Dependencies:** Phases 2-5 completed

**Acceptance Criteria:**
- [ ] All services covered
- [ ] Edge cases tested
- [ ] Mocks used properly

---

### Task 7.2: Integration Tests 🟡 P2

**What:** End-to-end integration tests

**Why:** Verify system integration

**Key Points:**
- Database integration tests
- LLM integration tests
- Handler integration tests

**Dependencies:** Task 7.1

**Acceptance Criteria:**
- [ ] Critical flows tested
- [ ] Database interactions work
- [ ] External APIs mocked

---

### Task 7.3: Load Frequency Lists 🟡 P1

**What:** Script to load word frequency lists

**Why:** Populate initial word database

**Key Points:**
- Parse frequency lists by level
- Bulk insert words
- Assign CEFR levels

**Dependencies:** Task 3.4

**Acceptance Criteria:**
- [ ] Script loads all lists
- [ ] Words categorized by level
- [ ] Database populated

---

### Task 7.4: Deployment Documentation 🟢 P1

**What:** Production deployment guide

**Why:** Repeatable deployment process

**Key Points:**
- Server requirements
- Installation steps
- Environment configuration
- Monitoring setup

**Dependencies:** None

**Acceptance Criteria:**
- [ ] Deployment guide complete
- [ ] Configuration documented
- [ ] Troubleshooting included

---

### Task 7.5: README Update 🟢 P1

**What:** Update project README

**Why:** Clear project documentation

**Key Points:**
- Feature overview
- Installation instructions
- Usage examples
- Architecture summary

**Dependencies:** None

**Acceptance Criteria:**
- [ ] README comprehensive
- [ ] Examples provided
- [ ] Links working

---

### Task 7.6: Systemd Service Setup 🟢 P2

**What:** Systemd service for bot

**Why:** Auto-restart and management

**Key Points:**
- Service file creation
- Auto-restart configuration
- Log management

**Dependencies:** Task 7.4

**Acceptance Criteria:**
- [ ] Service installs
- [ ] Auto-restart works
- [ ] Logs accessible

---

## Task Details Location

Детальные технические описания задач вынесены в отдельные файлы в `docs/tasks/`.

**Примеры:**
- [Task 1.1: Configuration Management](tasks/phase-1/task-1.1-configuration-management-completed.md)
- [Task 3.7: Auto Word Selection](tasks/phase-3/task-3.7-auto-word-selection-pending.md)
- [Task 4.1: String Utilities](tasks/phase-4/task-4.1-string-utilities-pending.md)

**Создать детальные файлы для остальных задач можно по аналогии с примерами выше.**

Каждый файл задачи содержит:
- Полное техническое описание
- Листинги кода (если применимо)
- Детальные критерии приемки
- Рекомендации по тестированию
- Примеры использования

---

**END OF DOCUMENT**
