"""
Start and registration handlers for the Telegram bot.

This module implements the user registration flow using aiogram Router and FSM.
It handles:
- /start command processing
- Native language selection
- Target language selection
- CEFR level selection
- User and profile creation

The registration flow uses FSM (Finite State Machine) to manage conversation state
and guides users through the onboarding process.
"""

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from src.words.bot.states.registration import RegistrationStates
from src.words.bot.keyboards.common import (
    build_language_keyboard,
    build_level_keyboard,
    build_main_menu
)
from src.words.services.user import UserService
from src.words.infrastructure.database import get_session
from src.words.repositories.user import UserRepository, ProfileRepository
from src.words.config.constants import SUPPORTED_LANGUAGES, CEFR_LEVELS

router = Router(name="start")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """
    Handle /start command.

    Checks if the user is already registered:
    - If registered: Shows main menu
    - If not registered: Starts registration flow

    Args:
        message: Telegram message with /start command
        state: FSM context for managing conversation state
    """
    user_id = message.from_user.id

    # Check if user exists
    async with get_session() as session:
        user_service = UserService(
            UserRepository(session),
            ProfileRepository(session)
        )

        user = await user_service.get_user(user_id)

    if user:
        # Existing user - show main menu
        await message.answer(
            f"Welcome back! Ready to practice?",
            reply_markup=build_main_menu()
        )
    else:
        # New user - start registration
        await message.answer(
            "Welcome to the Language Learning Bot! 🎓\n\n"
            "I'll help you learn foreign words using adaptive algorithms.\n\n"
            "First, let's set up your profile.\n"
            "What is your native language?",
            reply_markup=build_language_keyboard()
        )
        await state.set_state(RegistrationStates.native_language)


@router.callback_query(
    StateFilter(RegistrationStates.native_language),
    F.data.startswith("select_language:")
)
async def process_native_language(
    callback: CallbackQuery,
    state: FSMContext
):
    """
    Process native language selection.

    Saves the selected native language to FSM context and transitions
    to target language selection state.

    Args:
        callback: Callback query from language selection button
        state: FSM context for managing conversation state
    """
    language_code = callback.data.split(":")[1]

    await state.update_data(native_language=language_code)

    await callback.message.edit_text(
        f"Great! Your native language: {SUPPORTED_LANGUAGES[language_code]}\n\n"
        "Which language do you want to learn?",
        reply_markup=build_language_keyboard()
    )

    await state.set_state(RegistrationStates.target_language)
    await callback.answer()


@router.callback_query(
    StateFilter(RegistrationStates.target_language),
    F.data.startswith("select_language:")
)
async def process_target_language(
    callback: CallbackQuery,
    state: FSMContext
):
    """
    Process target language selection.

    Validates that target language is different from native language,
    saves it to FSM context, and transitions to level selection state.

    Args:
        callback: Callback query from language selection button
        state: FSM context for managing conversation state
    """
    language_code = callback.data.split(":")[1]
    data = await state.get_data()

    # Check if same as native
    if language_code == data["native_language"]:
        await callback.answer(
            "Please select a different language from your native language!",
            show_alert=True
        )
        return

    await state.update_data(target_language=language_code)

    await callback.message.edit_text(
        f"Excellent! You're learning: {SUPPORTED_LANGUAGES[language_code]}\n\n"
        "What's your current level? (CEFR scale)",
        reply_markup=build_level_keyboard()
    )

    await state.set_state(RegistrationStates.level)
    await callback.answer()


@router.callback_query(
    StateFilter(RegistrationStates.level),
    F.data.startswith("select_level:")
)
async def process_level(
    callback: CallbackQuery,
    state: FSMContext
):
    """
    Process level selection and complete registration.

    Creates the user and language profile in the database using UserService,
    shows completion message with main menu, and clears FSM state.

    Args:
        callback: Callback query from level selection button
        state: FSM context for managing conversation state
    """
    level = callback.data.split(":")[1]
    data = await state.get_data()

    user_id = callback.from_user.id

    # Create user and profile
    async with get_session() as session:
        user_service = UserService(
            UserRepository(session),
            ProfileRepository(session)
        )

        # Register user
        await user_service.register_user(
            user_id=user_id,
            native_language=data["native_language"],
            interface_language=data["native_language"]  # Use native as interface
        )

        # Create language profile
        await user_service.create_language_profile(
            user_id=user_id,
            target_language=data["target_language"],
            level=level
        )

    await callback.message.delete()
    await callback.message.answer(
        "✅ Registration complete!\n\n"
        f"Learning: {SUPPORTED_LANGUAGES[data['target_language']]}\n"
        f"Level: {level}\n\n"
        "Ready to start learning? Choose an action below:",
        reply_markup=build_main_menu()
    )

    await state.clear()
    await callback.answer()
