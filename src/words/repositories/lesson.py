"""
Lesson repositories for the Words application.

Provides data access for Lesson and LessonAttempt models.
"""

from datetime import datetime, timezone

from sqlalchemy import select, and_, desc, func

from .base import BaseRepository
from src.words.models.lesson import Lesson, LessonAttempt


class LessonRepository(BaseRepository[Lesson]):
    """Lesson database operations."""

    def __init__(self, session):
        super().__init__(session, Lesson)

    async def get_active_lesson(self, profile_id: int) -> Lesson | None:
        """Get active (incomplete) lesson for a profile."""
        result = await self.session.execute(
            select(Lesson).where(
                and_(
                    Lesson.profile_id == profile_id,
                    Lesson.completed_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_recent_lessons(
        self,
        profile_id: int,
        limit: int = 10
    ) -> list[Lesson]:
        """Get recent completed lessons."""
        result = await self.session.execute(
            select(Lesson).where(
                and_(
                    Lesson.profile_id == profile_id,
                    Lesson.completed_at.is_not(None)
                )
            ).order_by(desc(Lesson.completed_at)).limit(limit)
        )
        return list(result.scalars().all())

    async def count_lessons_today(self, profile_id: int) -> int:
        """Count lessons completed today (UTC)."""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        result = await self.session.execute(
            select(func.count(Lesson.lesson_id)).where(
                and_(
                    Lesson.profile_id == profile_id,
                    Lesson.completed_at >= today_start
                )
            )
        )
        return result.scalar_one()


class LessonAttemptRepository(BaseRepository[LessonAttempt]):
    """Lesson attempt operations."""

    def __init__(self, session):
        super().__init__(session, LessonAttempt)

    async def get_lesson_attempts(
        self,
        lesson_id: int
    ) -> list[LessonAttempt]:
        """Get all attempts for a lesson."""
        result = await self.session.execute(
            select(LessonAttempt).where(
                LessonAttempt.lesson_id == lesson_id
            ).order_by(LessonAttempt.attempted_at)
        )
        return list(result.scalars().all())
