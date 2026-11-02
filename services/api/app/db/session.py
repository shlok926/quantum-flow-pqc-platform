"""Quantum Flow Technologies — Database Engine & Session Management.

Provides async SQLAlchemy engine, session maker, and connection health diagnostics.
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from services.api.app.core.config import settings

logger = logging.getLogger(__name__)

_async_engine: AsyncEngine | None = None
_async_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_async_engine() -> AsyncEngine:
    """Return or lazily initialize the asynchronous SQLAlchemy engine."""
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _async_engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return or lazily initialize the async sessionmaker."""
    global _async_sessionmaker
    if _async_sessionmaker is None:
        _async_sessionmaker = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency providing an async database session for FastAPI endpoints."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database_health() -> tuple[bool, str]:
    """Verify connectivity to PostgreSQL database by executing a lightweight query.

    Returns sanitized status messages to prevent credential/path disclosure.
    """
    try:
        engine = get_async_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            if val == 1:
                return True, "connected"
            return False, "unexpected query result"
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return False, "Database connection unavailable"


async def close_async_engine() -> None:
    """Dispose of the async database engine connection pool upon application shutdown."""
    global _async_engine, _async_sessionmaker
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_sessionmaker = None
