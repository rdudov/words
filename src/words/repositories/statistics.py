"""
Statistics repository for the Words application.

Provides data access for WordStatistics model.
"""

from sqlalchemy import select, and_

from .base import BaseRepository
from src.words.models.statistics import WordStatistics


class StatisticsRepository(BaseRepository[WordStatistics]):
    """Word statistics operations."""

    def __init__(self, session):
        super().__init__(session, WordStatistics)

    async def get_or_create_stat(
        self,
        user_word_id: int,
        direction: str,
        test_type: str
    ) -> WordStatistics:
        """Get existing stat or create new one."""
        result = await self.session.execute(
            select(WordStatistics).where(
                and_(
                    WordStatistics.user_word_id == user_word_id,
                    WordStatistics.direction == direction,
                    WordStatistics.test_type == test_type
                )
            )
        )

        stat = result.scalar_one_or_none()

        if not stat:
            stat = WordStatistics(
                user_word_id=user_word_id,
                direction=direction,
                test_type=test_type
            )
            self.session.add(stat)
            await self.session.flush()

        return stat

    async def update_stat(
        self,
        user_word_id: int,
        direction: str,
        test_type: str,
        is_correct: bool
    ) -> WordStatistics:
        """Update statistics after an attempt."""
        stat = await self.get_or_create_stat(
            user_word_id, direction, test_type
        )

        stat.total_attempts += 1

        if is_correct:
            stat.correct_count += 1
            stat.total_correct += 1
        else:
            stat.correct_count = 0
            stat.total_errors += 1

        await self.session.flush()
        return stat
