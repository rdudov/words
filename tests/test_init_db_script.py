"""
Comprehensive tests for scripts/init_db.py database initialization script.

Tests cover:
- Script execution and success path
- Database directory creation for SQLite
- Idempotency (can run multiple times)
- Error handling and logging
- Proper engine disposal in all cases
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest
import tempfile
import shutil


# Add scripts directory to path for imports
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR.parent))


class TestDatabaseDirectoryCreation:
    """Tests for create_database_directory function."""

    def test_creates_directory_for_sqlite(self):
        """Test that directory is created for SQLite database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_db_path = Path(tmpdir) / "test_data" / "database" / "test.db"

            with patch("scripts.init_db.settings") as mock_settings:
                mock_settings.database_url = f"sqlite+aiosqlite:///{test_db_path}"

                # Import the function
                from scripts.init_db import create_database_directory

                create_database_directory()

                # Verify directory was created
                assert test_db_path.parent.exists()
                assert test_db_path.parent.is_dir()

    def test_handles_relative_sqlite_path(self):
        """Test that relative SQLite paths are handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(tmpdir)

                test_db_path = "data/database/test.db"

                with patch("scripts.init_db.settings") as mock_settings:
                    mock_settings.database_url = f"sqlite+aiosqlite:///{test_db_path}"

                    from scripts.init_db import create_database_directory

                    create_database_directory()

                    # Verify directory was created
                    full_path = Path(tmpdir) / "data" / "database"
                    assert full_path.exists()
                    assert full_path.is_dir()
            finally:
                os.chdir(original_cwd)

    def test_skips_directory_creation_for_postgresql(self):
        """Test that directory creation is skipped for PostgreSQL."""
        with patch("scripts.init_db.settings") as mock_settings:
            mock_settings.database_url = "postgresql+asyncpg://user:pass@localhost/words"

            with patch("pathlib.Path.mkdir") as mock_mkdir:
                from scripts.init_db import create_database_directory

                create_database_directory()

                # mkdir should not be called for PostgreSQL
                mock_mkdir.assert_not_called()

    def test_handles_existing_directory(self):
        """Test that existing directory doesn't cause error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_db_path = Path(tmpdir) / "existing" / "database" / "test.db"
            # Pre-create the directory
            test_db_path.parent.mkdir(parents=True, exist_ok=True)

            with patch("scripts.init_db.settings") as mock_settings:
                mock_settings.database_url = f"sqlite+aiosqlite:///{test_db_path}"

                from scripts.init_db import create_database_directory

                # Should not raise error
                create_database_directory()

                # Verify directory still exists
                assert test_db_path.parent.exists()

    def test_handles_directory_creation_error_gracefully(self, caplog):
        """Test that directory creation errors are logged but don't crash."""
        import logging
        caplog.set_level(logging.WARNING)

        with patch("scripts.init_db.settings") as mock_settings:
            # Use a path with a subdirectory so mkdir is actually called
            mock_settings.database_url = "sqlite+aiosqlite:///subdir/test.db"

            with patch("pathlib.Path.mkdir", side_effect=PermissionError("No permission")):
                from scripts.init_db import create_database_directory

                # Should not raise exception
                create_database_directory()

                # Should log warning
                assert "Could not create database directory" in caplog.text

    def test_handles_current_directory_sqlite_path(self):
        """Test SQLite path in current directory (no subdirectory)."""
        with patch("scripts.init_db.settings") as mock_settings:
            mock_settings.database_url = "sqlite+aiosqlite:///test.db"

            with patch("pathlib.Path.mkdir") as mock_mkdir:
                from scripts.init_db import create_database_directory

                create_database_directory()

                # mkdir should not be called for current directory
                mock_mkdir.assert_not_called()


