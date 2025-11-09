"""Tests for bot state machines.

This module tests the FSM (Finite State Machine) state groups defined
for managing conversation flows in the Telegram bot.
"""

import pytest
from aiogram.fsm.state import State, StatesGroup

from words.bot.states import (
    AddWordStates,
    LessonStates,
    RegistrationStates,
)
from words.bot.states.registration import (
    AddWordStates as DirectAddWordStates,
    LessonStates as DirectLessonStates,
    RegistrationStates as DirectRegistrationStates,
)


class TestRegistrationStates:
    """Tests for RegistrationStates state machine."""

    def test_is_states_group(self):
        """Test that RegistrationStates is a StatesGroup subclass."""
        assert issubclass(RegistrationStates, StatesGroup)

    def test_has_native_language_state(self):
        """Test that native_language state exists."""
        assert hasattr(RegistrationStates, "native_language")
        assert isinstance(RegistrationStates.native_language, State)

    def test_has_target_language_state(self):
        """Test that target_language state exists."""
        assert hasattr(RegistrationStates, "target_language")
        assert isinstance(RegistrationStates.target_language, State)

    def test_has_level_state(self):
        """Test that level state exists."""
        assert hasattr(RegistrationStates, "level")
        assert isinstance(RegistrationStates.level, State)

    def test_has_confirming_state(self):
        """Test that confirming state exists."""
        assert hasattr(RegistrationStates, "confirming")
        assert isinstance(RegistrationStates.confirming, State)

    def test_all_required_states_present(self):
        """Test that all required states are present."""
        required_states = {"native_language", "target_language", "level", "confirming"}
        state_names = {
            attr
            for attr in dir(RegistrationStates)
            if isinstance(getattr(RegistrationStates, attr), State)
        }
        assert required_states.issubset(state_names)

    def test_state_group_name(self):
        """Test that the state group has state names tuple."""
        # StatesGroup generates a __state_names__ for the group
        assert hasattr(RegistrationStates, "__state_names__")
        assert isinstance(RegistrationStates.__state_names__, tuple)

    def test_states_have_unique_values(self):
        """Test that all states have unique state values."""
        states = [
            RegistrationStates.native_language,
            RegistrationStates.target_language,
            RegistrationStates.level,
            RegistrationStates.confirming,
        ]
        state_strings = [state.state for state in states]
        assert len(state_strings) == len(set(state_strings))

    def test_state_string_format(self):
        """Test that state strings follow aiogram format."""
        # aiogram states follow the format: GroupName:state_name
        state = RegistrationStates.native_language
        assert ":" in state.state
        group_name, state_name = state.state.split(":", 1)
        assert state_name == "native_language"

    def test_can_import_from_package(self):
        """Test that RegistrationStates can be imported from package."""
        from words.bot import RegistrationStates as PackageImport

        assert PackageImport is RegistrationStates

    def test_can_import_from_states_module(self):
        """Test that RegistrationStates can be imported from states module."""
        from words.bot.states import RegistrationStates as StatesImport

        assert StatesImport is RegistrationStates


