"""Adaptive word selection logic for lessons."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.words.config.constants import TestType
from src.words.models.word import UserWord, WordStatusEnum


@dataclass
class ScoredWord:
    """Word with calculated priority score."""

    user_word: UserWord
    priority_score: float


class WordSelector:
    """
    Adaptive word selection algorithm.

    Selects words for lessons based on:
    - Spaced repetition (due for review)
    - Error rate (struggling words)
    - Word status (new, learning, reviewing)
    - Test type readiness (multiple choice → input)
    """

    def __init__(self, words_per_lesson: int = 30, input_ratio: float = 0.5) -> None:
        self.words_per_lesson = words_per_lesson
        self.input_ratio = input_ratio

    async def select_words_for_lesson(
        self,
        candidate_words: list[UserWord]
    ) -> list[UserWord]:
        """Select words for lesson using adaptive algorithm."""
        scored_words = [
            ScoredWord(word, self._calculate_priority(word))
            for word in candidate_words
        ]

        scored_words.sort(key=lambda item: item.priority_score, reverse=True)

        input_ready = [
            scored.user_word
            for scored in scored_words
            if self._is_input_ready(scored.user_word)
        ]
        choice_words = [
            scored.user_word
            for scored in scored_words
            if not self._is_input_ready(scored.user_word)
        ]

        selected: list[UserWord] = []

        input_target = int(self.words_per_lesson * self.input_ratio)
        selected.extend(input_ready[:input_target])

        remaining = self.words_per_lesson - len(selected)
        selected.extend(choice_words[:remaining])

        if len(selected) < self.words_per_lesson:
            additional = self.words_per_lesson - len(selected)
            selected.extend(input_ready[input_target:input_target + additional])

        return selected[:self.words_per_lesson]

    def _calculate_priority(self, user_word: UserWord) -> float:
        """
        Calculate priority score for word.

        Higher score = higher priority = should be shown sooner.
        """
        score = 0.0
        now = datetime.now(timezone.utc)

        if user_word.next_review_at:
            days_overdue = (now - user_word.next_review_at).days
            if days_overdue > 0:
                score += days_overdue * 10

        error_rate = self._calculate_error_rate(user_word)
        score += error_rate * 5

        if user_word.status == WordStatusEnum.NEW:
            score += 15

        if user_word.last_reviewed_at:
            days_since = (now - user_word.last_reviewed_at).days
            score += min(days_since, 7)
        else:
            score += 7

        if user_word.status == WordStatusEnum.LEARNING:
            score += 3
        elif user_word.status == WordStatusEnum.REVIEWING:
            score += 1

        return score

    def _calculate_error_rate(self, user_word: UserWord) -> float:
        """Calculate error rate for word (0.0 - 1.0)."""
        if not user_word.statistics:
            return 0.0

        total_attempts = sum(stat.total_attempts for stat in user_word.statistics)
        total_errors = sum(stat.total_errors for stat in user_word.statistics)

        if total_attempts == 0:
            return 0.0

        return total_errors / total_attempts

    def _is_input_ready(self, user_word: UserWord) -> bool:
        """
        Check if word is ready for input-type testing.

        Criteria: 3+ consecutive correct answers in multiple choice.
        """
        if not user_word.statistics:
            return False

        for stat in user_word.statistics:
            if (
                stat.test_type == TestType.MULTIPLE_CHOICE.value
                and stat.correct_count >= 3
            ):
                return True

        return False
