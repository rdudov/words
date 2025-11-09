"""
Initialize database schema for the Words application.

This script creates all database tables defined in the ORM models.
It is idempotent and can be run multiple times safely.

Usage:
    python scripts/init_db.py
"""

import asyncio
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.words.infrastructure.database import init_db, engine
from src.words.config.settings import settings

logger = logging.getLogger(__name__)


def create_database_directory():
    """
    Create database directory if using SQLite and it doesn't exist.

    Extracts the database path from DATABASE_URL and creates parent directories.
    Only applicable for SQLite databases.
    """
    db_url = settings.database_url

    # Check if it's a SQLite database
    if "sqlite" in db_url:
        try:
            # Parse the URL to extract the file path
            # Format: sqlite+aiosqlite:///path/to/db.db or sqlite:///path/to/db.db
            # In SQLite URLs:
            #   sqlite:///relative/path.db -> relative path (parsed.path = '/relative/path.db')
            #   sqlite:////absolute/path.db -> absolute path (parsed.path = '//absolute/path.db')
            parsed = urlparse(db_url)
            db_path = unquote(parsed.path)

            # For SQLite URLs, a single leading slash means relative path
            if db_path.startswith('/') and not db_path.startswith('//'):
                # Relative path - remove the leading slash
                db_path = db_path.lstrip('/')
            # No special handling needed for absolute paths

            db_file = Path(db_path)
            db_dir = db_file.parent

            if db_dir and str(db_dir) != '.':
                db_dir.mkdir(parents=True, exist_ok=True)
                logger.info("Database directory created/verified: path=%s", str(db_dir))
        except Exception as e:
            logger.warning("Could not create database directory: error=%s", str(e))


async def main():
    """
    Initialize database schema.

    This function:
    1. Creates database directory if needed (for SQLite)
    2. Initializes all database tables
    3. Handles errors gracefully
    4. Ensures proper cleanup of database engine
    """
    logger.info("Starting database initialization...")

    # Create database directory if needed
    create_database_directory()

    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database: error=%s", str(e), exc_info=True)
        raise
    finally:
        # Always dispose of the engine to clean up connections
        try:
            await engine.dispose()
            logger.debug("Database engine disposed")
        except Exception as disposal_error:
            # Log disposal errors but don't mask the original exception
            logger.warning("Error disposing engine: error=%s", str(disposal_error))


if __name__ == "__main__":
    asyncio.run(main())
