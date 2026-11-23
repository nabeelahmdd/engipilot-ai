"""Async database engine, session factory, and FastAPI dependency."""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from engipilot_ai.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Return the application's shared async database engine."""
    return create_async_engine(
        get_settings().database_url,
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the factory used to create independent sessions."""
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Provide one managed database session to a request."""
    async with get_session_factory()() as session:
        yield session
