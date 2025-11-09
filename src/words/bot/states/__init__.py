"""Bot state machines package.

This package exports all FSM state groups used in the Telegram bot
for managing conversation flows.
"""

from .registration import (
    AddWordStates,
    LessonStates,
    RegistrationStates,
)

__all__ = [
    "RegistrationStates",
    "AddWordStates",
    "LessonStates",
]