class TestAddWordStates:
    """Tests for AddWordStates state machine."""

    def test_is_states_group(self):
        """Test that AddWordStates is a StatesGroup subclass."""
        assert issubclass(AddWordStates, StatesGroup)

    def test_has_waiting_for_word_state(self):
        """Test that waiting_for_word state exists."""
        assert hasattr(AddWordStates, "waiting_for_word")
        assert isinstance(AddWordStates.waiting_for_word, State)

    def test_has_selecting_meaning_state(self):
        """Test that selecting_meaning state exists."""
        assert hasattr(AddWordStates, "selecting_meaning")
        assert isinstance(AddWordStates.selecting_meaning, State)

    def test_has_confirming_state(self):
        """Test that confirming state exists."""
        assert hasattr(AddWordStates, "confirming")
        assert isinstance(AddWordStates.confirming, State)

    def test_all_required_states_present(self):
        """Test that all required states are present."""
        required_states = {"waiting_for_word", "selecting_meaning", "confirming"}
        state_names = {
            attr
            for attr in dir(AddWordStates)
            if isinstance(getattr(AddWordStates, attr), State)
        }
        assert required_states.issubset(state_names)

    def test_state_group_name(self):
        """Test that the state group has state names tuple."""
        assert hasattr(AddWordStates, "__state_names__")
        assert isinstance(AddWordStates.__state_names__, tuple)

    def test_states_have_unique_values(self):
        """Test that all states have unique state values."""
        states = [
            AddWordStates.waiting_for_word,
            AddWordStates.selecting_meaning,
            AddWordStates.confirming,
        ]
        state_strings = [state.state for state in states]
        assert len(state_strings) == len(set(state_strings))

    def test_state_string_format(self):
        """Test that state strings follow aiogram format."""
        state = AddWordStates.waiting_for_word
        assert ":" in state.state
        group_name, state_name = state.state.split(":", 1)
        assert state_name == "waiting_for_word"

    def test_can_import_from_package(self):
        """Test that AddWordStates can be imported from package."""
        from words.bot import AddWordStates as PackageImport

        assert PackageImport is AddWordStates

    def test_can_import_from_states_module(self):
        """Test that AddWordStates can be imported from states module."""
        from words.bot.states import AddWordStates as StatesImport

        assert StatesImport is AddWordStates


class TestLessonStates:
    """Tests for LessonStates state machine."""

    def test_is_states_group(self):
        """Test that LessonStates is a StatesGroup subclass."""
        assert issubclass(LessonStates, StatesGroup)

    def test_has_in_progress_state(self):
        """Test that in_progress state exists."""
        assert hasattr(LessonStates, "in_progress")
        assert isinstance(LessonStates.in_progress, State)

    def test_has_answering_question_state(self):
        """Test that answering_question state exists."""
        assert hasattr(LessonStates, "answering_question")
        assert isinstance(LessonStates.answering_question, State)

    def test_has_viewing_result_state(self):
        """Test that viewing_result state exists."""
        assert hasattr(LessonStates, "viewing_result")
        assert isinstance(LessonStates.viewing_result, State)

    def test_all_required_states_present(self):
        """Test that all required states are present."""
        required_states = {"in_progress", "answering_question", "viewing_result"}
        state_names = {
            attr
            for attr in dir(LessonStates)
            if isinstance(getattr(LessonStates, attr), State)
        }
        assert required_states.issubset(state_names)

    def test_state_group_name(self):
        """Test that the state group has state names tuple."""
        assert hasattr(LessonStates, "__state_names__")
        assert isinstance(LessonStates.__state_names__, tuple)

    def test_states_have_unique_values(self):
        """Test that all states have unique state values."""
        states = [
            LessonStates.in_progress,
            LessonStates.answering_question,
            LessonStates.viewing_result,
        ]
        state_strings = [state.state for state in states]
        assert len(state_strings) == len(set(state_strings))

    def test_state_string_format(self):
        """Test that state strings follow aiogram format."""
        state = LessonStates.in_progress
        assert ":" in state.state
        group_name, state_name = state.state.split(":", 1)
        assert state_name == "in_progress"

    def test_can_import_from_package(self):
        """Test that LessonStates can be imported from package."""
        from words.bot import LessonStates as PackageImport

        assert PackageImport is LessonStates

    def test_can_import_from_states_module(self):
        """Test that LessonStates can be imported from states module."""
        from words.bot.states import LessonStates as StatesImport

        assert StatesImport is LessonStates


