"""Tests for bot setup and initialization.

This module tests the bot setup function that initializes the Bot and
Dispatcher instances with proper configuration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

from words.bot import setup_bot


class TestSetupBot:
    """Tests for setup_bot() function."""

    @pytest.mark.asyncio
    async def test_setup_bot_returns_tuple(self):
        """Test that setup_bot returns a tuple of Bot and Dispatcher."""
        with patch("words.bot.Bot") as mock_bot_class, \
             patch("words.bot.Dispatcher") as mock_dp_class, \
             patch("words.bot.logger"):

            # Setup mocks
            mock_bot = MagicMock(spec=Bot)
            mock_dp = MagicMock(spec=Dispatcher)
            mock_bot_class.return_value = mock_bot
            mock_dp_class.return_value = mock_dp

            # Call setup_bot
            result = await setup_bot()

            # Verify result is tuple with Bot and Dispatcher
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert result[0] is mock_bot
            assert result[1] is mock_dp

    @pytest.mark.asyncio
    async def test_setup_bot_creates_bot_with_token(self):
        """Test that Bot is created with correct token from settings."""
        with patch("words.bot.Bot") as mock_bot_class, \
             patch("words.bot.Dispatcher"), \
             patch("words.bot.logger"), \
             patch("words.bot.settings") as mock_settings:

            # Setup mock settings
            mock_settings.telegram_bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

            # Call setup_bot
            await setup_bot()

            # Verify Bot was created with correct token
            mock_bot_class.assert_called_once()
            call_kwargs = mock_bot_class.call_args[1]
            assert call_kwargs["token"] == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

    @pytest.mark.asyncio
    async def test_setup_bot_configures_html_parse_mode(self):
        """Test that Bot is configured with HTML parse mode."""
        with patch("words.bot.Bot") as mock_bot_class, \
             patch("words.bot.Dispatcher"), \
             patch("words.bot.logger"), \
             patch("words.bot.DefaultBotProperties") as mock_props:

            # Call setup_bot
            await setup_bot()

            # Verify DefaultBotProperties was created with HTML parse mode
            mock_props.assert_called_once_with(parse_mode=ParseMode.HTML)

            # Verify Bot was created with default properties
            call_kwargs = mock_bot_class.call_args[1]
            assert "default" in call_kwargs

    @pytest.mark.asyncio
    async def test_setup_bot_creates_dispatcher_with_memory_storage(self):
        """Test that Dispatcher is created with MemoryStorage."""
        with patch("words.bot.Bot"), \
             patch("words.bot.Dispatcher") as mock_dp_class, \
             patch("words.bot.logger"), \
             patch("words.bot.MemoryStorage") as mock_storage_class:

            # Setup mock storage
            mock_storage = MagicMock(spec=MemoryStorage)
            mock_storage_class.return_value = mock_storage

            # Call setup_bot
            await setup_bot()

            # Verify MemoryStorage was created
            mock_storage_class.assert_called_once()

            # Verify Dispatcher was created with storage
            mock_dp_class.assert_called_once()
            call_kwargs = mock_dp_class.call_args[1]
            assert call_kwargs["storage"] is mock_storage

    @pytest.mark.asyncio
    async def test_setup_bot_registers_start_router(self):
        """Test that start_router is registered with the dispatcher."""
        with patch("words.bot.Bot"), \
             patch("words.bot.Dispatcher") as mock_dp_class, \
             patch("words.bot.logger"):

            # Setup mock dispatcher
            mock_dp = MagicMock(spec=Dispatcher)
            mock_dp.include_router = MagicMock()
            mock_dp_class.return_value = mock_dp

            # Call setup_bot
            await setup_bot()

            # Verify router was registered (we check it was called at least once)
            assert mock_dp.include_router.called
            # Verify it was called with any Router
            assert len(mock_dp.include_router.call_args_list) > 0

    @pytest.mark.asyncio
    async def test_setup_bot_logs_initialization(self):
        """Test that bot initialization is logged."""
        with patch("words.bot.Bot"), \
             patch("words.bot.Dispatcher"), \
             patch("words.bot.logger") as mock_logger:

            # Call setup_bot
            await setup_bot()

            # Verify logger was called
            mock_logger.info.assert_called_with("Bot initialized")

    @pytest.mark.asyncio
    async def test_setup_bot_can_be_imported_from_package(self):
        """Test that setup_bot can be imported from the bot package."""
        from words.bot import setup_bot as imported_setup

        assert imported_setup is setup_bot
        assert callable(imported_setup)

    @pytest.mark.asyncio
    async def test_setup_bot_is_in_all_exports(self):
        """Test that setup_bot is in __all__ exports."""
        from words.bot import __all__

        assert "setup_bot" in __all__


class TestBotPackageExports:
    """Tests for bot package exports."""

    def test_all_exports_include_setup_bot(self):
        """Test that __all__ includes setup_bot along with states."""
        from words.bot import __all__

        expected_exports = {
            "RegistrationStates",
            "AddWordStates",
            "LessonStates",
            "setup_bot",
        }

        assert expected_exports.issubset(set(__all__))

    def test_can_import_all_exports(self):
        """Test that all exports can be imported."""
        from words.bot import (
            RegistrationStates,
            AddWordStates,
            LessonStates,
            setup_bot,
        )

        assert RegistrationStates is not None
        assert AddWordStates is not None
        assert LessonStates is not None
        assert setup_bot is not None
        assert callable(setup_bot)


class TestBotIntegration:
    """Integration tests for bot setup without mocks."""

    @pytest.mark.asyncio
    async def test_setup_bot_creates_real_instances(self):
        """Test that setup_bot creates real Bot and Dispatcher instances."""
        # This test uses real instances to verify integration
        bot, dp = await setup_bot()

        try:
            # Verify types
            assert isinstance(bot, Bot)
            assert isinstance(dp, Dispatcher)

            # Verify dispatcher has routers registered
            assert len(dp.sub_routers) > 0

            # Verify bot has session
            assert bot.session is not None

            # The token should be set (we can't directly access it but can verify bot is valid)
            assert bot.token is not None
            assert len(bot.token) > 0
        finally:
            # Cleanup
            if bot.session:
                await bot.session.close()
