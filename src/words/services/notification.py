"""Notification service for push reminders."""

from __future__ import annotations

import logging
from datetime import datetime

import pytz
from aiogram import Bot

from src.words.bot.keyboards.common import build_main_menu
from src.words.repositories.user import UserRepository

logger = logging.getLogger(__name__)


class NotificationService:
    """Push notification management."""

    def __init__(
        self,
        user_repo: UserRepository,
        bot: Bot,
        inactive_hours: int = 6,
        time_start: str = "07:00",
        time_end: str = "23:00",
        timezone: str = "Europe/Moscow",
    ):
        self.user_repo = user_repo
        self.bot = bot
        self.inactive_hours = inactive_hours
        self.time_start = time_start
        self.time_end = time_end
        self.timezone = pytz.timezone(timezone)

    async def check_and_send_notifications(self) -> None:
        """Check eligible users and send reminders."""
        now = datetime.now(self.timezone)
        if not self._is_within_window(now):
            logger.debug(
                "notification_outside_window: local_time=%s window=%s-%s",
                now.strftime("%H:%M"),
                self.time_start,
                self.time_end,
            )
            return

        users = await self.user_repo.get_users_for_notification(
            inactive_hours=self.inactive_hours,
            current_hour=now.hour,
        )

        logger.info(
            "notification_check: users_count=%d local_time=%s",
            len(users),
            now.strftime("%H:%M"),
        )

        sent_count = 0
        for user in users:
            try:
                await self._send_reminder(user.user_id)
                # Prevent reminder spam on each 15-minute scheduler tick.
                await self.user_repo.update_last_active(user.user_id)
                sent_count += 1
            except Exception:
                logger.exception("notification_send_failed: user_id=%d", user.user_id)

        logger.info("notifications_sent: count=%d", sent_count)

    async def _send_reminder(self, user_id: int) -> None:
        """Send a reminder message to the user."""
        await self.bot.send_message(
            chat_id=user_id,
            text=(
                "👋 Time to practice!\n\n"
                "Keep your learning streak going.\n"
                "Start a lesson now: 📚 Start Lesson"
            ),
            reply_markup=build_main_menu(),
        )
        logger.info("notification_sent: user_id=%d", user_id)

    def _is_within_window(self, now: datetime) -> bool:
        """Check if now is within [start, end) notification window."""
        start_minutes = self._time_to_minutes(self.time_start)
        end_minutes = self._time_to_minutes(self.time_end)
        now_minutes = now.hour * 60 + now.minute

        if start_minutes == end_minutes:
            return True

        if start_minutes < end_minutes:
            return start_minutes <= now_minutes < end_minutes

        # Overnight window, e.g. 22:00-07:00
        return now_minutes >= start_minutes or now_minutes < end_minutes

    @staticmethod
    def _time_to_minutes(value: str) -> int:
        """Convert HH:MM to minutes since midnight."""
        hour_str, minute_str = value.split(":", 1)
        return int(hour_str) * 60 + int(minute_str)
