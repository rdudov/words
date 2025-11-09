# Words - Language Learning Telegram Bot

A Telegram bot for language learning with adaptive spaced repetition, LLM-powered validation, and intelligent word selection.

## Project Status

**Current Phase:** Phase 3 In Progress - Word Management
**Version:** 0.3.0-dev

### Completed Tasks

**Phase 0 - Project Setup:**
- ✅ Task 0.1: Initialize Project Structure
- ✅ Task 0.2: Setup Dependencies
- ✅ Task 0.3: Setup Configuration Files

**Phase 1 - Core Infrastructure:**
- ✅ Task 1.1: Configuration Management
- ✅ Task 1.2: Database Setup
- ✅ Task 1.3: ORM Models - Base
- ✅ Task 1.4: ORM Models - User & Profile
- ✅ Task 1.5: ORM Models - Word & UserWord
- ✅ Task 1.6: ORM Models - Lesson & Statistics
- ✅ Task 1.7: ORM Models - Cache Tables
- ✅ Task 1.8: Logging Setup
- ✅ Task 1.9: Initialize Database Script

**Phase 2 - User Management:**
- ✅ Task 2.1: Base Repository Pattern
- ✅ Task 2.2: User Repository
- ✅ Task 2.3: User Service
- ✅ Task 2.4: Bot State Machine
- ✅ Task 2.5: Telegram Keyboards
- ✅ Task 2.6: Registration Handler
- ✅ Task 2.7: Main Bot Setup

**Phase 3 - Word Management:**
- ✅ Task 3.1: LLM Client
- ✅ Task 3.2: Cache Repository

### Phase 3 In Progress

Working on Word Management implementation with LLM integration.

## Project Structure

```
/opt/projects/words/
├── data/
│   ├── database/        # SQLite database files
│   ├── frequency_lists/ # Word frequency data
│   └── translations/    # Translation data
├── logs/                # Application logs
├── scripts/             # Utility scripts
│   └── init_db.py       # Database initialization script
├── src/words/           # Main application package
│   ├── bot/             # Telegram bot components
│   ├── config/          # Configuration and constants
│   ├── infrastructure/  # Database infrastructure
│   ├── models/          # ORM models
│   ├── repositories/    # Data access layer
│   ├── services/        # Business logic layer
│   ├── utils/           # Utility modules (logger, etc.)
│   ├── __init__.py
│   └── __main__.py
└── tests/               # Test suite
    ├── bot/             # Bot tests
    ├── config/          # Config tests
    ├── infrastructure/  # Infrastructure tests
    ├── models/          # Model tests
    ├── repositories/    # Repository tests
    ├── services/        # Service tests
    ├── utils/           # Utility tests
    ├── __init__.py
    └── conftest.py
```

## Development Setup

### Prerequisites

- Python 3.11+
- Virtual environment (venv)

### Installation

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python scripts/init_db.py
```

This script will:
- Create the necessary database directories (if using SQLite)
- Create all database tables
- Can be run multiple times safely (idempotent)

### Running the Application

```bash
python -m src.words
```

### Database Management

The project includes a database initialization script:

```bash
# Initialize or update database schema
python scripts/init_db.py
```

The script is idempotent and can be run multiple times without issues. It will:
- Create the database directory if needed (for SQLite)
- Create all required tables
- Handle errors gracefully with proper logging

### Using the Logger

The application includes structured logging with support for both development and production modes:

```python
from src.words.utils import logger

# Basic logging
logger.info("User action", user_id=123)
logger.error("Something went wrong", error_code=500)

# Exception logging with stack traces
try:
    risky_operation()
except Exception:
    logger.exception("Operation failed")
```

Logging configuration:
- **Production mode** (`debug=False`): JSON format for easy parsing
- **Development mode** (`debug=True`): Human-readable console format
- Logs written to both file (configured via `log_file`) and console
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Documentation

- [Requirements](docs/requirements.md) - Project requirements and specifications
- [Architecture](docs/architecture.md) - System architecture and design
- [Implementation Plan](docs/implementation_plan.md) - Detailed implementation roadmap

## Development Guidelines

See [CLAUDE.md](CLAUDE.md) for development guidelines and project conventions.

## License

TBD
