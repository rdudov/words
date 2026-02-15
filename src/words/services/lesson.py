"""
Lesson service for orchestrating lesson flow.

Handles lesson creation, question generation, answer processing,
and lesson completion summaries.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import random

from src.words.algorithm.difficulty import DifficultyAdjuster
from src.words.algorithm.spaced_repetition import update_review_schedule
from src.words.algorithm.word_selector import WordSelector
from src.words.config.constants import Direction, TestType
from src.words.config.settings import settings
from src.words.models.lesson import Lesson, LessonAttempt
from src.words.models.word import UserWord, Word, WordStatusEnum
from src.words.repositories.lesson import LessonRepository, LessonAttemptRepository
from src.words.repositories.statistics import StatisticsRepository
from src.words.repositories.word import UserWordRepository, WordRepository
from src.words.services.validation import ValidationService
from src.words.utils.logger import get_event_logger

logger = get_event_logger(__name__)


@dataclass
class Question:
    """Lesson question."""

    user_word_id: int
    word_id: int
    question_text: str
    expected_answer: str
    alternative_answers: list[str]
    direction: str
    test_type: str
    source_language: str
    target_language: str
    options: list[str] | None = None


@dataclass
class AnswerResult:
    """Answer processing result."""

    is_correct: bool
    validation_method: str
    feedback: str | None
    correct_answer: str


class LessonService:
    """Lesson orchestration and management."""

    def __init__(
        self,
        lesson_repo: LessonRepository,
        attempt_repo: LessonAttemptRepository,
        user_word_repo: UserWordRepository,
        word_repo: WordRepository,
        stats_repo: StatisticsRepository,
        validation_service: ValidationService
    ):
        self.lesson_repo = lesson_repo
        self.attempt_repo = attempt_repo
        self.user_word_repo = user_word_repo
        self.word_repo = word_repo
        self.stats_repo = stats_repo
        self.validation_service = validation_service
        self.difficulty_adjuster = DifficultyAdjuster(
            choice_to_input_threshold=settings.choice_to_input_threshold,
            mastered_threshold=settings.mastered_threshold
        )

    async def get_or_create_active_lesson(
        self,
        profile_id: int,
        words_count: int | None = None
    ) -> Lesson:
        """Get active lesson or create a new one."""
        if words_count is None:
            words_count = settings.words_per_lesson

        active = await self.lesson_repo.get_active_lesson(profile_id)
        if active:
            return active

        lesson = Lesson(
            profile_id=profile_id,
            words_count=words_count
        )

        lesson = await self.lesson_repo.add(lesson)
        await self.lesson_repo.commit()

        logger.info(
            "lesson_created",
            lesson_id=lesson.lesson_id,
            profile_id=profile_id,
            words_count=words_count
        )

        return lesson

    async def get_words_for_lesson(
        self,
        profile_id: int,
        count: int = 30,
        target_language: str | None = None,
        level: str | None = None,
    ) -> list[UserWord]:
        """
        Get words for lesson using adaptive selection.

        Uses WordSelector algorithm.
        """
        candidates = await self.user_word_repo.get_user_vocabulary(
            profile_id=profile_id,
            status=None
        )

        candidates = [
            word for word in candidates
            if word.status != WordStatusEnum.MASTERED
        ]

        if len(candidates) < count and target_language and level:
            await self._backfill_from_frequency_list(
                profile_id=profile_id,
                existing_candidates=candidates,
                target_language=target_language,
                level=level,
                needed=count - len(candidates),
            )
            candidates = await self.user_word_repo.get_user_vocabulary(
                profile_id=profile_id,
                status=None,
            )
            candidates = [
                word for word in candidates
                if word.status != WordStatusEnum.MASTERED
            ]

        selector = WordSelector(words_per_lesson=count)
        return await selector.select_words_for_lesson(candidates)

    async def _backfill_from_frequency_list(
        self,
        profile_id: int,
        existing_candidates: list[UserWord],
        target_language: str,
        level: str,
        needed: int,
    ) -> None:
        """Add missing lesson words from CEFR frequency list to user vocabulary."""
        if needed <= 0:
            return

        existing_word_ids = {item.word_id for item in existing_candidates}
        frequency_words = await self.word_repo.get_frequency_words(
            language=target_language,
            level=level.upper(),
            limit=max(needed * 5, settings.words_per_lesson * 3),
        )

        created = 0
        for word in frequency_words:
            if word.word_id in existing_word_ids:
                continue

            user_word = UserWord(
                profile_id=profile_id,
                word_id=word.word_id,
            )
            await self.user_word_repo.add(user_word)
            existing_word_ids.add(word.word_id)
            created += 1

            if created >= needed:
                break

        if created:
            await self.user_word_repo.commit()

    async def generate_next_question(
        self,
        lesson: Lesson,
        selected_words: list[UserWord]
    ) -> Question | None:
        """Generate next question for a lesson."""
        attempts = await self.attempt_repo.get_lesson_attempts(lesson.lesson_id)
        attempted_ids = {a.user_word_id for a in attempts}

        for user_word in selected_words:
            if user_word.user_word_id not in attempted_ids:
                return await self._create_question(user_word)

        return None

    async def _create_question(self, user_word: UserWord) -> Question:
        """Create question from a user word."""
        detailed = await self.user_word_repo.get_by_id_with_details(
            user_word.user_word_id
        )
        if detailed:
            user_word = detailed

        test_type = self._determine_test_type(user_word)
        direction = random.choice([
            Direction.NATIVE_TO_FOREIGN.value,
            Direction.FOREIGN_TO_NATIVE.value
        ])

        word = user_word.word
        profile = user_word.profile
        native_lang = profile.user.native_language
        target_lang = profile.target_language
        level = profile.level.value

        native_variants = self._get_language_variants(word, native_lang)
        target_variants = self._get_language_variants(word, target_lang)

        if direction == Direction.NATIVE_TO_FOREIGN.value:
            question_text = native_variants[0] if native_variants else word.word
            expected_answer = target_variants[0] if target_variants else word.word
            alternatives = target_variants[1:]
            source_language = native_lang
            target_language = target_lang
        else:
            question_text = target_variants[0] if target_variants else word.word
            expected_answer = native_variants[0] if native_variants else word.word
            alternatives = native_variants[1:]
            source_language = target_lang
            target_language = native_lang

        options = None
        if test_type == TestType.MULTIPLE_CHOICE.value:
            options = await self._generate_options(
                correct_answer=expected_answer,
                word=word,
                direction=direction,
                native_lang=native_lang,
                target_lang=target_lang,
                level=level,
                count=4
            )
            
            # Fallback to INPUT if insufficient options
            if options is None:
                test_type = TestType.INPUT.value
                logger.info(
                    "falling_back_to_input_test",
                    word_id=word.word_id,
                    reason="insufficient_distractors"
                )

        return Question(
            user_word_id=user_word.user_word_id,
            word_id=word.word_id,
            question_text=question_text,
            expected_answer=expected_answer,
            alternative_answers=alternatives,
            direction=direction,
            test_type=test_type,
            source_language=source_language,
            target_language=target_language,
            options=options
        )

    def _get_language_variants(self, word: Word, language: str) -> list[str]:
        """Return available word variants in the requested language."""
        if word.language == language:
            return [word.word]

        translations = (word.translations or {}).get(language) or []
        return [t for t in translations if t]

    def _determine_test_type(self, user_word: UserWord) -> str:
        """Determine test type based on word statistics."""
        return self.difficulty_adjuster.determine_test_type(user_word)

    async def _generate_options(
        self,
        correct_answer: str,
        word: Word,
        direction: str,
        native_lang: str,
        target_lang: str,
        level: str,
        count: int = 4
    ) -> list[str] | None:
        """
        Generate answer options for multiple choice.
        
        Returns None if insufficient options found (< 2), 
        indicating INPUT test should be used instead.
        """
        options = [correct_answer]
        answer_language = (
            target_lang
            if direction == Direction.NATIVE_TO_FOREIGN.value
            else native_lang
        )

        options = await self._collect_options_from_language(
            options=options,
            source_language=word.language,
            answer_language=answer_language,
            level=level,
            count=count,
            exclude_word_id=word.word_id
        )

        if len(options) < count and answer_language != word.language:
            options = await self._collect_options_from_language(
                options=options,
                source_language=answer_language,
                answer_language=answer_language,
                level=level,
                count=count,
                exclude_word_id=word.word_id
            )

        # Log warning if insufficient options
        if len(options) < 2:
            logger.warning(
                "insufficient_options_for_multiple_choice",
                word_id=word.word_id,
                expected=count,
                actual=len(options)
            )
            return None

        random.shuffle(options)
        return options[:count]

    async def _collect_options_from_language(
        self,
        options: list[str],
        source_language: str,
        answer_language: str,
        level: str,
        count: int,
        exclude_word_id: int
    ) -> list[str]:
        """Collect additional options from frequency lists."""
        existing = {opt.lower() for opt in options}
        similar_words = await self.word_repo.get_frequency_words(
            language=source_language,
            level=level,
            limit=15
        )

        for similar_word in similar_words:
            if similar_word.word_id == exclude_word_id:
                continue

            if answer_language == similar_word.language:
                option = similar_word.word
            else:
                translations = (similar_word.translations or {}).get(answer_language) or []
                option = translations[0] if translations else ""

            if not option:
                continue

            option_key = option.lower()
            if option_key in existing:
                continue

            options.append(option)
            existing.add(option_key)

            if len(options) >= count:
                break

        return options

    async def process_answer(
        self,
        lesson_id: int,
        question: Question,
        user_answer: str
    ) -> AnswerResult:
        """Process user's answer."""
        validation = await self.validation_service.validate_answer(
            user_answer=user_answer,
            expected_answer=question.expected_answer,
            alternative_answers=question.alternative_answers,
            word_id=question.word_id,
            direction=question.direction,
            question=question.question_text,
            source_lang=question.source_language,
            target_lang=question.target_language
        )

        attempt = LessonAttempt(
            lesson_id=lesson_id,
            user_word_id=question.user_word_id,
            direction=question.direction,
            test_type=question.test_type,
            user_answer=user_answer,
            correct_answer=question.expected_answer,
            is_correct=validation.is_correct,
            validation_method=validation.method
        )

        await self.attempt_repo.add(attempt)

        await self.stats_repo.update_stat(
            user_word_id=question.user_word_id,
            direction=question.direction,
            test_type=question.test_type,
            is_correct=validation.is_correct
        )

        lesson = await self.lesson_repo.get_by_id(lesson_id)
        if lesson:
            if validation.is_correct:
                lesson.correct_answers += 1
            else:
                lesson.incorrect_answers += 1

        user_word = await self.user_word_repo.get_by_id_with_details(
            question.user_word_id
        )
        if user_word:
            user_word.last_reviewed_at = datetime.now(timezone.utc)
            await self._update_word_status(user_word)
            await update_review_schedule(
                user_word,
                validation.is_correct,
                validation.method
            )

        await self.lesson_repo.commit()

        logger.info(
            "answer_processed",
            lesson_id=lesson_id,
            user_word_id=question.user_word_id,
            is_correct=validation.is_correct,
            method=validation.method
        )

        return AnswerResult(
            is_correct=validation.is_correct,
            validation_method=validation.method,
            feedback=validation.feedback,
            correct_answer=question.expected_answer
        )

    async def _update_word_status(self, user_word: UserWord) -> None:
        """Update word status based on performance."""
        self.difficulty_adjuster.update_word_status(user_word)

    async def complete_lesson(self, lesson_id: int) -> dict:
        """Complete lesson and return summary."""
        lesson = await self.lesson_repo.get_by_id(lesson_id)
        if not lesson:
            return {}

        lesson.completed_at = datetime.now(timezone.utc)
        await self.lesson_repo.commit()

        duration_seconds = int((lesson.completed_at - lesson.started_at).total_seconds())
        accuracy = (
            (lesson.correct_answers / lesson.words_count) * 100
            if lesson.words_count
            else 0.0
        )

        logger.info(
            "lesson_completed",
            lesson_id=lesson_id,
            correct=lesson.correct_answers,
            incorrect=lesson.incorrect_answers,
            duration=duration_seconds
        )

        return {
            "lesson_id": lesson_id,
            "words_count": lesson.words_count,
            "correct_answers": lesson.correct_answers,
            "incorrect_answers": lesson.incorrect_answers,
            "accuracy": accuracy,
            "duration_seconds": duration_seconds
        }
