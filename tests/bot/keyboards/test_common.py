"""
Tests for common keyboard builders.

This module tests all keyboard builder functions to ensure they:
- Return correct keyboard types
- Have proper button counts and layouts
- Format callback data correctly
- Can be imported from the keyboards package
"""

import pytest
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from src.words.bot.keyboards import (
    build_confirmation_keyboard,
    build_language_keyboard,
    build_level_keyboard,
    build_main_menu,
)
from src.words.bot.keyboards.common import (
    build_confirmation_keyboard as common_build_confirmation_keyboard,
    build_language_keyboard as common_build_language_keyboard,
    build_level_keyboard as common_build_level_keyboard,
    build_main_menu as common_build_main_menu,
)
from src.words.config.constants import CEFR_LEVELS, SUPPORTED_LANGUAGES


class TestBuildLanguageKeyboard:
    """Tests for build_language_keyboard function."""

    def test_returns_inline_keyboard_markup(self):
        """Test that function returns InlineKeyboardMarkup type."""
        keyboard = build_language_keyboard()
        assert isinstance(keyboard, InlineKeyboardMarkup)

    def test_has_correct_number_of_buttons(self):
        """Test that keyboard has one button per supported language."""
        keyboard = build_language_keyboard()
        total_buttons = sum(len(row) for row in keyboard.inline_keyboard)
        assert total_buttons == len(SUPPORTED_LANGUAGES)

    def test_buttons_have_correct_text(self):
        """Test that buttons display correct language names."""
        keyboard = build_language_keyboard()
        button_texts = {
            button.text for row in keyboard.inline_keyboard for button in row
        }
        expected_texts = set(SUPPORTED_LANGUAGES.values())
        assert button_texts == expected_texts

    def test_callback_data_format(self):
        """Test that callback data follows 'select_language:{code}' format."""
        keyboard = build_language_keyboard()
        for row in keyboard.inline_keyboard:
            for button in row:
                assert button.callback_data.startswith("select_language:")
                lang_code = button.callback_data.split(":")[1]
                assert lang_code in SUPPORTED_LANGUAGES

    def test_button_layout_two_per_row(self):
        """Test that buttons are arranged 2 per row."""
        keyboard = build_language_keyboard()
        # Most rows should have 2 buttons (last row may have fewer if odd total)
        row_counts = [len(row) for row in keyboard.inline_keyboard]
        # All rows except possibly the last should have 2 buttons
        for count in row_counts[:-1]:
            assert count == 2
        # Last row should have 1 or 2 buttons
        assert 1 <= row_counts[-1] <= 2

    def test_callback_data_matches_button_text(self):
        """Test that callback data language codes match button text languages."""
        keyboard = build_language_keyboard()
        for row in keyboard.inline_keyboard:
            for button in row:
                lang_code = button.callback_data.split(":")[1]
                expected_name = SUPPORTED_LANGUAGES[lang_code]
                assert button.text == expected_name


class TestBuildLevelKeyboard:
    """Tests for build_level_keyboard function."""

    def test_returns_inline_keyboard_markup(self):
        """Test that function returns InlineKeyboardMarkup type."""
        keyboard = build_level_keyboard()
        assert isinstance(keyboard, InlineKeyboardMarkup)

    def test_has_correct_number_of_buttons(self):
        """Test that keyboard has one button per CEFR level."""
        keyboard = build_level_keyboard()
        total_buttons = sum(len(row) for row in keyboard.inline_keyboard)
        assert total_buttons == len(CEFR_LEVELS)

    def test_buttons_have_correct_text(self):
        """Test that buttons display correct CEFR levels."""
        keyboard = build_level_keyboard()
        button_texts = {
            button.text for row in keyboard.inline_keyboard for button in row
        }
        expected_texts = set(CEFR_LEVELS)
        assert button_texts == expected_texts

    def test_callback_data_format(self):
        """Test that callback data follows 'select_level:{level}' format."""
        keyboard = build_level_keyboard()
        for row in keyboard.inline_keyboard:
            for button in row:
                assert button.callback_data.startswith("select_level:")
                level = button.callback_data.split(":")[1]
                assert level in CEFR_LEVELS

    def test_button_layout_three_per_row(self):
        """Test that buttons are arranged 3 per row."""
        keyboard = build_level_keyboard()
        # With 6 CEFR levels and 3 per row, should have exactly 2 rows
        assert len(keyboard.inline_keyboard) == 2
        for row in keyboard.inline_keyboard:
            assert len(row) == 3

    def test_callback_data_matches_button_text(self):
        """Test that callback data levels match button text."""
        keyboard = build_level_keyboard()
        for row in keyboard.inline_keyboard:
            for button in row:
                level = button.callback_data.split(":")[1]
                assert button.text == level

    def test_levels_in_correct_order(self):
        """Test that CEFR levels appear in order A1, A2, B1, B2, C1, C2."""
        keyboard = build_level_keyboard()
        all_buttons = [
            button for row in keyboard.inline_keyboard for button in row
        ]
        button_texts = [button.text for button in all_buttons]
        assert button_texts == list(CEFR_LEVELS)


