"""Scheduler infrastructure for periodic jobs."""

from __future__ import annotations

import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.words.config.settings import Settings
from src.words.infrastructure.database import get_session
from src.words.repositories.user import UserRepository
from src.words.services.notification import NotificationService

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """APScheduler wrapper for notification jobs."""

    def __init__(self, bot: Bot, settings: Settings):
        self.bot = bot
        self.settings = settings
        self.scheduler = AsyncIOScheduler(timezone=settings.timezone)
        self._is_setup = False

    def setup(self) -> None:
        """Configure scheduled jobs."""
        if self._is_setup:
            return

        self.scheduler.add_job(
            self._send_notifications,
            trigger=IntervalTrigger(minutes=15),
            id="send_notifications",
            name="Send inactive-user reminders",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self._is_setup = True
        logger.info("scheduler_configured")

    def start(self) -> None:
        """Start scheduler if notifications are enabled."""
        if not self.settings.notification_enabled:
            logger.info("scheduler_not_started_notifications_disabled")
            return

        if not self._is_setup:
            self.setup()

        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("scheduler_started")

    def shutdown(self) -> None:
        """Gracefully stop scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("scheduler_stopped")

    async def _send_notifications(self) -> None:
        """Run notification job."""
        try:
            async with get_session() as session:
                service = NotificationService(
                    user_repo=UserRepository(session),
                    bot=self.bot,
                    inactive_hours=self.settings.notification_interval_hours,
                    time_start=self.settings.notification_time_start,
                    time_end=self.settings.notification_time_end,
                    timezone=self.settings.timezone,
                )
                await service.check_and_send_notifications()
        except Exception:
            logger.exception("notification_job_failed")
