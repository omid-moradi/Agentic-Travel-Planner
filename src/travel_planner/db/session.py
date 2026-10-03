"""Async session management (ADR-05: SQLite fallback, Postgres in production).

``DATABASE_URL`` selects the backend; ``sqlite+aiosqlite://...`` works with no
daemon so the whole test suite runs anywhere. The engine is created lazily and
cached per URL.
"""

from __future__ import annotations

import functools
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from travel_planner.db.models import Base

_TEST_MEMORY_URL = "sqlite+aiosqlite://"  # in-memory, for tests


def _normalize_url(database_url: str) -> str:
    # A bare sqlite path is easy to misconfigure; accept it and do the right thing.
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return database_url


@functools.lru_cache(maxsize=4)
def get_engine(database_url: str) -> AsyncEngine:
    """Create (and cache) the async engine for a URL."""
    url = _normalize_url(database_url)
    kwargs: dict[str, object] = {"echo": False}
    if url.startswith("sqlite"):
        # SQLite needs a little help with concurrent readers in tests.
        kwargs["connect_args"] = {"timeout": 30}
    return create_async_engine(url, **kwargs)


def get_sessionmaker(database_url: str) -> async_sessionmaker[AsyncSession]:
    """Session factory bound to the engine for ``database_url``."""
    return async_sessionmaker(
        get_engine(database_url), expire_on_commit=False, class_=AsyncSession
    )


async def create_all(database_url: str) -> None:
    """Create the schema. Used by tests and demo mode.

    Production uses Alembic migrations (``alembic upgrade head``); this helper
    exists so the product runs with zero setup, per the master prompt.
    """
    engine = get_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def drop_all(database_url: str) -> None:
    """Drop the schema (tests only)."""
    engine = get_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


async def session_scope(database_url: str) -> AsyncIterator[AsyncSession]:
    """Provide a transactional session; commit on success, roll back on error."""
    maker = get_sessionmaker(database_url)
    async with maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def resolve_database_url(database_url: str | None = None) -> str:
    """Resolve the effective URL from settings when not given explicitly."""
    if database_url:
        return database_url
    from travel_planner.config.settings import get_settings

    return get_settings().database_url


__all__ = [
    "create_all",
    "drop_all",
    "get_engine",
    "get_sessionmaker",
    "resolve_database_url",
    "session_scope",
]
