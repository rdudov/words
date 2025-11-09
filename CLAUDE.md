# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot for language learning with adaptive spaced repetition, LLM-powered validation, and intelligent word selection. The project has completed Phase 2 (User Management) and is ready for Phase 3 (Word Management).

**Current Status:**
- ✅ Phase 0 Complete: Project Setup (Tasks 0.1-0.3)
- ✅ Phase 1 Complete: Core Infrastructure (Tasks 1.1-1.9 complete)
- ✅ Phase 2 Complete: User Management (Tasks 2.1-2.7 complete)

## Project Structure

```
/opt/projects/words/
├── src/words/           # Main application package
├── tests/               # Test suite with pytest
├── data/                # Data directories (frequency lists, translations)
├── logs/                # Application logs
└── docs/                # Project documentation
```

## Getting Started

The project uses Python 3.11+ and requires a virtual environment:

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (once available)
pip install -r requirements.txt

# Run the application
python -m src.words
```

## Development Workflow

1. Follow the implementation plan in `docs/implementation_plan.md`
2. Run tests before committing: `pytest`
3. Update README.md after significant changes

## Rules

Находи и используй уже имеющиеся в проекте классы и методы. Не дублируй похожую функциональность.

Не используй глобальный python-интерпретатор. Используй venv, если он есть в проекте. Если venv нет, то создай его.

Пиши структурированный код. Разбивай на отдельные файлы для лучшего понимания.

После изменений проверяй README.md на актуальность.
