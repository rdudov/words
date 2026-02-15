"""
Entry point for the Words application.

This module allows the package to be executed as a script:
    python -m src.words
"""

import asyncio
import sys
from pathlib import Path

# Ensure the parent directory is in the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
from src.words.bot import setup_bot
from src.words.config.settings import settings
from src.words.infrastructure.database import init_db, close_db
from src.words.infrastructure.scheduler import NotificationScheduler
from src.words.utils.logger import setup_logging

logger = logging.getLogger(__name__)


async def main():
    """
    Main entry point for the bot application.

    Initializes the database, sets up the bot and dispatcher,
    and starts polling for updates. Handles graceful shutdown
    on interrupt.
    """
    # Initialize logging FIRST
    setup_logging()

    logger.info("Starting bot...")

    # Initialize database
    await init_db()

    # Setup bot
    bot, dp = await setup_bot()
    scheduler = NotificationScheduler(bot, settings)
    scheduler.setup()
    scheduler.start()

    try:
        # Start polling
        logger.info("Bot is running. Press Ctrl+C to stop.")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()
        await close_db()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
