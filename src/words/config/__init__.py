"""
Configuration module for the Words application.

This module provides:
- Settings: Environment-based configuration using pydantic-settings
- Constants: Application-wide constants for statuses, types, and validation
"""

from .settings import Settings, settings
from .constants import (
    WordStatus,
    TestType,
    Direction,
    ValidationMethod,
    CEFR_LEVELS,
    SUPPORTED_LANGUAGES,
    FUZZY_MATCH_THRESHOLD,
)

__all__ = [
    "Settings",
    "settings",
    "WordStatus",
    "TestType",
    "Direction",
    "ValidationMethod",
    "CEFR_LEVELS",
    "SUPPORTED_LANGUAGES",
    "FUZZY_MATCH_THRESHOLD",
]