class TestStateGroupInteractions:
    """Tests for interactions between different state groups."""

    def test_state_groups_are_distinct(self):
        """Test that each state group is a separate class."""
        assert RegistrationStates is not AddWordStates
        assert RegistrationStates is not LessonStates
        assert AddWordStates is not LessonStates

    def test_state_groups_have_different_names(self):
        """Test that each state group has different state names."""
        # Each group should have its own unique set of state names
        reg_names = set(RegistrationStates.__state_names__)
        add_names = set(AddWordStates.__state_names__)
        lesson_names = set(LessonStates.__state_names__)

        # State names within each group should be different
        assert len(reg_names) == 4  # native_language, target_language, level, confirming
        assert len(add_names) == 3  # waiting_for_word, selecting_meaning, confirming
        assert len(lesson_names) == 3  # in_progress, answering_question, viewing_result

    def test_states_from_different_groups_are_distinct(self):
        """Test that states from different groups have different values."""
        # Even though both have 'confirming' state, they should be different
        reg_confirming = RegistrationStates.confirming
        add_confirming = AddWordStates.confirming

        assert reg_confirming.state != add_confirming.state

    def test_all_states_are_unique_across_groups(self):
        """Test that all state values are unique across all groups."""
        all_states = []

        # Collect states from RegistrationStates
        for attr in dir(RegistrationStates):
            state = getattr(RegistrationStates, attr)
            if isinstance(state, State):
                all_states.append(state.state)

        # Collect states from AddWordStates
        for attr in dir(AddWordStates):
            state = getattr(AddWordStates, attr)
            if isinstance(state, State):
                all_states.append(state.state)

        # Collect states from LessonStates
        for attr in dir(LessonStates):
            state = getattr(LessonStates, attr)
            if isinstance(state, State):
                all_states.append(state.state)

        # All state strings should be unique
        assert len(all_states) == len(set(all_states))


class TestPackageExports:
    """Tests for package __all__ exports."""

    def test_states_init_exports(self):
        """Test that states/__init__.py exports all state groups."""
        from words.bot.states import __all__ as states_all

        assert "RegistrationStates" in states_all
        assert "AddWordStates" in states_all
        assert "LessonStates" in states_all
        assert len(states_all) == 3

    def test_bot_init_exports(self):
        """Test that bot/__init__.py exports all state groups."""
        from words.bot import __all__ as bot_all

        assert "RegistrationStates" in bot_all
        assert "AddWordStates" in bot_all
        assert "LessonStates" in bot_all
        assert "setup_bot" in bot_all
        assert len(bot_all) == 4

    def test_direct_imports_match_package_imports(self):
        """Test that direct imports match package exports."""
        # Import from bot package
        from words.bot import AddWordStates as BotAdd
        from words.bot import LessonStates as BotLesson
        from words.bot import RegistrationStates as BotReg

        # Import from states subpackage
        from words.bot.states import AddWordStates as StatesAdd
        from words.bot.states import LessonStates as StatesLesson
        from words.bot.states import RegistrationStates as StatesReg

        # Import directly from module
        from words.bot.states.registration import AddWordStates as DirectAdd
        from words.bot.states.registration import LessonStates as DirectLesson
        from words.bot.states.registration import (
            RegistrationStates as DirectReg,
        )

        # All should be the same class
        assert BotReg is StatesReg is DirectReg
        assert BotAdd is StatesAdd is DirectAdd
        assert BotLesson is StatesLesson is DirectLesson


class TestStateMachineUsability:
    """Tests for practical usability of state machines with aiogram."""

    def test_can_access_state_as_string(self):
        """Test that states can be accessed as strings for aiogram compatibility."""
        state = RegistrationStates.native_language
        assert isinstance(state.state, str)
        assert len(state.state) > 0

    def test_can_compare_states(self):
        """Test that states can be compared."""
        state1 = RegistrationStates.native_language
        state2 = RegistrationStates.native_language
        state3 = RegistrationStates.target_language

        # Same states should be equal
        assert state1 == state2
        # Different states should not be equal
        assert state1 != state3

    def test_states_are_hashable(self):
        """Test that states can be used in sets and as dict keys."""
        states_set = {
            RegistrationStates.native_language,
            RegistrationStates.target_language,
            RegistrationStates.level,
        }
        assert len(states_set) == 3

        # Can use as dict keys
        state_dict = {RegistrationStates.native_language: "native"}
        assert state_dict[RegistrationStates.native_language] == "native"

    def test_state_group_states_property(self):
        """Test that state groups have a __states__ property."""
        # aiogram StatesGroup should provide access to all states
        assert hasattr(RegistrationStates, "__states__")

    def test_state_repr(self):
        """Test that states have meaningful string representations."""
        state = RegistrationStates.native_language
        repr_str = repr(state)
        assert isinstance(repr_str, str)
        assert len(repr_str) > 0
