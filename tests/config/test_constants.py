"""Tests for constants module."""

import pytest
from enum import Enum
from types import MappingProxyType

from words.config.constants import (
    WordStatus,
    TestType,
    Direction,
    ValidationMethod,
    CEFR_LEVELS,
    SUPPORTED_LANGUAGES,
    FUZZY_MATCH_THRESHOLD,
)


class TestWordStatus:
    """Test suite for WordStatus constants."""

    def test_word_status_values(self):
        """Test that WordStatus has correct values."""
        assert WordStatus.NEW == "new"
        assert WordStatus.LEARNING == "learning"
        assert WordStatus.REVIEWING == "reviewing"
        assert WordStatus.MASTERED == "mastered"

    def test_word_status_attributes_exist(self):
        """Test that all expected WordStatus attributes exist."""
        assert hasattr(WordStatus, "NEW")
        assert hasattr(WordStatus, "LEARNING")
        assert hasattr(WordStatus, "REVIEWING")
        assert hasattr(WordStatus, "MASTERED")

    def test_word_status_is_enum(self):
        """Test that WordStatus is an Enum."""
        assert issubclass(WordStatus, Enum)

    def test_word_status_is_string_comparable(self):
        """Test that WordStatus can be compared to strings."""
        assert WordStatus.NEW == "new"
        assert WordStatus.NEW.value == "new"


class TestTestType:
    """Test suite for TestType constants."""

    def test_test_type_values(self):
        """Test that TestType has correct values."""
        assert TestType.MULTIPLE_CHOICE == "multiple_choice"
        assert TestType.INPUT == "input"

    def test_test_type_attributes_exist(self):
        """Test that all expected TestType attributes exist."""
        assert hasattr(TestType, "MULTIPLE_CHOICE")
        assert hasattr(TestType, "INPUT")

    def test_test_type_is_enum(self):
        """Test that TestType is an Enum."""
        assert issubclass(TestType, Enum)


class TestDirection:
    """Test suite for Direction constants."""

    def test_direction_values(self):
        """Test that Direction has correct values."""
        assert Direction.NATIVE_TO_FOREIGN == "native_to_foreign"
        assert Direction.FOREIGN_TO_NATIVE == "foreign_to_native"

    def test_direction_attributes_exist(self):
        """Test that all expected Direction attributes exist."""
        assert hasattr(Direction, "NATIVE_TO_FOREIGN")
        assert hasattr(Direction, "FOREIGN_TO_NATIVE")

    def test_direction_is_enum(self):
        """Test that Direction is an Enum."""
        assert issubclass(Direction, Enum)


class TestValidationMethod:
    """Test suite for ValidationMethod constants."""

    def test_validation_method_values(self):
        """Test that ValidationMethod has correct values."""
        assert ValidationMethod.EXACT == "exact"
        assert ValidationMethod.FUZZY == "fuzzy"
        assert ValidationMethod.LLM == "llm"

    def test_validation_method_attributes_exist(self):
        """Test that all expected ValidationMethod attributes exist."""
        assert hasattr(ValidationMethod, "EXACT")
        assert hasattr(ValidationMethod, "FUZZY")
        assert hasattr(ValidationMethod, "LLM")

    def test_validation_method_is_enum(self):
        """Test that ValidationMethod is an Enum."""
        assert issubclass(ValidationMethod, Enum)


class TestCEFRLevels:
    """Test suite for CEFR levels constant."""

    def test_cefr_levels_content(self):
        """Test that CEFR_LEVELS contains correct values."""
        assert CEFR_LEVELS == ("A1", "A2", "B1", "B2", "C1", "C2")

    def test_cefr_levels_type(self):
        """Test that CEFR_LEVELS is a tuple (immutable)."""
        assert isinstance(CEFR_LEVELS, tuple)

    def test_cefr_levels_count(self):
        """Test that CEFR_LEVELS has 6 levels."""
        assert len(CEFR_LEVELS) == 6

    def test_cefr_levels_order(self):
        """Test that CEFR_LEVELS are in correct order."""
        expected_order = ("A1", "A2", "B1", "B2", "C1", "C2")
        assert CEFR_LEVELS == expected_order

    def test_cefr_levels_immutable(self):
        """Test that CEFR_LEVELS cannot be modified."""
        with pytest.raises(TypeError):
            CEFR_LEVELS[0] = "X1"


class TestSupportedLanguages:
    """Test suite for supported languages constant."""

    def test_supported_languages_content(self):
        """Test that SUPPORTED_LANGUAGES contains correct entries."""
        assert "en" in SUPPORTED_LANGUAGES
        assert "ru" in SUPPORTED_LANGUAGES
        assert "es" in SUPPORTED_LANGUAGES
        assert SUPPORTED_LANGUAGES["en"] == "English"
        assert SUPPORTED_LANGUAGES["ru"] == "Русский"
        assert SUPPORTED_LANGUAGES["es"] == "Español"

    def test_supported_languages_type(self):
        """Test that SUPPORTED_LANGUAGES is a MappingProxyType (immutable)."""
        assert isinstance(SUPPORTED_LANGUAGES, MappingProxyType)

    def test_supported_languages_count(self):
        """Test that SUPPORTED_LANGUAGES has 3 languages."""
        assert len(SUPPORTED_LANGUAGES) == 3

    def test_supported_languages_keys_are_iso_codes(self):
        """Test that language keys are 2-letter ISO 639-1 codes."""
        for code in SUPPORTED_LANGUAGES.keys():
            assert isinstance(code, str)
            assert len(code) == 2
            assert code.islower()

    def test_supported_languages_immutable(self):
        """Test that SUPPORTED_LANGUAGES cannot be modified."""
        with pytest.raises(TypeError):
            SUPPORTED_LANGUAGES["fr"] = "Français"


class TestFuzzyMatchThreshold:
    """Test suite for fuzzy match threshold constant."""

    def test_fuzzy_match_threshold_value(self):
        """Test that FUZZY_MATCH_THRESHOLD has correct value."""
        assert FUZZY_MATCH_THRESHOLD == 2

    def test_fuzzy_match_threshold_type(self):
        """Test that FUZZY_MATCH_THRESHOLD is an integer."""
        assert isinstance(FUZZY_MATCH_THRESHOLD, int)

    def test_fuzzy_match_threshold_positive(self):
        """Test that FUZZY_MATCH_THRESHOLD is positive."""
        assert FUZZY_MATCH_THRESHOLD > 0


class TestConstantsImportability:
    """Test suite for verifying constants can be imported from package."""

    def test_import_from_config_package(self):
        """Test that all constants can be imported from words.config."""
        from words.config import (
            WordStatus,
            TestType,
            Direction,
            ValidationMethod,
            CEFR_LEVELS,
            SUPPORTED_LANGUAGES,
            FUZZY_MATCH_THRESHOLD,
        )

        # Verify they are not None
        assert WordStatus is not None
        assert TestType is not None
        assert Direction is not None
        assert ValidationMethod is not None
        assert CEFR_LEVELS is not None
        assert SUPPORTED_LANGUAGES is not None
        assert FUZZY_MATCH_THRESHOLD is not None

    def test_constants_available_in_all(self):
        """Test that constants are in __all__ export list."""
        from words.config import __all__

        assert "WordStatus" in __all__
        assert "TestType" in __all__
        assert "Direction" in __all__
        assert "ValidationMethod" in __all__
        assert "CEFR_LEVELS" in __all__
        assert "SUPPORTED_LANGUAGES" in __all__
        assert "FUZZY_MATCH_THRESHOLD" in __all__
