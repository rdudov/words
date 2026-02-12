"""Difficulty adjustment utilities for word progression."""

from __future__ import annotations

from src.words.config.constants import TestType
from src.words.models.word import UserWord, WordStatusEnum
from src.words.utils.logger import get_event_logger

logger = get_event_logger(__name__)


class DifficultyAdjuster:
    """
    Manages word difficulty progression.

    Controls:
    - Test type progression (multiple choice → input)
    - Word status transitions
    - Mastery detection
    """

    def __init__(
        self,
        choice_to_input_threshold: int = 3,
        mastered_threshold: int = 30
    ) -> None:
        self.choice_to_input_threshold = choice_to_input_threshold
        self.mastered_threshold = mastered_threshold

    def determine_test_type(self, user_word: UserWord) -> str:
        """Determine appropriate test type for word."""
        stats = self._get_choice_stats(user_word)

        if stats and stats.correct_count >= self.choice_to_input_threshold:
            return TestType.INPUT.value

        return TestType.MULTIPLE_CHOICE.value

    def should_update_status(self, user_word: UserWord) -> bool:
        """Check if word status should be updated."""
        if self._is_mastered(user_word):
            return True

        if user_word.status == WordStatusEnum.NEW:
            return any(stat.total_attempts > 0 for stat in user_word.statistics)

        if user_word.status == WordStatusEnum.LEARNING:
            return any(stat.total_correct >= 5 for stat in user_word.statistics)

        return False

    def update_word_status(self, user_word: UserWord) -> str:
        """Update word status based on performance."""
        old_status = user_word.status

        if self._is_mastered(user_word):
            user_word.status = WordStatusEnum.MASTERED
            logger.info(
                "word_status_updated",
                user_word_id=user_word.user_word_id,
                old_status=old_status.value,
                new_status="mastered"
            )
            return user_word.status.value

        if user_word.status == WordStatusEnum.NEW:
            if any(stat.total_attempts > 0 for stat in user_word.statistics):
                user_word.status = WordStatusEnum.LEARNING

        elif user_word.status == WordStatusEnum.LEARNING:
            if any(stat.total_correct >= 5 for stat in user_word.statistics):
                user_word.status = WordStatusEnum.REVIEWING

        if old_status != user_word.status:
            logger.info(
                "word_status_updated",
                user_word_id=user_word.user_word_id,
                old_status=old_status.value,
                new_status=user_word.status.value
            )

        return user_word.status.value

    def _is_mastered(self, user_word: UserWord) -> bool:
        """Check if word is mastered."""
        for stat in user_word.statistics:
            if stat.correct_count >= self.mastered_threshold:
                return True

        return False

    def _get_choice_stats(self, user_word: UserWord):
        """Get multiple choice statistics for word."""
        for stat in user_word.statistics:
            if stat.test_type == TestType.MULTIPLE_CHOICE.value:
                return stat

        return None
