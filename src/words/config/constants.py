"""
Application-wide constants.

This module defines constants used throughout the Words application,
including word statuses, test types, translation directions, and validation methods.
"""

from enum import Enum
from types import MappingProxyType


class WordStatus(str, Enum):
    """Word learning status constants."""

    NEW = "new"
    LEARNING = "learning"
    REVIEWING = "reviewing"
    MASTERED = "mastered"


class TestType(str, Enum):
    """Test type constants for word practice."""

    MULTIPLE_CHOICE = "multiple_choice"
    INPUT = "input"


class Direction(str, Enum):
    """Translation direction constants."""

    NATIVE_TO_FOREIGN = "native_to_foreign"
    FOREIGN_TO_NATIVE = "foreign_to_native"


class ValidationMethod(str, Enum):
    """Answer validation method constants."""

    EXACT = "exact"
    FUZZY = "fuzzy"
    LLM = "llm"


# CEFR Levels (immutable tuple)
CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")

# Supported Languages (ISO 639-1 codes) - immutable mapping
SUPPORTED_LANGUAGES = MappingProxyType({
    "en": "English",
    "ru": "Русский",
    "es": "Español"
})

# Fuzzy Matching
FUZZY_MATCH_THRESHOLD = 2  # Levenshtein distance
