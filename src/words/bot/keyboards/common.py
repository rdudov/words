"""
Telegram keyboard builders.

This module provides builder functions for creating Telegram keyboards
including language selection, CEFR level selection, main menu, and confirmation dialogs.
"""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from src.words.config.constants import SUPPORTED_LANGUAGES, CEFR_LEVELS


def build_language_keyboard() -> InlineKeyboardMarkup:
    """
    Build keyboard for language selection.

    Creates an inline keyboard with buttons for each supported language.
    Each button triggers a callback with format: "select_language:{code}".

    Returns:
        InlineKeyboardMarkup: Keyboard with language selection buttons (2 per row).
    """
    builder = InlineKeyboardBuilder()

    for code, name in SUPPORTED_LANGUAGES.items():
        builder.button(text=name, callback_data=f"select_language:{code}")

    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()


def build_level_keyboard() -> InlineKeyboardMarkup:
    """
    Build keyboard for CEFR level selection.

    Creates an inline keyboard with buttons for each CEFR level (A1-C2).
    Each button triggers a callback with format: "select_level:{level}".

    Returns:
        InlineKeyboardMarkup: Keyboard with CEFR level buttons (3 per row).
    """
    builder = InlineKeyboardBuilder()

    for level in CEFR_LEVELS:
        builder.button(text=level, callback_data=f"select_level:{level}")

    builder.adjust(3)  # 3 buttons per row
    return builder.as_markup()


def build_main_menu() -> ReplyKeyboardMarkup:
    """
    Build main menu keyboard.

    Creates a reply keyboard with the main menu options:
    - Start Lesson
    - Add Word
    - Statistics
    - Settings

    Returns:
        ReplyKeyboardMarkup: Main menu keyboard with emoji buttons (2x2 layout).
    """
    builder = ReplyKeyboardBuilder()

    builder.button(text="📚 Start Lesson")
    builder.button(text="➕ Add Word")
    builder.button(text="📊 Statistics")
    builder.button(text="⚙️ Settings")

    builder.adjust(2, 2)  # 2 rows with 2 buttons each
    return builder.as_markup(resize_keyboard=True)


def build_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Build Yes/No confirmation keyboard.

    Creates an inline keyboard with Yes and No buttons.
    Callbacks: "confirm:yes" and "confirm:no".

    Returns:
        InlineKeyboardMarkup: Confirmation keyboard with Yes/No buttons.
    """
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Yes", callback_data="confirm:yes")
    builder.button(text="❌ No", callback_data="confirm:no")

    builder.adjust(2)
    return builder.as_markup()
