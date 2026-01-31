"""
Word handlers for the Telegram bot.

This module implements the word addition flow using aiogram Router and FSM.
It handles:
- Adding new words to user vocabulary
- Language detection (target→native or native→target)
- Translation fetching and display
- Word validation and error handling

The word addition flow uses FSM (Finite State Machine) to manage conversation state
and guides users through adding words to their learning vocabulary.
"""

import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.words.bot.states.registration import AddWordStates
from src.words.services.word import WordService
from src.words.services.translation import TranslationService
from src.words.repositories.word import WordRepository, UserWordRepository
from src.words.repositories.user import ProfileRepository
from src.words.repositories.cache import CacheRepository
from src.words.infrastructure.llm_client import LLMClient
from src.words.infrastructure.database import get_session
from src.words.config.settings import settings

logger = logging.getLogger(__name__)

router = Router(name="words")

_llm_client: LLMClient | None = None
_llm_client_factory = None


def _get_llm_client() -> LLMClient:
    """Return a shared LLM client, recreating it if the class was patched."""
    global _llm_client, _llm_client_factory
    if _llm_client is None or _llm_client_factory is not LLMClient:
        _llm_client = LLMClient(settings.llm_api_key, settings.llm_model)
        _llm_client_factory = LLMClient
    return _llm_client


@router.message(F.text == "➕ Add Word")
async def cmd_add_word(message: Message, state: FSMContext) -> None:
    """
    Start add word flow.

    Triggered when user clicks "➕ Add Word" button.
    Shows instruction message and transitions to waiting_for_word state.

    Args:
        message: Telegram message with "➕ Add Word" text
        state: FSM context for managing conversation state
    """
    await message.answer(
        "📝 Send me the word you want to add.\n"
        "You can send it in your native language or in the language you're learning."
    )
    await state.set_state(AddWordStates.waiting_for_word)


@router.message(StateFilter(AddWordStates.waiting_for_word))
async def process_word_input(message: Message, state: FSMContext) -> None:
    """
    Process word input from user.

    This handler implements the complete word addition flow:
    1. Validates word input (not empty)
    2. Shows processing message
    3. Gets user's active profile
    4. Sets up services (LLM, cache, translation, word)
    5. Detects language (tries target→native, then native→target)
    6. Adds word to vocabulary via WordService
    7. Formats and displays translation data with examples
    8. Handles errors gracefully
    9. Clears state when done

    Args:
        message: Telegram message with word text
        state: FSM context for managing conversation state
    """
    word_text = message.text.strip()
    user_id = message.from_user.id

    # Validate input
    if not word_text:
        await message.answer("Please send a valid word.")
        return

    # Show processing message
    processing_msg = await message.answer("🔍 Looking up translations...")

    try:
        async with get_session() as session:
            # Get user's active profile
            profile_repo = ProfileRepository(session)
            profile = await profile_repo.get_active_profile(user_id)

            if not profile:
                try:
                    await processing_msg.delete()
                except Exception as e:
                    logger.debug("Failed to delete processing message: %s", str(e))
                await message.answer("Please complete registration first using /start")
                await state.clear()
                return

            # Setup services (reuse shared LLM client)
            word_repo = WordRepository(session)
            user_word_repo = UserWordRepository(session)
            cache_repo = CacheRepository(session)
            translation_service = TranslationService(_get_llm_client(), cache_repo)
            word_service = WordService(word_repo, user_word_repo, translation_service)

            # Try to get translation (detect language)
            # First try: word is in target language
            try:
                translation_data = await word_service.get_word_with_translations(
                    word_text,
                    profile.target_language,
                    profile.user.native_language
                )
                source_lang = profile.target_language
                target_lang = profile.user.native_language
                logger.info(
                    "Language detected (target→native): word='%s', source=%s, target=%s",
                    word_text,
                    source_lang,
                    target_lang
                )
            except Exception as e:
                # Second try: word is in native language
                logger.debug(
                    "First translation attempt failed, trying reverse: word='%s', error=%s",
                    word_text,
                    str(e)
                )
                translation_data = await word_service.get_word_with_translations(
                    word_text,
                    profile.user.native_language,
                    profile.target_language
                )
                source_lang = profile.user.native_language
                target_lang = profile.target_language
                logger.info(
                    "Language detected (native→target): word='%s', source=%s, target=%s",
                    word_text,
                    source_lang,
                    target_lang
                )

            # Add word to vocabulary
            user_word = await word_service.add_word_for_user(
                profile_id=profile.profile_id,
                word_text=word_text,
                source_language=source_lang,
                target_language=target_lang,
                translation_data=translation_data
            )

            # Format response
            translations = ", ".join(translation_data.get("translations", []))
            examples = "\n".join([
                f"• {ex.get('source', '')} → {ex.get('target', '')}"
                for ex in translation_data.get("examples", [])[:2]
            ])

            try:
                await processing_msg.delete()
            except Exception as e:
                logger.debug("Failed to delete processing message: %s", str(e))
            await message.answer(
                f"✅ Word added to your vocabulary!\n\n"
                f"<b>{word_text}</b>\n"
                f"Translations: {translations}\n\n"
                f"Examples:\n{examples}",
                parse_mode="HTML"
            )

            logger.info(
                "Word added via bot: user_id=%d, profile_id=%d, word='%s', source=%s, target=%s",
                user_id,
                profile.profile_id,
                word_text,
                source_lang,
                target_lang
            )

    except Exception as e:
        logger.error(
            "Add word failed: user_id=%d, word='%s', error=%s (%s)",
            user_id,
            word_text,
            str(e),
            type(e).__name__
        )
        try:
            await processing_msg.delete()
        except Exception as delete_error:
            logger.debug("Failed to delete processing message: %s", str(delete_error))
        await message.answer(
            "❌ Failed to add word. Please try again later."
        )

    await state.clear()
