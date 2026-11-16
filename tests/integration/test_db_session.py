"""Verify async database sessions and automatic transaction rollback."""

import asyncio
import uuid

from sqlalchemy import select

from engipilot_ai.core.database import get_session_factory
from engipilot_ai.core.model_registry import register_models
from engipilot_ai.modules.identity.models.user import User


class ExpectedRollback(Exception):
    """Signal an intentional test rollback."""


async def verify_rollback() -> None:
    register_models()
    user_uuid: uuid.UUID | None = None

    try:
        async with get_session_factory()() as session:
            async with session.begin():
                user = User(
                    first_name="Temporary",
                    last_name="IntegrationTest",
                )

                session.add(user)
                await session.flush()

                assert user.id is not None
                assert user.id > 0

                user_uuid = user.uuid
                assert isinstance(user_uuid, uuid.UUID)

                # Force rollback before committing this test user.
                raise ExpectedRollback

    except ExpectedRollback:
        pass

    assert user_uuid is not None

    # Use a separate session to verify nothing persisted.
    async with get_session_factory()() as session:
        statement = select(User.id).where(User.uuid == user_uuid)

        saved_id = await session.scalar(statement)

        assert saved_id is None


def test_async_session_rollback() -> None:
    asyncio.run(verify_rollback())
