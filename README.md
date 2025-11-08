# Words - Language Learning Telegram Bot

A Telegram bot for language learning with adaptive spaced repetition, LLM-powered validation, and intelligent word selection.

## Project Status

**Current Phase:** Phase 1 - Core Infrastructure
**Version:** 0.1.0

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

### Next Tasks
- Task 1.6: ORM Models - Lesson & Statistics
- Task 1.7: ORM Models - Cache Tables
- Task 1.8: Logging Setup
- Task 1.9: Initialize Database Script

## Project Structure

```
/opt/projects/words/
├── data/
│   ├── frequency_lists/  # Word frequency data
│   └── translations/     # Translation data
├── logs/                 # Application logs
├── src/words/           # Main application package
│   ├── __init__.py
│   └── __main__.py
└── tests/               # Test suite
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

2. Install dependencies (once Task 0.2 is complete):
```bash
pip install -r requirements.txt
```

### Running the Application

```bash
python -m src.words
```

## Documentation

- [Requirements](docs/requirements.md) - Project requirements and specifications
- [Architecture](docs/architecture.md) - System architecture and design
- [Implementation Plan](docs/implementation_plan.md) - Detailed implementation roadmap

## Development Guidelines

See [CLAUDE.md](CLAUDE.md) for development guidelines and project conventions.

## License

TBD
