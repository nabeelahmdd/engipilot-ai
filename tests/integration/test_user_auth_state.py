"""Integration test for user authentication state."""

import asyncio
import uuid

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from engipilot_ai.core.config import get_settings
from engipilot_ai.core.model_registry import register_models
from engipilot_ai.modules.identity.models.user import User


class RollbackTest(Exception):
    """Intentionally roll back test data."""


async def verify_user_auth_state() -> None:
    register_models()

    engine = create_async_engine(
        get_settings().database_url,
        poolclass=NullPool,
    )
    factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    email = f"auth-{uuid.uuid4().hex}@example.test"

    try:
        with pytest.raises(RollbackTest):
            async with factory() as session:
                async with session.begin():
                    # Create a temporary user.
                    user = User(
                        email=email,
                        first_name="Auth",
                        last_name="Test",
                    )

                    session.add(user)
                    await session.flush()

                    assert user.auth_version == 1
                    assert user.password_hash is None
                    assert user.is_active is True

                    # Simulate the database update used
                    # during account deactivation.
                    await session.execute(
                        update(User)
                        .where(User.id == user.id)
                        .values(
                            is_active=False,
                            auth_version=User.auth_version + 1,
                        )
                    )

                    await session.refresh(user)

                    assert user.is_active is False
                    assert user.auth_version == 2

                    raise RollbackTest()

        # A fresh session confirms test data was rolled back.
        async with factory() as session:
            saved = await session.scalar(select(User).where(User.email == email))
            assert saved is None

    finally:
        await engine.dispose()


def test_user_auth_version_and_rollback() -> None:
    asyncio.run(verify_user_auth_state())
