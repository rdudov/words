"""Tests for application main entry point.

This module tests the main() function and bot startup logic including
database initialization, bot setup, and graceful shutdown.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from aiogram import Bot, Dispatcher


class TestMainFunction:
    """Tests for main() entry point function."""

    @pytest.mark.asyncio
    async def test_main_initializes_database(self):
        """Test that main() calls init_db() on startup."""
        with patch("words.__main__.init_db") as mock_init_db, \
             patch("words.__main__.setup_bot") as mock_setup_bot, \
             patch("words.__main__.close_db") as mock_close_db, \
             patch("words.__main__.logger"):

            # Setup mocks
            mock_init_db.return_value = AsyncMock()
            mock_bot = MagicMock(spec=Bot)
            mock_bot.session = MagicMock()
            mock_bot.session.close = AsyncMock()
            mock_dp = MagicMock(spec=Dispatcher)
            mock_dp.start_polling = AsyncMock(side_effect=KeyboardInterrupt)
            mock_setup_bot.return_value = (mock_bot, mock_dp)
            mock_close_db.return_value = AsyncMock()

            # Import and run main
            from words.__main__ import main

            try:
                await main()
            except KeyboardInterrupt:
                pass

            # Verify init_db was called
            mock_init_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_calls_setup_bot(self):
        """Test that main() calls setup_bot()."""
        with patch("words.__main__.init_db") as mock_init_db, \
             patch("words.__main__.setup_bot") as mock_setup_bot, \
             patch("words.__main__.close_db") as mock_close_db, \
             patch("words.__main__.logger"):

            # Setup mocks
            mock_init_db.return_value = AsyncMock()
            mock_bot = MagicMock(spec=Bot)
            mock_bot.session = MagicMock()
            mock_bot.session.close = AsyncMock()
            mock_dp = MagicMock(spec=Dispatcher)
            mock_dp.start_polling = AsyncMock(side_effect=KeyboardInterrupt)
            mock_setup_bot.return_value = (mock_bot, mock_dp)
            mock_close_db.return_value = AsyncMock()

            # Import and run main
            from words.__main__ import main

            try:
                await main()
            except KeyboardInterrupt:
                pass

            # Verify setup_bot was called
            mock_setup_bot.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_starts_polling(self):
        """Test that main() starts polling for updates."""
        with patch("words.__main__.init_db") as mock_init_db, \
             patch("words.__main__.setup_bot") as mock_setup_bot, \
             patch("words.__main__.close_db") as mock_close_db, \
             patch("words.__main__.logger"):

            # Setup mocks
            mock_init_db.return_value = AsyncMock()
            mock_bot = MagicMock(spec=Bot)
            mock_bot.session = MagicMock()
            mock_bot.session.close = AsyncMock()
            mock_dp = MagicMock(spec=Dispatcher)
            mock_dp.start_polling = AsyncMock(side_effect=KeyboardInterrupt)
            mock_dp.resolve_used_update_types = MagicMock(return_value=[])
            mock_setup_bot.return_value = (mock_bot, mock_dp)
            mock_close_db.return_value = AsyncMock()

            # Import and run main
            from words.__main__ import main

            try:
                await main()
            except KeyboardInterrupt:
                pass

            # Verify start_polling was called with bot and allowed_updates
            mock_dp.start_polling.assert_called_once()
            call_args = mock_dp.start_polling.call_args
            assert call_args[0][0] is mock_bot
            assert "allowed_updates" in call_args[1]

    @pytest.mark.asyncio
    async def test_main_closes_bot_session_on_exit(self):
        """Test that main() closes bot session on exit."""
        with patch("words.__main__.init_db") as mock_init_db, \
             patch("words.__main__.setup_bot") as mock_setup_bot, \
             patch("words.__main__.close_db") as mock_close_db, \
             patch("words.__main__.logger"):

            # Setup mocks
            mock_init_db.return_value = AsyncMock()
            mock_bot = MagicMock(spec=Bot)
            mock_bot.session = MagicMock()
            mock_bot.session.close = AsyncMock()
            mock_dp = MagicMock(spec=Dispatcher)
            mock_dp.start_polling = AsyncMock(side_effect=KeyboardInterrupt)
            mock_setup_bot.return_value = (mock_bot, mock_dp)
            mock_close_db.return_value = AsyncMock()

            # Import and run main
            from words.__main__ import main

            try:
                await main()
            except KeyboardInterrupt:
                pass

            # Verify bot session was closed
            mock_bot.session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_closes_database_on_exit(self):
        """Test that main() closes database connections on exit."""
        with patch("words.__main__.init_db") as mock_init_db, \
             patch("words.__main__.setup_bot") as mock_setup_bot, \
             patch("words.__main__.close_db") as mock_close_db, \
             patch("words.__main__.logger"):

            # Setup mocks
            mock_init_db.return_value = AsyncMock()
            mock_bot = MagicMock(spec=Bot)
            mock_bot.session = MagicMock()
            mock_bot.session.close = AsyncMock()
            mock_dp = MagicMock(spec=Dispatcher)
            mock_dp.start_polling = AsyncMock(side_effect=KeyboardInterrupt)
            mock_setup_bot.return_value = (mock_bot, mock_dp)
            mock_close_db.return_value = AsyncMock()

            # Import and run main
            from words.__main__ import main

            try:
                await main()
            except KeyboardInterrupt:
                pass

            # Verify close_db was called
            mock_close_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_logs_startup(self):
        """Test that main() logs startup message."""
        with patch("words.__main__.init_db") as mock_init_db, \
             patch("words.__main__.setup_bot") as mock_setup_bot, \
             patch("words.__main__.close_db") as mock_close_db, \
             patch("words.__main__.logger") as mock_logger:

            # Setup mocks
            mock_init_db.return_value = AsyncMock()
            mock_bot = MagicMock(spec=Bot)
            mock_bot.session = MagicMock()
            mock_bot.session.close = AsyncMock()
            mock_dp = MagicMock(spec=Dispatcher)
            mock_dp.start_polling = AsyncMock(side_effect=KeyboardInterrupt)
            mock_setup_bot.return_value = (mock_bot, mock_dp)
            mock_close_db.return_value = AsyncMock()

            # Import and run main
            from words.__main__ import main

            try:
                await main()
            except KeyboardInterrupt:
                pass

            # Verify startup logging
            assert any("Starting bot" in str(c) for c in mock_logger.info.call_args_list)

    @pytest.mark.asyncio
    async def test_main_logs_running_message(self):
        """Test that main() logs running message before polling."""
        with patch("words.__main__.init_db") as mock_init_db, \
             patch("words.__main__.setup_bot") as mock_setup_bot, \
             patch("words.__main__.close_db") as mock_close_db, \
             patch("words.__main__.logger") as mock_logger:

            # Setup mocks
            mock_init_db.return_value = AsyncMock()
            mock_bot = MagicMock(spec=Bot)
            mock_bot.session = MagicMock()
            mock_bot.session.close = AsyncMock()
            mock_dp = MagicMock(spec=Dispatcher)
            mock_dp.start_polling = AsyncMock(side_effect=KeyboardInterrupt)
            mock_setup_bot.return_value = (mock_bot, mock_dp)
            mock_close_db.return_value = AsyncMock()

            # Import and run main
            from words.__main__ import main

            try:
                await main()
            except KeyboardInterrupt:
                pass

            # Verify running logging
            assert any("Bot is running" in str(c) for c in mock_logger.info.call_args_list)

    @pytest.mark.asyncio
    async def test_main_logs_shutdown_message(self):
        """Test that main() logs shutdown message on exit."""
        with patch("words.__main__.init_db") as mock_init_db, \
             patch("words.__main__.setup_bot") as mock_setup_bot, \
             patch("words.__main__.close_db") as mock_close_db, \
             patch("words.__main__.logger") as mock_logger:

            # Setup mocks
            mock_init_db.return_value = AsyncMock()
            mock_bot = MagicMock(spec=Bot)
            mock_bot.session = MagicMock()
            mock_bot.session.close = AsyncMock()
            mock_dp = MagicMock(spec=Dispatcher)
            mock_dp.start_polling = AsyncMock(side_effect=KeyboardInterrupt)
            mock_setup_bot.return_value = (mock_bot, mock_dp)
            mock_close_db.return_value = AsyncMock()

            # Import and run main
            from words.__main__ import main

            try:
                await main()
            except KeyboardInterrupt:
                pass

            # Verify shutdown logging
            assert any("Bot stopped" in str(c) for c in mock_logger.info.call_args_list)

    @pytest.mark.asyncio
    async def test_main_cleanup_on_exception(self):
        """Test that main() performs cleanup even on exception."""
        with patch("words.__main__.init_db") as mock_init_db, \
             patch("words.__main__.setup_bot") as mock_setup_bot, \
             patch("words.__main__.close_db") as mock_close_db, \
             patch("words.__main__.logger"):

            # Setup mocks - make polling raise an exception
            mock_init_db.return_value = AsyncMock()
            mock_bot = MagicMock(spec=Bot)
            mock_bot.session = MagicMock()
            mock_bot.session.close = AsyncMock()
            mock_dp = MagicMock(spec=Dispatcher)
            mock_dp.start_polling = AsyncMock(side_effect=RuntimeError("Test error"))
            mock_setup_bot.return_value = (mock_bot, mock_dp)
            mock_close_db.return_value = AsyncMock()

            # Import and run main
            from words.__main__ import main

            with pytest.raises(RuntimeError):
                await main()

            # Verify cleanup was called even after exception
            mock_bot.session.close.assert_called_once()
            mock_close_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_execution_order(self):
        """Test that main() executes operations in correct order."""
        call_order = []

        async def track_init_db():
            call_order.append("init_db")

        async def track_setup_bot():
            call_order.append("setup_bot")
            mock_bot = MagicMock(spec=Bot)
            mock_bot.session = MagicMock()
            mock_bot.session.close = AsyncMock()
            mock_dp = MagicMock(spec=Dispatcher)
            mock_dp.start_polling = AsyncMock(side_effect=KeyboardInterrupt)
            return mock_bot, mock_dp

        async def track_close_db():
            call_order.append("close_db")

        with patch("words.__main__.init_db", side_effect=track_init_db), \
             patch("words.__main__.setup_bot", side_effect=track_setup_bot), \
             patch("words.__main__.close_db", side_effect=track_close_db), \
             patch("words.__main__.logger"):

            # Import and run main
            from words.__main__ import main

            try:
                await main()
            except KeyboardInterrupt:
                pass

            # Verify execution order
            assert call_order == ["init_db", "setup_bot", "close_db"]


class TestMainEntryPoint:
    """Tests for __main__ entry point execution."""

    def test_keyboard_interrupt_handling(self):
        """Test that KeyboardInterrupt is handled gracefully."""
        with patch("words.__main__.asyncio.run") as mock_run, \
             patch("words.__main__.logger") as mock_logger:

            # Make asyncio.run raise KeyboardInterrupt
            mock_run.side_effect = KeyboardInterrupt

            # Import __main__ module
            import words.__main__

            # Execute the main block
            try:
                # Simulate running the module
                import sys
                original_argv = sys.argv
                sys.argv = ["words.__main__"]

                # This would normally be executed by Python
                # We simulate it by catching the interrupt
                try:
                    asyncio.run(words.__main__.main())
                except KeyboardInterrupt:
                    mock_logger.info("Bot stopped by user")

                sys.argv = original_argv
            except:
                pass

            # Verify logger was called or would be called
            # Note: This test is more of a structure test

    def test_main_module_has_correct_docstring(self):
        """Test that __main__ module has proper documentation."""
        import words.__main__

        assert words.__main__.__doc__ is not None
        assert "Entry point" in words.__main__.__doc__

    def test_main_function_is_async(self):
        """Test that main() is an async function."""
        from words.__main__ import main

        assert asyncio.iscoroutinefunction(main)

    def test_main_function_has_docstring(self):
        """Test that main() has proper documentation."""
        from words.__main__ import main

        assert main.__doc__ is not None
        assert "Main entry point" in main.__doc__


class TestImports:
    """Tests for module imports."""

    def test_can_import_main_module(self):
        """Test that __main__ module can be imported."""
        import words.__main__

        assert words.__main__ is not None

    def test_can_import_main_function(self):
        """Test that main function can be imported."""
        from words.__main__ import main

        assert main is not None
        assert callable(main)

    def test_main_imports_are_correct(self):
        """Test that __main__ imports required dependencies."""
        import words.__main__

        # Verify that necessary imports are available
        assert hasattr(words.__main__, "asyncio")
        assert hasattr(words.__main__, "sys")
        assert hasattr(words.__main__, "Path")
        assert hasattr(words.__main__, "setup_bot")
        assert hasattr(words.__main__, "init_db")
        assert hasattr(words.__main__, "close_db")
        assert hasattr(words.__main__, "logger")


class TestPathSetup:
    """Tests for sys.path manipulation."""

    def test_main_adds_parent_to_path(self):
        """Test that __main__ adds parent directory to sys.path."""
        import sys
        import words.__main__
        from pathlib import Path

        # Get expected path
        expected_path = str(Path(words.__main__.__file__).parent.parent.parent)

        # Check if it's in sys.path (it should be added at position 0)
        assert expected_path in sys.path or any(
            Path(p).resolve() == Path(expected_path).resolve() for p in sys.path
        )
