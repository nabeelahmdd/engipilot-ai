"""Alembic migration environment for EngiPilot AI."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from engipilot_ai.core.config import get_settings
from engipilot_ai.core.db_base import Base

# Import all models to register tables in Base.metadata.
from engipilot_ai.modules.identity.models import user  # noqa: F401
from engipilot_ai.modules.organizations.models import (  # noqa: F401
    membership as organization_membership,
)
from engipilot_ai.modules.projects.models import (  # noqa: F401
    membership as project_membership,
)

config = context.config

# Configure Alembic logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy metadata for autogenerate.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate migration SQL without connecting to DB."""

    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations using an active connection."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Connect to PostgreSQL using asyncpg."""

    settings = get_settings()

    configuration = dict(config.get_section(config.config_ini_section) or {})
    configuration["sqlalchemy.url"] = settings.database_url

    engine = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
