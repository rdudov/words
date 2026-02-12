"""Telegram bot package.

This package contains all bot-related components including handlers,
state machines, and middleware.
"""

import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.words.config.settings import settings
from .states import (
    AddWordStates,
    LessonStates,
    RegistrationStates,
)

logger = logging.getLogger(__name__)


async def setup_bot() -> tuple[Bot, Dispatcher]:
    """
    Initialize bot and dispatcher with all handlers.

    Creates a Bot instance with HTML parse mode and a Dispatcher
    with memory storage. Registers all application routers.

    Returns:
        tuple[Bot, Dispatcher]: Configured bot and dispatcher instances
    """
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register handlers
    # Order matters: more specific handlers (with StateFilter) must be first
    from src.words.bot.handlers import lesson_router, start_router, words_router

    dp.include_router(lesson_router)  # First: has StateFilter conditions
    dp.include_router(words_router)
    dp.include_router(start_router)

    logger.info("Bot initialized")

    return bot, dp


__all__ = [
    "RegistrationStates",
    "AddWordStates",
    "LessonStates",
    "setup_bot",
]