class TestMainFunction:
    """Tests for main() async function."""

    @pytest.mark.asyncio
    async def test_main_calls_init_db(self):
        """Test that main() calls init_db()."""
        with patch("scripts.init_db.init_db", new_callable=AsyncMock) as mock_init_db:
            with patch("scripts.init_db.engine") as mock_engine:
                mock_engine.dispose = AsyncMock()
                with patch("scripts.init_db.create_database_directory"):
                    from scripts.init_db import main

                    await main()

                    mock_init_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_creates_database_directory(self):
        """Test that main() creates database directory."""
        with patch("scripts.init_db.init_db", new_callable=AsyncMock):
            with patch("scripts.init_db.engine") as mock_engine:
                mock_engine.dispose = AsyncMock()
                with patch("scripts.init_db.create_database_directory") as mock_create_dir:
                    from scripts.init_db import main

                    await main()

                    mock_create_dir.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_disposes_engine_on_success(self):
        """Test that main() disposes engine after successful initialization."""
        with patch("scripts.init_db.init_db", new_callable=AsyncMock):
            with patch("scripts.init_db.engine") as mock_engine:
                mock_engine.dispose = AsyncMock()
                with patch("scripts.init_db.create_database_directory"):
                    from scripts.init_db import main

                    await main()

                    mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_disposes_engine_on_error(self):
        """Test that main() disposes engine even when init_db fails."""
        with patch("scripts.init_db.init_db", new_callable=AsyncMock, side_effect=Exception("DB error")):
            with patch("scripts.init_db.engine") as mock_engine:
                mock_engine.dispose = AsyncMock()
                with patch("scripts.init_db.create_database_directory"):
                    from scripts.init_db import main

                    with pytest.raises(Exception, match="DB error"):
                        await main()

                    # Engine should still be disposed
                    mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_logs_start(self, caplog):
        """Test that main() logs initialization start."""
        import logging
        caplog.set_level(logging.INFO)

        with patch("scripts.init_db.init_db", new_callable=AsyncMock):
            with patch("scripts.init_db.engine") as mock_engine:
                mock_engine.dispose = AsyncMock()
                with patch("scripts.init_db.create_database_directory"):
                    from scripts.init_db import main

                    await main()

                    assert "Starting database initialization" in caplog.text

    @pytest.mark.asyncio
    async def test_main_logs_success(self, caplog):
        """Test that main() logs successful initialization."""
        import logging
        caplog.set_level(logging.INFO)

        with patch("scripts.init_db.init_db", new_callable=AsyncMock):
            with patch("scripts.init_db.engine") as mock_engine:
                mock_engine.dispose = AsyncMock()
                with patch("scripts.init_db.create_database_directory"):
                    from scripts.init_db import main

                    await main()

                    assert "Database initialized successfully" in caplog.text

    @pytest.mark.asyncio
    async def test_main_logs_error(self, caplog):
        """Test that main() logs initialization errors."""
        import logging
        caplog.set_level(logging.ERROR)

        test_error = Exception("Test database error")

        with patch("scripts.init_db.init_db", new_callable=AsyncMock, side_effect=test_error):
            with patch("scripts.init_db.engine") as mock_engine:
                mock_engine.dispose = AsyncMock()
                with patch("scripts.init_db.create_database_directory"):
                    from scripts.init_db import main

                    with pytest.raises(Exception):
                        await main()

                    assert "Failed to initialize database" in caplog.text

    @pytest.mark.asyncio
    async def test_main_propagates_exception(self):
        """Test that main() propagates exceptions after logging."""
        test_error = ValueError("Database initialization failed")

        with patch("scripts.init_db.init_db", new_callable=AsyncMock, side_effect=test_error):
            with patch("scripts.init_db.engine") as mock_engine:
                mock_engine.dispose = AsyncMock()
                with patch("scripts.init_db.create_database_directory"):
                    from scripts.init_db import main

                    with pytest.raises(ValueError, match="Database initialization failed"):
                        await main()


