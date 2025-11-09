# Task 1.1: Configuration Management

**Status:** ✅ COMPLETED
**Phase:** 1 - Core Infrastructure
**Priority:** P0 (Critical)
**Complexity:** 🟢 Simple
**Estimated Time:** 1-2 hours

## Related Use Cases

- *Infrastructure task - no direct UC mapping*

## Related Non-Functional Requirements

- **Configuration:** Все настройки через переменные окружения (requirements.md - Environment section)
- **Security:** Безопасное хранение API ключей и токенов через переменные окружения

## Description

### What

Централизованное управление настройками приложения через переменные окружения с использованием Pydantic Settings.

### Why

- Единая точка доступа ко всем настройкам проекта
- Валидация конфигурации при запуске
- Разделение конфигурации dev/prod через .env файлы
- Type safety для всех параметров

### How

1. Создать класс `Settings` с использованием `pydantic-settings`
2. Определить все параметры из requirements.md (Environment section)
3. Создать singleton instance для глобального доступа
4. Вынести константы в отдельный модуль `constants.py`

## Files

### To Create

- `src/words/config/settings.py` - класс Settings с pydantic-settings
- `src/words/config/constants.py` - константы проекта (статусы, типы, языки)
- `src/words/config/__init__.py` - экспорт settings и констант

## Implementation Details

### settings.py - Configuration Class

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Telegram Bot
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")

    # LLM API
    llm_api_key: str = Field(..., env="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", env="LLM_MODEL")

    # Database
    database_url: str = Field(..., env="DATABASE_URL")

    # Lesson Configuration
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

# Singleton instance - импортируется во всех модулях
settings = Settings()
```

### constants.py - Application Constants

```python
"""Application-wide constants"""

# Word Status States
class WordStatus:
    """Possible states for user words (requirements.md - user_words table)"""
    NEW = "new"
    LEARNING = "learning"
    REVIEWING = "reviewing"
    MASTERED = "mastered"

# Test Types
class TestType:
    """Types of knowledge tests (requirements.md - UC7, UC8)"""
    MULTIPLE_CHOICE = "multiple_choice"  # UC7
    INPUT = "input"                       # UC8

# Translation Directions
class Direction:
    """Translation direction for testing (requirements.md - UC12)"""
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
    """Methods for answer validation (requirements.md - UC9)"""
    EXACT = "exact"      # UC9 Level 1: Exact match
    FUZZY = "fuzzy"      # UC9 Level 2: Typo detection
    LLM = "llm"          # UC9 Level 3: LLM validation

# Fuzzy Matching Threshold
FUZZY_MATCH_THRESHOLD = 2  # Levenshtein distance (requirements.md - UC9)
```

### __init__.py - Module Exports

```python
"""Configuration module exports"""

from .settings import settings
from .constants import (
    WordStatus,
    TestType,
    Direction,
    CEFR_LEVELS,
    SUPPORTED_LANGUAGES,
    ValidationMethod,
    FUZZY_MATCH_THRESHOLD,
)

__all__ = [
    "settings",
    "WordStatus",
    "TestType",
    "Direction",
    "CEFR_LEVELS",
    "SUPPORTED_LANGUAGES",
    "ValidationMethod",
    "FUZZY_MATCH_THRESHOLD",
]
```

## Integration Points

### Usage in other modules

```python
# In any module
from src.words.config import settings, WordStatus

# Access settings
bot_token = settings.telegram_bot_token
words_count = settings.words_per_lesson

# Use constants
if user_word.status == WordStatus.MASTERED:
    # skip this word
    pass
```

### Environment File (.env)

See `.env.example` from Task 0.3 for required variables.

## Error Handling

- Pydantic will raise `ValidationError` if required env vars are missing
- Application will fail fast on startup if configuration is invalid
- This is desired behavior - better to fail early than run with bad config

## Testing

### Unit Tests

```python
# tests/config/test_settings.py

def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("LLM_API_KEY", "test_key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

    settings = Settings()
    assert settings.telegram_bot_token == "test_token"
    assert settings.llm_api_key == "test_key"

def test_settings_defaults():
    settings = Settings()
    assert settings.words_per_lesson == 30
    assert settings.mastered_threshold == 30
    assert settings.notification_enabled == True
```

### Integration Verification

- Application starts without errors
- All config values accessible
- Constants importable from other modules

## Dependencies

- **Task 0.2:** Setup Dependencies (pydantic, pydantic-settings installed)
- **Task 0.3:** .env.example created

## Acceptance Criteria

- [x] Settings class created with all parameters from requirements.md
- [x] Constants defined for WordStatus, TestType, Direction
- [x] Settings singleton instance available
- [x] All constants importable from config module
- [x] Pydantic validates required fields
- [x] Application can load settings from .env

## Implementation Notes

### Design Decisions

1. **Pydantic Settings**: Chosen for type safety and validation
2. **Singleton Pattern**: One settings instance shared across application
3. **Separate Constants**: Keep settings (runtime config) separate from constants (compile-time)

### Future Enhancements

- Add settings for cache TTL
- Add settings for LLM retry configuration
- Add settings for rate limiting

## References

- **requirements.md:** Environment section (lines 356-375)
- **requirements.md:** Constraints section (lines 321-335)
- **architecture.md:** Configuration management patterns

---

**Implementation Date:** 2025-11-08
**Last Updated:** 2025-11-08
