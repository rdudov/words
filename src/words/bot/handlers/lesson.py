"""Lesson handlers for the Telegram bot."""

import logging

from src.words.utils.logger import get_event_logger

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.words.bot.keyboards.common import build_main_menu
from src.words.bot.states.registration import LessonStates
from src.words.config.settings import settings
from src.words.infrastructure.database import get_session
from src.words.infrastructure.llm_client import LLMClient
from src.words.repositories.cache import CacheRepository
from src.words.repositories.lesson import LessonRepository, LessonAttemptRepository
from src.words.repositories.statistics import StatisticsRepository
from src.words.repositories.user import ProfileRepository
from src.words.repositories.word import UserWordRepository, WordRepository
from src.words.services.lesson import LessonService, Question
from src.words.services.translation import TranslationService
from src.words.services.validation import ValidationService

logger = logging.getLogger(__name__)
event_logger = get_event_logger(__name__)

router = Router(name="lesson")

_llm_client: LLMClient | None = None
_llm_client_factory = None


def _get_llm_client() -> LLMClient:
    """Return a shared LLM client, recreating it if the class was patched."""
    global _llm_client, _llm_client_factory
    if _llm_client is None or _llm_client_factory is not LLMClient:
        _llm_client = LLMClient(settings.llm_api_key, settings.llm_model)
        _llm_client_factory = LLMClient
    return _llm_client


def _build_lesson_service(session) -> LessonService:
    """Create a LessonService with repository dependencies."""
    cache_repo = CacheRepository(session)
    translation_service = TranslationService(_get_llm_client(), cache_repo)
    validation_service = ValidationService(translation_service)

    return LessonService(
        LessonRepository(session),
        LessonAttemptRepository(session),
        UserWordRepository(session),
        WordRepository(session),
        StatisticsRepository(session),
        validation_service
    )


@router.message(
    StateFilter(LessonStates.answering_question),
    F.text.in_(["➕ Add Word", "📊 Statistics", "⚙️ Settings"])
)
async def cancel_lesson_by_menu(message: Message, state: FSMContext) -> None:
    """Cancel active lesson when user clicks menu button."""
    await message.answer(
        "Lesson cancelled. Your progress has been saved.",
        reply_markup=build_main_menu()
    )
    await state.clear()
    event_logger.info(
        "lesson_cancelled_by_user",
        user_id=message.from_user.id,
        menu_item=message.text
    )


@router.message(F.text == "📚 Start Lesson")
async def cmd_start_lesson(message: Message, state: FSMContext) -> None:
    """Start a new lesson."""
    user_id = message.from_user.id
    
    # Clear any previous lesson state
    current_state = await state.get_state()
    if current_state:
        await state.clear()

    processing_msg = await message.answer("Preparing your lesson...")

    try:
        async with get_session() as session:
            profile_repo = ProfileRepository(session)
            profile = await profile_repo.get_active_profile(user_id)

            if not profile:
                try:
                    await processing_msg.delete()
                except Exception as delete_error:
                    logger.debug(
                        "Failed to delete processing message: %s",
                        str(delete_error)
                    )
                await message.answer("Please complete registration first using /start")
                return

            lesson_service = _build_lesson_service(session)

            lesson = await lesson_service.get_or_create_active_lesson(
                profile_id=profile.profile_id,
                words_count=settings.words_per_lesson
            )

            selected_words = await lesson_service.get_words_for_lesson(
                profile_id=profile.profile_id,
                count=settings.words_per_lesson
            )

            if not selected_words:
                try:
                    await processing_msg.delete()
                except Exception as delete_error:
                    logger.debug(
                        "Failed to delete processing message: %s",
                        str(delete_error)
                    )
                event_logger.warning(
                    "lesson_start_failed_no_words",
                    user_id=user_id,
                    profile_id=profile.profile_id
                )
                await message.answer(
                    "📚 You don't have any words to practice yet.\n\n"
                    "Add some words to start learning using the "
                    "<b>➕ Add Word</b> button below.",
                    reply_markup=build_main_menu()
                )
                return
            
            event_logger.info(
                "lesson_started",
                user_id=user_id,
                profile_id=profile.profile_id,
                words_count=len(selected_words)
            )

            question = await lesson_service.generate_next_question(
                lesson, selected_words
            )

            await state.update_data(
                lesson_id=lesson.lesson_id,
                selected_words=[word.user_word_id for word in selected_words],
                current_question=question.__dict__
            )

            try:
                await processing_msg.delete()
            except Exception as delete_error:
                logger.debug(
                    "Failed to delete processing message: %s",
                    str(delete_error)
                )

            await send_question(message, question)
            await state.set_state(LessonStates.answering_question)

    except Exception as e:
        logger.error("start_lesson_failed", exc_info=e)
        try:
            await processing_msg.delete()
        except Exception as delete_error:
            logger.debug(
                "Failed to delete processing message: %s",
                str(delete_error)
            )
        await message.answer("Failed to start lesson. Please try again.")


