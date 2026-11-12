"""Async SQLAlchemy engine factory; no database tables exist in Day 1."""

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from engipilot_ai.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)
