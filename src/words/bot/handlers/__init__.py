"""
Bot handlers package.

This package contains all Telegram bot message and callback handlers
organized by functionality (start/registration, word management, lessons, etc.).
"""

from src.words.bot.handlers.lesson import router as lesson_router
from src.words.bot.handlers.settings import router as settings_router
from src.words.bot.handlers.start import router as start_router
from src.words.bot.handlers.stats import router as stats_router
from src.words.bot.handlers.words import router as words_router

__all__ = [
    "lesson_router",
    "settings_router",
    "start_router",
    "stats_router",
    "words_router",
]
