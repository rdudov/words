"""Tests for settings module."""

import os
import pytest
from pydantic import ValidationError

from words.config.settings import Settings


class TestSettings:
    """Test suite for Settings class."""

    def test_settings_load_from_env(self, monkeypatch):
        """Test that settings can be loaded from environment variables."""
        # Set required environment variables
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token_123")
        monkeypatch.setenv("LLM_API_KEY", "test_api_key_456")
        monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///test.db")

        # Create settings instance
        settings = Settings()

        # Verify required fields
        assert settings.telegram_bot_token == "test_token_123"
        assert settings.llm_api_key == "test_api_key_456"
        assert settings.database_url == "sqlite+aiosqlite:///test.db"

    def test_settings_default_values(self, monkeypatch):
        """Test that settings use correct default values."""
        # Set only required environment variables
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        # Unset optional environment variables to test defaults
        monkeypatch.delenv("LOG_FILE", raising=False)
        monkeypatch.delenv("DEBUG", raising=False)

        settings = Settings()

        # Verify default values
        assert settings.llm_model == "gpt-4o-mini"
        assert settings.words_per_lesson == 30
        assert settings.mastered_threshold == 30
        assert settings.choice_to_input_threshold == 3
        assert settings.notification_enabled is True
        assert settings.notification_interval_hours == 6
        assert settings.notification_time_start == "07:00"
        assert settings.notification_time_end == "23:00"
        assert settings.timezone == "Europe/Moscow"
        assert settings.log_level == "INFO"
        assert settings.log_file == "logs/bot.log"
        assert settings.debug is False

    def test_settings_custom_values(self, monkeypatch):
        """Test that settings can be overridden with custom values."""
        # Set all environment variables with custom values
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "custom_token")
        monkeypatch.setenv("LLM_API_KEY", "custom_key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("LLM_MODEL", "gpt-4")
        monkeypatch.setenv("WORDS_PER_LESSON", "50")
        monkeypatch.setenv("MASTERED_THRESHOLD", "40")
        monkeypatch.setenv("CHOICE_TO_INPUT_THRESHOLD", "5")
        monkeypatch.setenv("NOTIFICATION_ENABLED", "false")
        monkeypatch.setenv("NOTIFICATION_INTERVAL_HOURS", "12")
        monkeypatch.setenv("NOTIFICATION_TIME_START", "08:00")
        monkeypatch.setenv("NOTIFICATION_TIME_END", "22:00")
        monkeypatch.setenv("TIMEZONE", "America/New_York")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("LOG_FILE", "logs/custom.log")
        monkeypatch.setenv("DEBUG", "true")

        settings = Settings()

        # Verify custom values
        assert settings.telegram_bot_token == "custom_token"
        assert settings.llm_api_key == "custom_key"
        assert settings.database_url == "postgresql://localhost/test"
        assert settings.llm_model == "gpt-4"
        assert settings.words_per_lesson == 50
        assert settings.mastered_threshold == 40
        assert settings.choice_to_input_threshold == 5
        assert settings.notification_enabled is False
        assert settings.notification_interval_hours == 12
        assert settings.notification_time_start == "08:00"
        assert settings.notification_time_end == "22:00"
        assert settings.timezone == "America/New_York"
        assert settings.log_level == "DEBUG"
        assert settings.log_file == "logs/custom.log"
        assert settings.debug is True

    def test_settings_missing_required_fields(self, monkeypatch, tmp_path):
        """Test that settings raise error when required fields are missing."""
        # Clear all environment variables
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        # Change to temp directory to avoid loading .env file
        monkeypatch.chdir(tmp_path)

        # Attempt to create settings should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        # Verify error mentions missing fields
        error_str = str(exc_info.value)
        assert "telegram_bot_token" in error_str or "TELEGRAM_BOT_TOKEN" in error_str

    def test_settings_case_insensitive(self, monkeypatch):
        """Test that settings are case insensitive."""
        # Set environment variables with different cases
        monkeypatch.setenv("telegram_bot_token", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("database_url", "sqlite:///test.db")

        settings = Settings()

        # Should work regardless of case
        assert settings.telegram_bot_token == "test_token"
        assert settings.llm_api_key == "test_key"
        assert settings.database_url == "sqlite:///test.db"

    def test_settings_type_conversion(self, monkeypatch):
        """Test that settings correctly convert types."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("WORDS_PER_LESSON", "45")
        monkeypatch.setenv("NOTIFICATION_ENABLED", "true")
        monkeypatch.setenv("DEBUG", "1")

        settings = Settings()

        # Verify type conversions
        assert isinstance(settings.words_per_lesson, int)
        assert settings.words_per_lesson == 45
        assert isinstance(settings.notification_enabled, bool)
        assert settings.notification_enabled is True
        assert isinstance(settings.debug, bool)
        assert settings.debug is True

    def test_settings_singleton_from_env_file(self):
        """Test that singleton settings instance loads from .env file."""
        from words.config import settings

        # Should load from .env file in project root
        assert hasattr(settings, "telegram_bot_token")
        assert hasattr(settings, "llm_api_key")
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "llm_model")
        assert hasattr(settings, "words_per_lesson")


class TestSettingsValidation:
    """Test suite for Settings validation."""

    def test_empty_telegram_bot_token(self, monkeypatch, tmp_path):
        """Test that empty telegram_bot_token raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "telegram_bot_token" in str(exc_info.value)

    def test_whitespace_only_telegram_bot_token(self, monkeypatch, tmp_path):
        """Test that whitespace-only telegram_bot_token raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "   ")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "telegram_bot_token" in str(exc_info.value)

    def test_empty_llm_api_key(self, monkeypatch, tmp_path):
        """Test that empty llm_api_key raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "llm_api_key" in str(exc_info.value)

    def test_empty_database_url(self, monkeypatch, tmp_path):
        """Test that empty database_url raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "database_url" in str(exc_info.value)

    def test_negative_words_per_lesson(self, monkeypatch, tmp_path):
        """Test that negative words_per_lesson raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("WORDS_PER_LESSON", "-5")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "words_per_lesson" in str(exc_info.value)

    def test_zero_words_per_lesson(self, monkeypatch, tmp_path):
        """Test that zero words_per_lesson raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("WORDS_PER_LESSON", "0")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "words_per_lesson" in str(exc_info.value)

    def test_negative_mastered_threshold(self, monkeypatch, tmp_path):
        """Test that negative mastered_threshold raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("MASTERED_THRESHOLD", "-10")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "mastered_threshold" in str(exc_info.value)

    def test_zero_choice_to_input_threshold(self, monkeypatch, tmp_path):
        """Test that zero choice_to_input_threshold raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("CHOICE_TO_INPUT_THRESHOLD", "0")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "choice_to_input_threshold" in str(exc_info.value)

    def test_negative_notification_interval_hours(self, monkeypatch, tmp_path):
        """Test that negative notification_interval_hours raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("NOTIFICATION_INTERVAL_HOURS", "-1")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "notification_interval_hours" in str(exc_info.value)

    def test_invalid_time_format_missing_colon(self, monkeypatch, tmp_path):
        """Test that invalid time format without colon raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("NOTIFICATION_TIME_START", "0700")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "notification_time_start" in str(exc_info.value)
        assert "HH:MM" in str(exc_info.value)

    def test_invalid_time_format_out_of_range_hour(self, monkeypatch, tmp_path):
        """Test that time with hour > 23 raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("NOTIFICATION_TIME_START", "25:00")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "notification_time_start" in str(exc_info.value)

    def test_invalid_time_format_out_of_range_minute(self, monkeypatch, tmp_path):
        """Test that time with minute > 59 raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("NOTIFICATION_TIME_END", "23:60")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "notification_time_end" in str(exc_info.value)

    def test_invalid_time_format_single_digit_hour(self, monkeypatch, tmp_path):
        """Test that time with single digit hour raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("NOTIFICATION_TIME_START", "7:00")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "notification_time_start" in str(exc_info.value)

    def test_valid_time_formats(self, monkeypatch, tmp_path):
        """Test that valid time formats are accepted."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("NOTIFICATION_TIME_START", "00:00")
        monkeypatch.setenv("NOTIFICATION_TIME_END", "23:59")

        settings = Settings()
        assert settings.notification_time_start == "00:00"
        assert settings.notification_time_end == "23:59"

    def test_invalid_log_level(self, monkeypatch, tmp_path):
        """Test that invalid log level raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("LOG_LEVEL", "INVALID")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "log_level" in str(exc_info.value)

    def test_valid_log_levels(self, monkeypatch, tmp_path):
        """Test that all valid log levels are accepted."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            monkeypatch.chdir(tmp_path)
            monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
            monkeypatch.setenv("LLM_API_KEY", "test_key")
            monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
            monkeypatch.setenv("LOG_LEVEL", level)

            settings = Settings()
            assert settings.log_level == level

    def test_invalid_timezone(self, monkeypatch, tmp_path):
        """Test that invalid timezone raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("LLM_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("TIMEZONE", "Invalid/Timezone")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "timezone" in str(exc_info.value)
        assert "IANA" in str(exc_info.value)

    def test_valid_timezones(self, monkeypatch, tmp_path):
        """Test that valid timezones are accepted."""
        valid_timezones = [
            "Europe/Moscow",
            "America/New_York",
            "Asia/Tokyo",
            "UTC"
        ]

        for tz in valid_timezones:
            monkeypatch.chdir(tmp_path)
            monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
            monkeypatch.setenv("LLM_API_KEY", "test_key")
            monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
            monkeypatch.setenv("TIMEZONE", tz)

            settings = Settings()
            assert settings.timezone == tz
