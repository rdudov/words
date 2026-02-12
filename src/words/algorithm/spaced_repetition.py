"""Spaced repetition algorithm utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.words.config.constants import ValidationMethod


@dataclass
class SpacedRepetitionResult:
    """Result of spaced repetition calculation."""

    next_interval_days: int
    next_review_at: datetime
    easiness_factor: float


class SpacedRepetition:
    """
    SM-2 Spaced Repetition Algorithm.

    Based on SuperMemo 2 algorithm:
    https://www.supermemo.com/en/archives1990-2015/english/ol/sm2
    """

    MIN_EASINESS_FACTOR = 1.3
    DEFAULT_EASINESS_FACTOR = 2.5

    def calculate_next_review(
        self,
        current_interval_days: int,
        easiness_factor: float,
        is_correct: bool,
        quality: int = 3
    ) -> SpacedRepetitionResult:
        """
        Calculate next review interval and updated easiness factor.

        Args:
            current_interval_days: Current interval in days (0 for new words)
            easiness_factor: Current easiness factor (2.5 default)
            is_correct: Whether answer was correct
            quality: Quality of recall (0-5, where 3+ is correct)

        Returns:
            SpacedRepetitionResult with next interval and EF
        """
        if not is_correct or quality < 3:
            next_interval = 1
            new_ef = max(self.MIN_EASINESS_FACTOR, easiness_factor - 0.2)
        else:
            new_ef = self._calculate_new_ef(easiness_factor, quality)

            if current_interval_days == 0:
                next_interval = 1
            elif current_interval_days == 1:
                next_interval = 6
            else:
                next_interval = int(current_interval_days * new_ef)

        next_review_at = datetime.now(timezone.utc) + timedelta(days=next_interval)

        return SpacedRepetitionResult(
            next_interval_days=next_interval,
            next_review_at=next_review_at,
            easiness_factor=new_ef
        )

    def _calculate_new_ef(self, current_ef: float, quality: int) -> float:
        """
        Calculate new easiness factor.

        Formula: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        """
        new_ef = current_ef + (
            0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        )

        return max(self.MIN_EASINESS_FACTOR, new_ef)

    def quality_from_correctness(self, is_correct: bool, validation_method: str) -> int:
        """
        Convert validation result to quality score (0-5).

        - Exact match: 5
        - Fuzzy match (typo): 4
        - LLM accepted: 3
        - Wrong: 0
        """
        if not is_correct:
            return 0

        if validation_method == ValidationMethod.EXACT.value:
            return 5
        if validation_method == ValidationMethod.FUZZY.value:
            return 4
        if validation_method == ValidationMethod.LLM.value:
            return 3

        return 3


async def update_review_schedule(
    user_word,
    is_correct: bool,
    validation_method: str,
    sr_algorithm: SpacedRepetition | None = None
) -> None:
    """Update user word review schedule after attempt."""
    if sr_algorithm is None:
        sr_algorithm = SpacedRepetition()

    current_interval = user_word.review_interval or 0
    easiness_factor = (
        user_word.easiness_factor or SpacedRepetition.DEFAULT_EASINESS_FACTOR
    )
    quality = sr_algorithm.quality_from_correctness(is_correct, validation_method)

    result = sr_algorithm.calculate_next_review(
        current_interval_days=current_interval,
        easiness_factor=easiness_factor,
        is_correct=is_correct,
        quality=quality
    )

    user_word.review_interval = result.next_interval_days
    user_word.easiness_factor = result.easiness_factor
    user_word.next_review_at = result.next_review_at
