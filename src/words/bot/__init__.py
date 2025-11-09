"""Telegram bot package.

This package contains all bot-related components including handlers,
state machines, and middleware.
"""

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.words.config.settings import settings
from src.words.utils.logger import logger
from .states import (
    AddWordStates,
    LessonStates,
    RegistrationStates,
)


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
    from src.words.bot.handlers import start_router, words_router

    dp.include_router(start_router)
    dp.include_router(words_router)

    logger.info("Bot initialized")

    return bot, dp


__all__ = [
    "RegistrationStates",
    "AddWordStates",
    "LessonStates",
    "setup_bot",
]