class TestScriptIdempotency:
    """Tests for script idempotency (can run multiple times safely)."""

    @pytest.mark.asyncio
    async def test_script_can_run_multiple_times(self):
        """Test that script can be executed multiple times without errors."""
        with patch("scripts.init_db.init_db", new_callable=AsyncMock) as mock_init_db:
            with patch("scripts.init_db.engine") as mock_engine:
                mock_engine.dispose = AsyncMock()
                with patch("scripts.init_db.create_database_directory"):
                    from scripts.init_db import main

                    # Run multiple times
                    await main()
                    await main()
                    await main()

                    # Should have been called three times
                    assert mock_init_db.call_count == 3
                    assert mock_engine.dispose.call_count == 3

    @pytest.mark.asyncio
    async def test_directory_creation_is_idempotent(self):
        """Test that directory creation can be called multiple times."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_db_path = Path(tmpdir) / "data" / "database" / "test.db"

            with patch("scripts.init_db.settings") as mock_settings:
                mock_settings.database_url = f"sqlite+aiosqlite:///{test_db_path}"

                from scripts.init_db import create_database_directory

                # Call multiple times
                create_database_directory()
                create_database_directory()
                create_database_directory()

                # Directory should still exist and be valid
                assert test_db_path.parent.exists()
                assert test_db_path.parent.is_dir()


class TestScriptExecution:
    """Tests for script execution via __main__ block."""

    def test_script_has_main_block(self):
        """Test that script has __main__ block."""
        script_path = SCRIPTS_DIR / "init_db.py"
        with open(script_path) as f:
            content = f.read()
            assert 'if __name__ == "__main__":' in content
            assert "asyncio.run(main())" in content

    @patch("scripts.init_db.asyncio.run")
    @patch("scripts.init_db.main")
    def test_main_block_calls_asyncio_run(self, mock_main, mock_asyncio_run):
        """Test that __main__ block uses asyncio.run(main())."""
        # This test verifies the pattern but can't directly test __main__ block
        # We verify that the pattern exists in the file
        script_path = SCRIPTS_DIR / "init_db.py"
        with open(script_path) as f:
            content = f.read()
            # Verify the correct pattern is present
            assert "asyncio.run(main())" in content


class TestScriptImports:
    """Tests for script imports and path setup."""

    def test_script_adds_src_to_path(self):
        """Test that script adds src directory to sys.path."""
        script_path = SCRIPTS_DIR / "init_db.py"
        with open(script_path) as f:
            content = f.read()
            assert "sys.path.insert(0" in content
            assert "Path(__file__).parent.parent" in content

    def test_script_imports_required_modules(self):
        """Test that script imports all required modules."""
        script_path = SCRIPTS_DIR / "init_db.py"
        with open(script_path) as f:
            content = f.read()

            # Check for required imports
            assert "import asyncio" in content
            assert "import sys" in content
            assert "from pathlib import Path" in content
            assert "from src.words.infrastructure.database import init_db, engine" in content
            assert "from src.words.utils.logger import logger" in content
            assert "from src.words.config.settings import settings" in content

    def test_can_import_script_functions(self):
        """Test that we can import functions from the script."""
        from scripts.init_db import main, create_database_directory

        assert callable(main)
        assert callable(create_database_directory)


class TestErrorHandling:
    """Tests for various error scenarios."""

    @pytest.mark.asyncio
    async def test_handles_database_connection_error(self, caplog):
        """Test handling of database connection errors."""
        import logging
        caplog.set_level(logging.ERROR)

        connection_error = Exception("Connection refused")

        with patch("scripts.init_db.init_db", new_callable=AsyncMock, side_effect=connection_error):
            with patch("scripts.init_db.engine") as mock_engine:
                mock_engine.dispose = AsyncMock()
                with patch("scripts.init_db.create_database_directory"):
                    from scripts.init_db import main

                    with pytest.raises(Exception):
                        await main()

                    # Error should be logged
                    assert "Failed to initialize database" in caplog.text
                    # Engine should still be disposed
                    mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_permission_error(self, caplog):
        """Test handling of permission errors during initialization."""
        import logging
        caplog.set_level(logging.ERROR)

        permission_error = PermissionError("Permission denied")

        with patch("scripts.init_db.init_db", new_callable=AsyncMock, side_effect=permission_error):
            with patch("scripts.init_db.engine") as mock_engine:
                mock_engine.dispose = AsyncMock()
                with patch("scripts.init_db.create_database_directory"):
                    from scripts.init_db import main

                    with pytest.raises(PermissionError):
                        await main()

                    # Error should be logged
                    assert "Failed to initialize database" in caplog.text

    @pytest.mark.asyncio
    async def test_engine_disposal_error_doesnt_mask_original_error(self):
        """Test that engine disposal errors don't mask the original error."""
        original_error = ValueError("Original initialization error")
        disposal_error = Exception("Disposal error")

        with patch("scripts.init_db.init_db", new_callable=AsyncMock, side_effect=original_error):
            with patch("scripts.init_db.engine") as mock_engine:
                mock_engine.dispose = AsyncMock(side_effect=disposal_error)
                with patch("scripts.init_db.create_database_directory"):
                    from scripts.init_db import main

                    # Should raise the original error, not disposal error
                    with pytest.raises(ValueError, match="Original initialization error"):
                        await main()


