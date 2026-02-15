"""Statistics handler for the Telegram bot."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message

from src.words.config.settings import settings
from src.words.infrastructure.database import get_session
from src.words.infrastructure.llm_client import LLMClient
from src.words.repositories.cache import CacheRepository
from src.words.repositories.lesson import LessonRepository
from src.words.repositories.user import ProfileRepository
from src.words.repositories.word import UserWordRepository, WordRepository
from src.words.services.translation import TranslationService
from src.words.services.word import WordService

logger = logging.getLogger(__name__)

router = Router(name="stats")

_llm_client: LLMClient | None = None
_llm_client_factory = None


def _get_llm_client() -> LLMClient:
    """Return a shared LLM client, recreating it if patched in tests."""
    global _llm_client, _llm_client_factory
    if _llm_client is None or _llm_client_factory is not LLMClient:
        _llm_client = LLMClient(settings.llm_api_key, settings.llm_model)
        _llm_client_factory = LLMClient
    return _llm_client


@router.message(F.text == "📊 Statistics")
async def cmd_statistics(message: Message) -> None:
    """Show vocabulary and lesson statistics for the active profile."""
    user_id = message.from_user.id

    try:
        async with get_session() as session:
            profile_repo = ProfileRepository(session)
            profile = await profile_repo.get_active_profile(user_id)

            if not profile:
                await message.answer("Please complete registration first using /start")
                return

            translation_service = TranslationService(
                _get_llm_client(),
                CacheRepository(session),
            )
            word_service = WordService(
                WordRepository(session),
                UserWordRepository(session),
                translation_service,
            )
            lesson_repo = LessonRepository(session)

            vocab_stats = await word_service.get_user_vocabulary_stats(profile.profile_id)
            recent_lessons = await lesson_repo.get_recent_lessons(profile.profile_id, limit=10)
            lessons_today = await lesson_repo.count_lessons_today(profile.profile_id)

            total_completed = len(recent_lessons)
            stats_text = (
                "📊 <b>Your Statistics</b>\n\n"
                "<b>Vocabulary</b>\n"
                f"📚 Total words: {vocab_stats['total']}\n"
                f"🆕 New: {vocab_stats['new']}\n"
                f"📖 Learning: {vocab_stats['learning']}\n"
                f"🔄 Reviewing: {vocab_stats['reviewing']}\n"
                f"✅ Mastered: {vocab_stats['mastered']}\n\n"
                "<b>Lessons</b>\n"
                f"📅 Today: {lessons_today}\n"
                f"📈 Recent completed (last 10): {total_completed}"
            )

            if recent_lessons:
                last_lesson = recent_lessons[0]
                attempted = last_lesson.correct_answers + last_lesson.incorrect_answers
                denominator = attempted if attempted > 0 else last_lesson.words_count
                accuracy = (
                    (last_lesson.correct_answers / denominator) * 100
                    if denominator > 0
                    else 0.0
                )
                stats_text += (
                    "\n\n<b>Last Lesson</b>\n"
                    f"✅ Correct: {last_lesson.correct_answers}\n"
                    f"❌ Incorrect: {last_lesson.incorrect_answers}\n"
                    f"📊 Accuracy: {accuracy:.1f}%"
                )

            await message.answer(stats_text)
    except Exception:
        logger.exception("statistics_failed: user_id=%d", user_id)
        await message.answer("❌ Failed to load statistics.")
