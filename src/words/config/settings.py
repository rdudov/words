"""
Application settings management using Pydantic Settings.

This module provides environment-based configuration for the Words application.
Settings are loaded from environment variables and .env file.
"""

import re
from typing import Literal

import pytz
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be configured via environment variables or .env file.
    Required settings must be provided, while optional settings have defaults.
    """

    # Telegram
    telegram_bot_token: str

    # LLM
    llm_api_key: str
    llm_model: str = "gpt-4o-mini"

    # Database
    database_url: str

    # Lesson Settings
    words_per_lesson: int = Field(default=30, gt=0)
    mastered_threshold: int = Field(default=30, gt=0)
    choice_to_input_threshold: int = Field(default=3, gt=0)

    # Notifications
    notification_enabled: bool = True
    notification_interval_hours: int = Field(default=6, gt=0)
    notification_time_start: str = "07:00"
    notification_time_end: str = "23:00"
    timezone: str = "Europe/Moscow"

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_file: str = "logs/bot.log"

    # Development
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("telegram_bot_token", "llm_api_key", "database_url")
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        """Validate that required string fields are not empty."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v

    @field_validator("notification_time_start", "notification_time_end")
    @classmethod
    def validate_time_format(cls, v: str, info) -> str:
        """Validate time format is HH:MM (00:00 to 23:59)."""
        time_pattern = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
        if not time_pattern.match(v):
            raise ValueError(
                f"{info.field_name} must be in HH:MM format (00:00 to 23:59)"
            )
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone is a valid IANA timezone name."""
        if v not in pytz.all_timezones:
            raise ValueError(
                f"Invalid timezone: {v}. Must be a valid IANA timezone name."
            )
        return v


# Singleton instance
settings = Settings()
