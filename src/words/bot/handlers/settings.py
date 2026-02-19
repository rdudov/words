"""Settings handlers for the Telegram bot."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.words.config.constants import CEFR_LEVELS, SUPPORTED_LANGUAGES
from src.words.infrastructure.database import get_session
from src.words.models.user import CEFRLevel, LanguageProfile, User
from src.words.repositories.user import ProfileRepository, UserRepository
from src.words.repositories.word import UserWordRepository, WordRepository
from src.words.services.user import UserService

logger = logging.getLogger(__name__)

router = Router(name="settings")


def _build_settings_menu(notification_enabled: bool):
    """Build settings menu keyboard."""
    builder = InlineKeyboardBuilder()
    notif_text = "🔔 Notifications: ON" if notification_enabled else "🔕 Notifications: OFF"
    builder.button(text=notif_text, callback_data="settings:notifications")
    builder.button(text="🌍 Change Language", callback_data="settings:language")
    builder.button(text="📊 Change Level", callback_data="settings:level")
    builder.adjust(1)
    return builder.as_markup()


async def _load_context(session, user_id: int) -> tuple[User | None, LanguageProfile | None]:
    """Load user and active profile for settings operations."""
    user_repo = UserRepository(session)
    profile_repo = ProfileRepository(session)
    user = await user_repo.get_by_telegram_id(user_id)
    profile = await profile_repo.get_active_profile(user_id)
    return user, profile


@router.message(F.text == "⚙️ Settings")
async def cmd_settings(message: Message) -> None:
    """Show settings menu."""
    user_id = message.from_user.id
    async with get_session() as session:
        user, profile = await _load_context(session, user_id)
        if not user or not profile:
            await message.answer("Please complete registration first using /start")
            return

        await message.answer(
            "⚙️ <b>Settings</b>\n\n"
            f"Current language: {SUPPORTED_LANGUAGES.get(profile.target_language, profile.target_language)}\n"
            f"Current level: {profile.level.value}\n\n"
            "What would you like to change?",
            reply_markup=_build_settings_menu(user.notification_enabled),
        )


@router.callback_query(F.data == "settings:notifications")
async def toggle_notifications(callback: CallbackQuery) -> None:
    """Toggle notification setting."""
    user_id = callback.from_user.id
    async with get_session() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(user_id)
        if not user:
            await callback.answer("Please complete registration first using /start", show_alert=True)
            return

        user.notification_enabled = not user.notification_enabled
        await user_repo.commit()

        status = "enabled" if user.notification_enabled else "disabled"
        await callback.message.edit_text(
            "⚙️ <b>Settings</b>\n\n"
            f"Notifications are now <b>{status}</b>.",
            reply_markup=_build_settings_menu(user.notification_enabled),
        )

    await callback.answer()


@router.callback_query(F.data == "settings:language")
async def show_language_options(callback: CallbackQuery) -> None:
    """Show language profiles available for switching."""
    user_id = callback.from_user.id
    async with get_session() as session:
        profile_repo = ProfileRepository(session)
        user_repo = UserRepository(session)

        user = await user_repo.get_by_telegram_id(user_id)
        profiles = await profile_repo.get_user_profiles(user_id)
        if not user or not profiles:
            await callback.answer("No language profiles found", show_alert=True)
            return

        builder = InlineKeyboardBuilder()
        for profile in profiles:
            marker = "✅ " if profile.is_active else ""
            language_name = SUPPORTED_LANGUAGES.get(profile.target_language, profile.target_language)
            builder.button(
                text=f"{marker}{language_name}",
                callback_data=f"settings:set_language:{profile.target_language}",
            )

        # Show "Add language" if user can add more (exclude native and existing)
        existing_langs = {p.target_language for p in profiles}
        languages_to_add = [
            (code, name) for code, name in SUPPORTED_LANGUAGES.items()
            if code != user.native_language and code not in existing_langs
        ]
        if languages_to_add:
            builder.button(text="➕ Add language", callback_data="settings:add_language")

        builder.button(text="◀️ Back", callback_data="settings:back")
        builder.adjust(1)

        await callback.message.edit_text(
            "🌍 <b>Choose active language</b>",
            reply_markup=builder.as_markup(),
        )

    await callback.answer()


@router.callback_query(F.data == "settings:add_language")
async def show_add_language_options(callback: CallbackQuery) -> None:
    """Show languages available to add (excluding native and existing profiles)."""
    user_id = callback.from_user.id
    async with get_session() as session:
        user_repo = UserRepository(session)
        profile_repo = ProfileRepository(session)
        user = await user_repo.get_by_telegram_id(user_id)
        profiles = await profile_repo.get_user_profiles(user_id)

        if not user or not profiles:
            await callback.answer("Please complete registration first using /start", show_alert=True)
            return

        existing_langs = {p.target_language for p in profiles}
        languages_to_add = [
            (code, name) for code, name in SUPPORTED_LANGUAGES.items()
            if code != user.native_language and code not in existing_langs
        ]

        if not languages_to_add:
            await callback.answer(
                "You're already learning all available languages!",
                show_alert=True
            )
            return

        builder = InlineKeyboardBuilder()
        for code, name in languages_to_add:
            builder.button(
                text=name,
                callback_data=f"settings:add_language:{code}",
            )
        builder.button(text="◀️ Back", callback_data="settings:language")
        builder.adjust(2)

        await callback.message.edit_text(
            "➕ <b>Add new language</b>\n\n"
            "Select the language you want to learn:",
            reply_markup=builder.as_markup(),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("settings:add_language:"))
async def show_level_for_new_language(callback: CallbackQuery) -> None:
    """Show CEFR level selection for the new language profile."""
    target_language = callback.data.split(":", 2)[2]
    if target_language not in SUPPORTED_LANGUAGES:
        await callback.answer("Invalid language", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for level in CEFR_LEVELS:
        builder.button(
            text=level,
            callback_data=f"settings:create_profile:{target_language}:{level}",
        )
    builder.button(text="◀️ Back", callback_data="settings:add_language")
    builder.adjust(3, 3, 1)

    language_name = SUPPORTED_LANGUAGES[target_language]
    await callback.message.edit_text(
        f"➕ <b>Add {language_name}</b>\n\n"
        "What's your current level? (CEFR scale)",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:create_profile:"))
async def create_new_language_profile(callback: CallbackQuery) -> None:
    """Create new language profile and switch to it."""
    parts = callback.data.split(":", 2)[2].rsplit(":", 1)
    if len(parts) != 2:
        await callback.answer("Invalid request", show_alert=True)
        return

    target_language, level = parts
    if target_language not in SUPPORTED_LANGUAGES or level not in CEFR_LEVELS:
        await callback.answer("Invalid language or level", show_alert=True)
        return

    user_id = callback.from_user.id
    async with get_session() as session:
        user_repo = UserRepository(session)
        profile_repo = ProfileRepository(session)
        word_repo = WordRepository(session)
        user_word_repo = UserWordRepository(session)
        user_service = UserService(
            user_repo,
            profile_repo,
            word_repo=word_repo,
            user_word_repo=user_word_repo,
        )

        user = await user_repo.get_by_telegram_id(user_id)
        if not user:
            await callback.answer("Please complete registration first using /start", show_alert=True)
            return

        # Check profile doesn't already exist
        profiles = await profile_repo.get_user_profiles(user_id)
        if any(p.target_language == target_language for p in profiles):
            await callback.answer("You already have this language", show_alert=True)
            return

        if target_language == user.native_language:
            await callback.answer(
                "Cannot add native language as learning language",
                show_alert=True
            )
            return

        try:
            await user_service.create_language_profile(
                user_id=user_id,
                target_language=target_language,
                level=level,
            )
        except Exception as e:
            logger.exception("Failed to create language profile: %s", e)
            await callback.answer("Failed to add language", show_alert=True)
            return

        language_name = SUPPORTED_LANGUAGES[target_language]
        await callback.message.edit_text(
            "⚙️ <b>Settings</b>\n\n"
            f"✅ <b>{language_name}</b> added! Level: {level}\n\n"
            "You can switch between languages in the language settings.",
            reply_markup=_build_settings_menu(user.notification_enabled),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("settings:set_language:"))
async def set_active_language(callback: CallbackQuery) -> None:
    """Switch active language profile."""
    user_id = callback.from_user.id
    target_language = callback.data.split(":", 2)[2]

    async with get_session() as session:
        user_repo = UserRepository(session)
        profile_repo = ProfileRepository(session)
        user_service = UserService(user_repo, profile_repo)
        user = await user_repo.get_by_telegram_id(user_id)
        if not user:
            await callback.answer("Please complete registration first using /start", show_alert=True)
            return

        try:
            profile = await user_service.switch_active_language(user_id, target_language)
        except ValueError:
            await callback.answer("Language profile is not available", show_alert=True)
            return

        language_name = SUPPORTED_LANGUAGES.get(profile.target_language, profile.target_language)
        await callback.message.edit_text(
            "⚙️ <b>Settings</b>\n\n"
            f"Active language switched to: <b>{language_name}</b>",
            reply_markup=_build_settings_menu(user.notification_enabled),
        )

    await callback.answer()


@router.callback_query(F.data == "settings:level")
async def show_level_options(callback: CallbackQuery) -> None:
    """Show CEFR levels for the active profile."""
    builder = InlineKeyboardBuilder()
    for level in CEFR_LEVELS:
        builder.button(text=level, callback_data=f"settings:set_level:{level}")
    builder.button(text="◀️ Back", callback_data="settings:back")
    builder.adjust(3, 3, 1)
    await callback.message.edit_text(
        "📊 <b>Choose your level</b>",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:set_level:"))
async def set_level(callback: CallbackQuery) -> None:
    """Update active profile CEFR level."""
    user_id = callback.from_user.id
    level = callback.data.split(":", 2)[2]
    if level not in CEFR_LEVELS:
        await callback.answer("Invalid level", show_alert=True)
        return

    async with get_session() as session:
        user_repo = UserRepository(session)
        profile_repo = ProfileRepository(session)
        user = await user_repo.get_by_telegram_id(user_id)
        profile = await profile_repo.get_active_profile(user_id)

        if not user or not profile:
            await callback.answer("Please complete registration first using /start", show_alert=True)
            return

        profile.level = CEFRLevel[level]
        await profile_repo.commit()

        await callback.message.edit_text(
            "⚙️ <b>Settings</b>\n\n"
            f"Level updated to: <b>{level}</b>",
            reply_markup=_build_settings_menu(user.notification_enabled),
        )

    await callback.answer()


@router.callback_query(F.data == "settings:back")
async def back_to_settings(callback: CallbackQuery) -> None:
    """Return to settings main menu."""
    user_id = callback.from_user.id
    async with get_session() as session:
        user, profile = await _load_context(session, user_id)
        if not user or not profile:
            await callback.answer("Please complete registration first using /start", show_alert=True)
            return

        await callback.message.edit_text(
            "⚙️ <b>Settings</b>\n\n"
            f"Current language: {SUPPORTED_LANGUAGES.get(profile.target_language, profile.target_language)}\n"
            f"Current level: {profile.level.value}",
            reply_markup=_build_settings_menu(user.notification_enabled),
        )
    await callback.answer()
