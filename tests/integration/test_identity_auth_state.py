"""Integration tests for database-backed authentication state."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from engipilot_ai.core.config import get_settings
from engipilot_ai.modules.identity.models.user import User
from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.services import (
    AuthenticationRejected,
    AuthenticationService,
)
from engipilot_ai.modules.identity.tokens import AccessClaims


async def verify_authentication_state() -> None:

    engine = create_async_engine(
        get_settings().database_url,
        poolclass=NullPool,
    )

    try:
        async with engine.connect() as connection:
            outer_transaction = await connection.begin()

            try:
                factory = async_sessionmaker(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                )

                async with factory() as session:
                    async with session.begin():
                        user = User(
                            email=f"auth-{uuid.uuid4().hex}@example.com",
                            first_name="Authentication",
                            last_name="Test",
                            is_email_verified=True,
                        )

                        session.add(user)
                        await session.flush()

                        auth_session = await IdentityRepository.create_auth_session(
                            session,
                            user_id=user.id,
                            client_type="browser",
                            expires_at=(datetime.now(UTC) + timedelta(days=1)),
                        )

                        user_uuid = user.uuid
                        session_uuid = auth_session.uuid

                claims = AccessClaims(
                    user_uuid=user_uuid,
                    session_uuid=session_uuid,
                    token_uuid=uuid.uuid4(),
                    auth_version=1,
                )

                # Active user and active session are accepted.
                async with factory() as session:
                    authenticated_user = (
                        await AuthenticationService.require_authenticated_user(
                            session,
                            claims,
                        )
                    )

                    assert authenticated_user.uuid == user_uuid

                # Simulate account deactivation.
                async with factory() as session:
                    async with session.begin():
                        user = await IdentityRepository.get_user_by_uuid(
                            session,
                            user_uuid,
                        )

                        assert user is not None
                        user.is_active = False
                        user.auth_version += 1

                # Old claims must no longer authenticate.
                async with factory() as session:
                    with pytest.raises(AuthenticationRejected):
                        await AuthenticationService.require_authenticated_user(
                            session,
                            claims,
                        )

            finally:
                await outer_transaction.rollback()

    finally:
        await engine.dispose()


def test_authenticated_user_rejected_after_deactivation() -> None:
    asyncio.run(verify_authentication_state())