class TestLogging:
    """Tests for logging behavior."""

    @pytest.mark.asyncio
    async def test_logs_include_structured_context(self, caplog):
        """Test that logs include structured context (if using structlog)."""
        import logging
        caplog.set_level(logging.INFO)

        with patch("scripts.init_db.init_db", new_callable=AsyncMock):
            with patch("scripts.init_db.engine") as mock_engine:
                mock_engine.dispose = AsyncMock()
                with patch("scripts.init_db.create_database_directory"):
                    from scripts.init_db import main

                    await main()

                    # Verify key log messages are present
                    assert "Starting database initialization" in caplog.text
                    assert "Database initialized successfully" in caplog.text

    @pytest.mark.asyncio
    async def test_logs_debug_message_on_disposal(self, caplog):
        """Test that engine disposal is logged at debug level."""
        import logging

        # Set both caplog and the structlog logger to DEBUG level
        caplog.set_level(logging.DEBUG)
        # Also need to configure the structlog logger to output DEBUG messages
        with patch("scripts.init_db.logger") as mock_logger:
            mock_logger.info = MagicMock()
            mock_logger.error = MagicMock()
            mock_logger.debug = MagicMock()

            with patch("scripts.init_db.init_db", new_callable=AsyncMock):
                with patch("scripts.init_db.engine") as mock_engine:
                    mock_engine.dispose = AsyncMock()
                    with patch("scripts.init_db.create_database_directory"):
                        from scripts.init_db import main

                        await main()

                        # Verify debug was called for engine disposal
                        mock_logger.debug.assert_called_with("Database engine disposed")


class TestIntegrationScenarios:
    """Integration tests for complete scenarios."""

    @pytest.mark.asyncio
    async def test_full_initialization_flow(self, caplog):
        """Test complete initialization flow from start to finish."""
        import logging
        caplog.set_level(logging.INFO)

        with patch("scripts.init_db.init_db", new_callable=AsyncMock) as mock_init_db:
            with patch("scripts.init_db.engine") as mock_engine:
                mock_engine.dispose = AsyncMock()
                with patch("scripts.init_db.create_database_directory") as mock_create_dir:
                    from scripts.init_db import main

                    await main()

                    # Verify complete flow
                    mock_create_dir.assert_called_once()
                    mock_init_db.assert_called_once()
                    mock_engine.dispose.assert_called_once()

                    # Verify logging
                    assert "Starting database initialization" in caplog.text
                    assert "Database initialized successfully" in caplog.text

    @pytest.mark.asyncio
    async def test_initialization_with_sqlite_database(self):
        """Test initialization flow with SQLite database configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_db_path = Path(tmpdir) / "data" / "database" / "test.db"

            with patch("scripts.init_db.settings") as mock_settings:
                mock_settings.database_url = f"sqlite+aiosqlite:///{test_db_path}"

                with patch("scripts.init_db.init_db", new_callable=AsyncMock):
                    with patch("scripts.init_db.engine") as mock_engine:
                        mock_engine.dispose = AsyncMock()

                        from scripts.init_db import main

                        await main()

                        # Verify directory was created
                        assert test_db_path.parent.exists()
                        # Verify engine was disposed
                        mock_engine.dispose.assert_called_once()
