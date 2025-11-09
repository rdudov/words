"""
Bot handlers package.

This package contains all Telegram bot message and callback handlers
organized by functionality (start/registration, word management, lessons, etc.).
"""

from src.words.bot.handlers.start import router as start_router

__all__ = ["start_router"]