async def send_question(message: Message, question: Question) -> None:
    """Send question to user."""
    from src.words.config.constants import TestType

    if question.test_type == TestType.MULTIPLE_CHOICE.value:
        builder = InlineKeyboardBuilder()

        for index, option in enumerate(question.options or []):
            builder.button(
                text=option,
                callback_data=f"answer:{index}:{option}"
            )

        builder.adjust(1)

        await message.answer(
            f"<b>Question:</b> {question.question_text}\n\n"
            "Choose the correct translation:",
            reply_markup=builder.as_markup()
        )
        return

    await message.answer(
        f"<b>Question:</b> {question.question_text}\n\n"
        "Type your answer:"
    )


@router.callback_query(
    StateFilter(LessonStates.answering_question),
    F.data.startswith("answer:")
)
async def process_multiple_choice_answer(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """Process multiple choice answer."""
    _, _, answer = callback.data.split(":", 2)
    await process_answer(callback.message, answer, state, callback)


@router.message(StateFilter(LessonStates.answering_question))
async def process_input_answer(message: Message, state: FSMContext) -> None:
    """Process text input answer."""
    answer = message.text.strip()
    await process_answer(message, answer, state)


async def process_answer(
    message: Message,
    answer: str,
    state: FSMContext,
    callback: CallbackQuery | None = None
) -> None:
    """Process answer and show result."""
    data = await state.get_data()
    lesson_id = data.get("lesson_id")
    question_dict = data.get("current_question")

    if not lesson_id or not question_dict:
        await message.answer("Lesson state lost. Please start a new lesson.")
        await state.clear()
        if callback:
            await callback.answer()
        return

    question = Question(**question_dict)

    processing_msg = await message.answer("Checking your answer...")

    try:
        async with get_session() as session:
            lesson_service = _build_lesson_service(session)

            result = await lesson_service.process_answer(
                lesson_id=lesson_id,
                question=question,
                user_answer=answer
            )

            try:
                await processing_msg.delete()
            except Exception as delete_error:
                logger.debug(
                    "Failed to delete processing message: %s",
                    str(delete_error)
                )

            if result.is_correct:
                result_text = "<b>Correct!</b>"
                if result.feedback:
                    result_text += f"\n\n{result.feedback}"
            else:
                result_text = (
                    "<b>Incorrect</b>\n\n"
                    f"Your answer: {answer}\n"
                    f"Correct answer: {result.correct_answer}"
                )
                if result.feedback:
                    result_text += f"\n\n{result.feedback}"

            lesson = await lesson_service.lesson_repo.get_by_id(lesson_id)
            selected_word_ids = data.get("selected_words", [])
            selected_words = []
            for word_id in selected_word_ids:
                word = await lesson_service.user_word_repo.get_by_id(word_id)
                if word:
                    selected_words.append(word)

            attempts = await lesson_service.attempt_repo.get_lesson_attempts(lesson_id)

            if len(attempts) >= len(selected_words):
                summary = await lesson_service.complete_lesson(lesson_id)

                await message.answer(result_text)
                await message.answer(
                    "<b>Lesson Complete!</b>\n\n"
                    f"Words practiced: {summary.get('words_count', 0)}\n"
                    f"Correct: {summary.get('correct_answers', 0)}\n"
                    f"Incorrect: {summary.get('incorrect_answers', 0)}\n"
                    f"Accuracy: {summary.get('accuracy', 0):.1f}%\n"
                    f"Duration: {summary.get('duration_seconds', 0)}s",
                    reply_markup=build_main_menu()
                )

                await state.clear()
            else:
                next_question = await lesson_service.generate_next_question(
                    lesson, selected_words
                )

                if next_question:
                    await state.update_data(
                        current_question=next_question.__dict__
                    )

                    await message.answer(result_text)
                    await send_question(message, next_question)

    except Exception as e:
        logger.error("process_answer_failed", exc_info=e)
        try:
            await processing_msg.delete()
        except Exception as delete_error:
            logger.debug(
                "Failed to delete processing message: %s",
                str(delete_error)
            )
        await message.answer("Error processing answer. Please try again.")

    if callback:
        await callback.answer()
