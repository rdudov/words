"""
Validation service for user answers.

Implements a three-level validation pipeline:
1) Exact match
2) Fuzzy match (typos)
3) LLM validation (synonyms, alternative forms)
"""

from dataclasses import dataclass

from src.words.config.constants import ValidationMethod, FUZZY_MATCH_THRESHOLD
from src.words.services.translation import TranslationService
from src.words.utils.logger import get_event_logger
from src.words.utils.string_utils import FuzzyMatcher

logger = get_event_logger(__name__)


@dataclass
class ValidationResult:
    """Answer validation result."""

    is_correct: bool
    method: str
    feedback: str | None = None


class ValidationService:
    """Three-level answer validation service."""

    def __init__(
        self,
        translation_service: TranslationService,
        fuzzy_threshold: int = FUZZY_MATCH_THRESHOLD
    ):
        self.translation_service = translation_service
        self.fuzzy_threshold = fuzzy_threshold

    async def validate_answer(
        self,
        user_answer: str,
        expected_answer: str,
        alternative_answers: list[str] | None = None,
        word_id: int | None = None,
        direction: str | None = None,
        question: str | None = None,
        source_lang: str | None = None,
        target_lang: str | None = None
    ) -> ValidationResult:
        """
        Validate an answer using exact/fuzzy/LLM checks.

        Args:
            user_answer: User's answer
            expected_answer: Expected correct answer
            alternative_answers: Additional acceptable answers
            word_id: Word id for caching LLM validation
            direction: Translation direction string
            question: Original question text
            source_lang: Source language code
            target_lang: Target language code
        """
        user = FuzzyMatcher.normalize_text(user_answer)
        expected = FuzzyMatcher.normalize_text(expected_answer)
        alternatives = [
            FuzzyMatcher.normalize_text(a)
            for a in (alternative_answers or [])
        ]

        # Level 1: Exact match
        if self._exact_match(user, expected, alternatives):
            logger.debug(
                "validation_exact_match",
                user_answer=user_answer,
                expected=expected_answer
            )
            return ValidationResult(
                is_correct=True,
                method=ValidationMethod.EXACT.value
            )

        # Level 2: Fuzzy match (typo)
        if self._fuzzy_match(user, expected):
            logger.debug(
                "validation_fuzzy_match",
                user_answer=user_answer,
                expected=expected_answer,
                distance=FuzzyMatcher.levenshtein_distance(user, expected)
            )
            return ValidationResult(
                is_correct=True,
                method=ValidationMethod.FUZZY.value,
                feedback=f"Small typo detected. Expected: {expected_answer}"
            )

        # Level 3: LLM validation (if context is available)
        if word_id and direction and question and source_lang and target_lang:
            return await self._llm_validate(
                question=question,
                expected_answer=expected_answer,
                user_answer=user_answer,
                source_lang=source_lang,
                target_lang=target_lang,
                word_id=word_id,
                direction=direction
            )

        # No LLM validation possible - reject
        return ValidationResult(
            is_correct=False,
            method=ValidationMethod.EXACT.value,
            feedback=f"Incorrect. Expected: {expected_answer}"
        )

    def _exact_match(
        self,
        user: str,
        expected: str,
        alternatives: list[str]
    ) -> bool:
        """Check exact match."""
        return user == expected or user in alternatives

    def _fuzzy_match(self, user: str, expected: str) -> bool:
        """Check fuzzy match (typo)."""
        return FuzzyMatcher.is_typo(user, expected, self.fuzzy_threshold)

    async def _llm_validate(
        self,
        question: str,
        expected_answer: str,
        user_answer: str,
        source_lang: str,
        target_lang: str,
        word_id: int,
        direction: str
    ) -> ValidationResult:
        """LLM-based validation."""
        logger.info(
            "validation_llm_call",
            word_id=word_id,
            user_answer=user_answer,
            expected=expected_answer
        )

        try:
            is_correct, comment = await self.translation_service.validate_answer_with_llm(
                question=question,
                expected=expected_answer,
                user_answer=user_answer,
                source_lang=source_lang,
                target_lang=target_lang,
                word_id=word_id,
                direction=direction
            )

            return ValidationResult(
                is_correct=is_correct,
                method=ValidationMethod.LLM.value,
                feedback=comment
            )

        except Exception as e:
            logger.error(
                "llm_validation_failed",
                word_id=word_id,
                error=str(e)
            )
            # Fallback: reject answer
            return ValidationResult(
                is_correct=False,
                method=ValidationMethod.EXACT.value,
                feedback=f"Incorrect. Expected: {expected_answer}"
            )
