"""Async SQLAlchemy engine and request-scoped session helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def create_database_engine(settings: Settings) -> AsyncEngine:
    """Create the single bounded async database engine for this process."""
    db_url = settings.database_url
    connect_args: dict[str, Any] = {}

    if settings.app_env == "test" and "postgresql" in db_url:
        db_url = "sqlite+aiosqlite:///:memory:"

    if "postgresql" in db_url:
        try:
            import asyncpg  # noqa: F401

            connect_args = {"server_settings": {"statement_timeout": "5000"}}
        except ImportError:
            try:
                import aiosqlite  # noqa: F401

                db_url = "sqlite+aiosqlite:///./data/dev.db"
                connect_args = {}
            except ImportError:
                # If neither asyncpg nor aiosqlite is installed, fallback to sqlite in-memory
                db_url = "sqlite+aiosqlite:///:memory:"
                connect_args = {}

    if "sqlite" in db_url:
        return create_async_engine(db_url)

    return create_async_engine(
        db_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        pool_timeout=10,
        connect_args=connect_args,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create sessions that do not expire objects during response serialization."""

    return async_sessionmaker(engine, expire_on_commit=False)


async def session_from_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session and close it after the request."""

    async with session_factory() as session:
        yield session