class TestBuildMainMenu:
    """Tests for build_main_menu function."""

    def test_returns_reply_keyboard_markup(self):
        """Test that function returns ReplyKeyboardMarkup type."""
        keyboard = build_main_menu()
        assert isinstance(keyboard, ReplyKeyboardMarkup)

    def test_has_correct_number_of_buttons(self):
        """Test that keyboard has 4 main menu buttons."""
        keyboard = build_main_menu()
        total_buttons = sum(len(row) for row in keyboard.keyboard)
        assert total_buttons == 4

    def test_buttons_have_correct_text(self):
        """Test that buttons have correct text with emojis."""
        keyboard = build_main_menu()
        button_texts = {
            button.text for row in keyboard.keyboard for button in row
        }
        expected_texts = {
            "📚 Start Lesson",
            "➕ Add Word",
            "📊 Statistics",
            "⚙️ Settings",
        }
        assert button_texts == expected_texts

    def test_button_layout_two_by_two(self):
        """Test that buttons are arranged in 2x2 grid."""
        keyboard = build_main_menu()
        assert len(keyboard.keyboard) == 2  # 2 rows
        for row in keyboard.keyboard:
            assert len(row) == 2  # 2 buttons per row

    def test_keyboard_is_resizable(self):
        """Test that resize_keyboard flag is set to True."""
        keyboard = build_main_menu()
        assert keyboard.resize_keyboard is True

    def test_button_order(self):
        """Test that buttons appear in expected order."""
        keyboard = build_main_menu()
        expected_order = [
            ["📚 Start Lesson", "➕ Add Word"],
            ["📊 Statistics", "⚙️ Settings"],
        ]
        for row_idx, row in enumerate(keyboard.keyboard):
            for button_idx, button in enumerate(row):
                assert button.text == expected_order[row_idx][button_idx]


class TestBuildConfirmationKeyboard:
    """Tests for build_confirmation_keyboard function."""

    def test_returns_inline_keyboard_markup(self):
        """Test that function returns InlineKeyboardMarkup type."""
        keyboard = build_confirmation_keyboard()
        assert isinstance(keyboard, InlineKeyboardMarkup)

    def test_has_correct_number_of_buttons(self):
        """Test that keyboard has exactly 2 buttons (Yes and No)."""
        keyboard = build_confirmation_keyboard()
        total_buttons = sum(len(row) for row in keyboard.inline_keyboard)
        assert total_buttons == 2

    def test_buttons_have_correct_text(self):
        """Test that buttons display 'Yes' and 'No' with emojis."""
        keyboard = build_confirmation_keyboard()
        button_texts = {
            button.text for row in keyboard.inline_keyboard for button in row
        }
        expected_texts = {"✅ Yes", "❌ No"}
        assert button_texts == expected_texts

    def test_callback_data_format(self):
        """Test that callback data follows 'confirm:{yes|no}' format."""
        keyboard = build_confirmation_keyboard()
        callback_data = {
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
        }
        expected_callbacks = {"confirm:yes", "confirm:no"}
        assert callback_data == expected_callbacks

    def test_button_layout_two_per_row(self):
        """Test that both buttons are in the same row."""
        keyboard = build_confirmation_keyboard()
        assert len(keyboard.inline_keyboard) == 1  # Single row
        assert len(keyboard.inline_keyboard[0]) == 2  # 2 buttons

    def test_yes_button_first(self):
        """Test that Yes button appears before No button."""
        keyboard = build_confirmation_keyboard()
        buttons = keyboard.inline_keyboard[0]
        assert buttons[0].text == "✅ Yes"
        assert buttons[1].text == "❌ No"


class TestPackageImports:
    """Tests for package-level imports."""

    def test_functions_exported_from_package(self):
        """Test that all functions can be imported from keyboards package."""
        # This test passes if imports at module level succeed
        assert callable(build_language_keyboard)
        assert callable(build_level_keyboard)
        assert callable(build_main_menu)
        assert callable(build_confirmation_keyboard)

    def test_functions_match_common_module(self):
        """Test that package exports match common module functions."""
        assert build_language_keyboard is common_build_language_keyboard
        assert build_level_keyboard is common_build_level_keyboard
        assert build_main_menu is common_build_main_menu
        assert build_confirmation_keyboard is common_build_confirmation_keyboard


class TestKeyboardIntegration:
    """Integration tests for keyboard functions."""

    def test_all_keyboards_can_be_created(self):
        """Test that all keyboard types can be created without errors."""
        keyboards = [
            build_language_keyboard(),
            build_level_keyboard(),
            build_main_menu(),
            build_confirmation_keyboard(),
        ]
        assert len(keyboards) == 4
        assert all(keyboard is not None for keyboard in keyboards)

    def test_inline_keyboards_have_buttons(self):
        """Test that all inline keyboards have at least one button."""
        inline_keyboards = [
            build_language_keyboard(),
            build_level_keyboard(),
            build_confirmation_keyboard(),
        ]
        for keyboard in inline_keyboards:
            assert len(keyboard.inline_keyboard) > 0
            assert all(len(row) > 0 for row in keyboard.inline_keyboard)

    def test_reply_keyboard_has_buttons(self):
        """Test that reply keyboard has at least one button."""
        keyboard = build_main_menu()
        assert len(keyboard.keyboard) > 0
        assert all(len(row) > 0 for row in keyboard.keyboard)

    def test_no_duplicate_callback_data_in_language_keyboard(self):
        """Test that language keyboard has unique callback data."""
        keyboard = build_language_keyboard()
        callback_data = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
        ]
        assert len(callback_data) == len(set(callback_data))

    def test_no_duplicate_callback_data_in_level_keyboard(self):
        """Test that level keyboard has unique callback data."""
        keyboard = build_level_keyboard()
        callback_data = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
        ]
        assert len(callback_data) == len(set(callback_data))
