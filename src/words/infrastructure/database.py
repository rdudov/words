"""
Database infrastructure module for the Words application.

This module provides SQLAlchemy async engine, session management,
and database lifecycle functions (initialization and cleanup).
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
from src.words.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    poolclass=NullPool if "sqlite" in settings.database_url else None,
    pool_pre_ping=True
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@asynccontextmanager
async def get_session():
    """Provide database session with automatic cleanup"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def init_db():
    """Initialize database (create tables)"""
    from src.words.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")

async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")
