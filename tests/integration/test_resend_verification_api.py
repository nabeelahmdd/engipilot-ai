"""Resend verification endpoint integration test."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from engipilot_ai.core.config import get_settings
from engipilot_ai.core.database import get_db_session
from engipilot_ai.main import app
from engipilot_ai.modules.identity.email_payload import (
    get_email_payload_cipher,
)
from engipilot_ai.modules.identity.models.email_outbox import EmailOutbox
from engipilot_ai.modules.identity.models.one_time_token import OneTimeToken
from engipilot_ai.modules.identity.models.user import User
from engipilot_ai.modules.identity.services.verification import (
    EmailVerificationService,
)
from engipilot_ai.modules.identity.tokens import digest_secret, utcnow


async def verify_resend_endpoint() -> None:
    engine = create_async_engine(
        get_settings().database_url,
        poolclass=NullPool,
    )

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()

            try:
                factory = async_sessionmaker(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                )

                async def override_session() -> AsyncIterator[AsyncSession]:
                    async with factory() as session:
                        yield session

                app.dependency_overrides[get_db_session] = override_session

                email = f"resend-{uuid.uuid4().hex}@example.com"
                endpoint = "/api/v1/auth/resend-verification"

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    # 1. Register an unverified account.
                    registered = await client.post(
                        "/api/v1/auth/register",
                        json={
                            "email": email,
                            "password": "SecurePassword@2026",
                            "confirm_password": "SecurePassword@2026",
                        },
                    )
                    assert registered.status_code == 201

                    # 2. Unknown email gets the same generic response.
                    unknown = await client.post(
                        endpoint,
                        json={"email": "unknown@example.com"},
                    )
                    assert unknown.status_code == 202

                    # 3. Invalid email format is rejected.
                    invalid = await client.post(
                        endpoint,
                        json={"email": "not-an-email"},
                    )
                    assert invalid.status_code == 422

                    # 4. Immediate resend is suppressed by cooldown.
                    cooldown = await client.post(
                        endpoint,
                        json={"email": email},
                    )
                    assert cooldown.status_code == 202
                    assert cooldown.json() == unknown.json()

                    async with factory() as session:
                        async with session.begin():
                            user = await session.scalar(
                                select(User).where(User.email == email)
                            )
                            assert user is not None
                            user_id = user.id

                            first_token = await session.scalar(
                                select(OneTimeToken).where(
                                    OneTimeToken.user_id == user_id
                                )
                            )
                            assert first_token is not None
                            first_hash = first_token.token_hash

                            # Simulate passage of 60 seconds.
                            first_token.created_at = utcnow() - timedelta(minutes=2)

                    # 5. Resend succeeds after cooldown.
                    resent = await client.post(
                        endpoint,
                        json={"email": email},
                    )
                    assert resent.status_code == 202

                    async with factory() as session:
                        tokens = (
                            await session.scalars(
                                select(OneTimeToken)
                                .where(OneTimeToken.user_id == user_id)
                                .order_by(OneTimeToken.id)
                            )
                        ).all()

                        emails = (
                            await session.scalars(
                                select(EmailOutbox)
                                .where(EmailOutbox.user_id == user_id)
                                .order_by(EmailOutbox.id)
                            )
                        ).all()

                        assert len(tokens) == 2
                        assert len(emails) == 2
                        assert tokens[0].token_hash == first_hash
                        assert tokens[0].expires_at <= utcnow()
                        assert tokens[1].consumed_at is None

                        assert emails[0].status == "failed"
                        assert emails[1].status == "pending"

                        new_secret = get_email_payload_cipher().decrypt_token(
                            emails[1].encrypted_payload
                        )
                        assert digest_secret(new_secret) == tokens[1].token_hash

                    # 6. Another immediate resend must not issue a token.
                    repeated = await client.post(
                        endpoint,
                        json={"email": email},
                    )
                    assert repeated.status_code == 202

                    # 7. Reach the five-token hourly limit.
                    # Already issued: 1 registration + 1 resend.
                    for _ in range(3):
                        async with factory() as session:
                            async with session.begin():
                                latest = await session.scalar(
                                    select(OneTimeToken)
                                    .where(OneTimeToken.user_id == user_id)
                                    .order_by(
                                        OneTimeToken.created_at.desc(),
                                        OneTimeToken.id.desc(),
                                    )
                                    .limit(1)
                                )
                                assert latest is not None
                                latest.created_at = utcnow() - timedelta(seconds=70)

                        response = await client.post(
                            endpoint,
                            json={"email": email},
                        )
                        assert response.status_code == 202

                    # Move the latest timestamp back again so
                    # the cooldown cannot hide the hourly-limit check.
                    async with factory() as session:
                        async with session.begin():
                            latest = await session.scalar(
                                select(OneTimeToken)
                                .where(OneTimeToken.user_id == user_id)
                                .order_by(
                                    OneTimeToken.created_at.desc(),
                                    OneTimeToken.id.desc(),
                                )
                                .limit(1)
                            )
                            assert latest is not None
                            latest.created_at = utcnow() - timedelta(seconds=70)

                    capped = await client.post(
                        endpoint,
                        json={"email": email},
                    )
                    assert capped.status_code == 202

                    async with factory() as session:
                        tokens = (
                            await session.scalars(
                                select(OneTimeToken)
                                .where(OneTimeToken.user_id == user_id)
                                .order_by(OneTimeToken.id)
                            )
                        ).all()
                        assert len(tokens) == 5

                        newest_email = await session.scalar(
                            select(EmailOutbox)
                            .where(EmailOutbox.user_id == user_id)
                            .order_by(EmailOutbox.id.desc())
                            .limit(1)
                        )
                        assert newest_email is not None

                        latest_secret = get_email_payload_cipher().decrypt_token(
                            newest_email.encrypted_payload
                        )

                    # 8. Verify account using the last valid token.
                    async with factory() as session:
                        verified_uuid = await EmailVerificationService.verify_email(
                            session,
                            token=latest_secret,
                        )
                        assert verified_uuid == uuid.UUID(
                            registered.json()["user_uuid"]
                        )

                    # Verified accounts cannot queue more emails.
                    already_verified = await client.post(
                        endpoint,
                        json={"email": email},
                    )
                    assert already_verified.status_code == 202
                    assert already_verified.json() == unknown.json()

                    async with factory() as session:
                        final_tokens = (
                            await session.scalars(
                                select(OneTimeToken).where(
                                    OneTimeToken.user_id == user_id
                                )
                            )
                        ).all()
                        assert len(final_tokens) == 5

            finally:
                app.dependency_overrides.pop(get_db_session, None)
                await transaction.rollback()

    finally:
        await engine.dispose()


def test_resend_verification_api() -> None:
    asyncio.run(verify_resend_endpoint())
