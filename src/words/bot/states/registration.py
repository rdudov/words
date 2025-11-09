"""State machines for bot conversation flows.

This module defines FSM (Finite State Machine) states for managing
different conversation flows in the Telegram bot using aiogram.fsm.

The state machines defined here handle:
- User registration process
- Adding new words to user's vocabulary
- Lesson flow and progression
"""

from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """States for user registration flow.

    This state machine manages the initial user onboarding process,
    collecting necessary information about language preferences and proficiency.

    States:
        native_language: Waiting for user to select their native language
        target_language: Waiting for user to select their target learning language
        level: Waiting for user to select their proficiency level
        confirming: Waiting for user to confirm registration details
    """

    native_language = State()
    target_language = State()
    level = State()
    confirming = State()


class AddWordStates(StatesGroup):
    """States for adding new word flow.

    This state machine manages the process of adding a new word to the user's
    vocabulary, including word input and meaning disambiguation.

    States:
        waiting_for_word: Waiting for user to input a word to add
        selecting_meaning: Waiting for user to select the correct meaning if multiple exist
        confirming: Waiting for user to confirm the word addition
    """

    waiting_for_word = State()
    selecting_meaning = State()
    confirming = State()


class LessonStates(StatesGroup):
    """States for lesson flow.

    This state machine manages the lesson session, including question presentation
    and answer validation.

    States:
        in_progress: Lesson is active and ready for next question
        answering_question: Waiting for user to answer the current question
        viewing_result: Showing results of the answer and preparing next question
    """

    in_progress = State()
    answering_question = State()
    viewing_result = State()
