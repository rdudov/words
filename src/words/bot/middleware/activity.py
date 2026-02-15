"""Middleware for tracking user activity timestamps."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware

from src.words.infrastructure.database import get_session
from src.words.repositories.user import UserRepository

logger = logging.getLogger(__name__)


class ActivityTrackingMiddleware(BaseMiddleware):
    """Update user's last activity timestamp for incoming updates."""

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        from_user = getattr(event, "from_user", None)
        user_id = getattr(from_user, "id", None)

        if user_id is not None:
            try:
                async with get_session() as session:
                    repo = UserRepository(session)
                    await repo.update_last_active(user_id)
            except Exception:
                logger.exception("activity_update_failed: user_id=%s", user_id)

        return await handler(event, data)
