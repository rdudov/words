# Telegram Keyboards Overview

This document provides an overview of the keyboard implementations for the Words Telegram bot.

## Implemented Keyboards

### 1. Language Selection Keyboard
**Function:** `build_language_keyboard()`
- **Type:** InlineKeyboardMarkup
- **Layout:** 2 buttons per row
- **Callback format:** `select_language:{code}`

```
┌──────────────────────────────────┐
│  English    │    Русский         │
│  Español    │                    │
└──────────────────────────────────┘
```

### 2. CEFR Level Selection Keyboard
**Function:** `build_level_keyboard()`
- **Type:** InlineKeyboardMarkup
- **Layout:** 3 buttons per row (2 rows total)
- **Callback format:** `select_level:{level}`

```
┌──────────────────────────────────┐
│   A1    │    A2    │    B1      │
│   B2    │    C1    │    C2      │
└──────────────────────────────────┘
```

### 3. Main Menu Keyboard
**Function:** `build_main_menu()`
- **Type:** ReplyKeyboardMarkup (persistent)
- **Layout:** 2x2 grid
- **Features:** Resizable keyboard

```
┌──────────────────────────────────┐
│ 📚 Start Lesson │  ➕ Add Word  │
│ 📊 Statistics   │  ⚙️ Settings  │
└──────────────────────────────────┘
```

### 4. Confirmation Keyboard
**Function:** `build_confirmation_keyboard()`
- **Type:** InlineKeyboardMarkup
- **Layout:** 2 buttons in 1 row
- **Callback format:** `confirm:{yes|no}`

```
┌──────────────────────────────────┐
│     ✅ Yes     │     ❌ No       │
└──────────────────────────────────┘
```

## Usage Example

```python
from src.words.bot.keyboards import (
    build_language_keyboard,
    build_level_keyboard,
    build_main_menu,
    build_confirmation_keyboard,
)

# In your bot handlers:

@router.message(Command("start"))
async def cmd_start(message: Message):
    keyboard = build_language_keyboard()
    await message.answer(
        "Please select your learning language:",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("select_language:"))
async def process_language_selection(callback: CallbackQuery):
    lang_code = callback.data.split(":")[1]
    # Process language selection...
    keyboard = build_level_keyboard()
    await callback.message.edit_text(
        "Select your CEFR level:",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("select_level:"))
async def process_level_selection(callback: CallbackQuery):
    level = callback.data.split(":")[1]
    # Process level selection...
    keyboard = build_main_menu()
    await callback.message.answer(
        "Setup complete! Use the menu below:",
        reply_markup=keyboard
    )
```

## Test Coverage

All keyboard functions have comprehensive test coverage (100%) including:
- Correct keyboard type verification
- Button count and layout validation
- Callback data format verification
- Button text and emoji validation
- Package-level import testing
- Integration testing

## Files

- **Implementation:** `/home/user/words/src/words/bot/keyboards/common.py`
- **Package exports:** `/home/user/words/src/words/bot/keyboards/__init__.py`
- **Tests:** `/home/user/words/tests/bot/keyboards/test_common.py`
