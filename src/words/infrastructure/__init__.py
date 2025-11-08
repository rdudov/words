"""
Infrastructure layer for the Words application.

This package contains infrastructure components such as database
connections, external service clients, and other technical concerns.
"""

from src.words.infrastructure.database import (
    engine,
    AsyncSessionLocal,
    get_session,
    init_db,
    close_db,
)

__all__ = [
    "engine",
    "AsyncSessionLocal",
    "get_session",
    "init_db",
    "close_db",
]
