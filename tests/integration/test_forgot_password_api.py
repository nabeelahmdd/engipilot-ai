"""Forgot-password API and encrypted outbox integration checks."""

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
from engipilot_ai.modules.identity.email_payload import get_email_payload_cipher
from engipilot_ai.modules.identity.models.email_outbox import EmailOutbox
from engipilot_ai.modules.identity.models.one_time_token import OneTimeToken
from engipilot_ai.modules.identity.models.user import User
from engipilot_ai.modules.identity.services.email_dispatcher import dispatch_one
from engipilot_ai.modules.identity.tokens import digest_secret, utcnow


class FakeEmailSender:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, str]] = []

    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
    ) -> None:
        self.messages.append((recipient, subject, body))


async def verify_forgot_password_api() -> None:
    engine = create_async_engine(
        get_settings().database_url,
        poolclass=NullPool,
    )

    try:
        async with engine.connect() as connection:
            outer = await connection.begin()
            try:
                factory = async_sessionmaker(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                )

                async def override_db_session() -> AsyncIterator[AsyncSession]:
                    async with factory() as session:
                        yield session

                app.dependency_overrides[get_db_session] = override_db_session

                email = f"recover-{uuid.uuid4().hex}@example.com"
                password = "SecurePassword@2026"
                endpoint = "/api/v1/auth/forgot-password"
                sender = FakeEmailSender()

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    invalid = await client.post(
                        endpoint,
                        json={"email": "not-an-email"},
                    )
                    assert invalid.status_code == 422

                    unknown = await client.post(
                        endpoint,
                        json={"email": f"missing-{uuid.uuid4().hex}@example.com"},
                    )
                    assert unknown.status_code == 202
                    assert "token" not in unknown.text.lower()

                    registered = await client.post(
                        "/api/v1/auth/register",
                        json={
                            "email": email,
                            "password": password,
                            "confirm_password": password,
                        },
                    )
                    assert registered.status_code == 201

                    unverified = await client.post(
                        endpoint,
                        json={"email": email},
                    )
                    assert unverified.status_code == 202
                    assert unverified.json() == unknown.json()

                    async with factory() as session:
                        user = await session.scalar(
                            select(User).where(User.email == email)
                        )
                        assert user is not None
                        user_id = user.id
                        verification_email = await session.scalar(
                            select(EmailOutbox).where(
                                EmailOutbox.user_id == user_id,
                                EmailOutbox.template == "verify_email",
                            )
                        )
                        assert verification_email is not None
                        verification_token = (
                            get_email_payload_cipher().decrypt_token(
                                verification_email.encrypted_payload
                            )
                        )
                        early_resets = (
                            await session.scalars(
                                select(OneTimeToken).where(
                                    OneTimeToken.user_id == user_id,
                                    OneTimeToken.purpose == "reset_password",
                                )
                            )
                        ).all()
                        assert not early_resets

                    delivered_verification = await dispatch_one(
                        sender=sender,
                        session_factory=factory,
                    )
                    assert delivered_verification is True
                    assert len(sender.messages) == 1

                    verified = await client.post(
                        "/api/v1/auth/verify-email",
                        json={"token": verification_token},
                    )
                    assert verified.status_code == 200

                    first = await client.post(
                        endpoint,
                        json={"email": email.upper()},
                    )
                    assert first.status_code == 202
                    assert first.json() == unknown.json()

                    cooldown = await client.post(
                        endpoint,
                        json={"email": email},
                    )
                    assert cooldown.status_code == 202

                    async with factory() as session:
                        tokens = (
                            await session.scalars(
                                select(OneTimeToken).where(
                                    OneTimeToken.user_id == user_id,
                                    OneTimeToken.purpose == "reset_password",
                                )
                            )
                        ).all()
                        reset_emails = (
                            await session.scalars(
                                select(EmailOutbox).where(
                                    EmailOutbox.user_id == user_id,
                                    EmailOutbox.template == "reset_password",
                                )
                            )
                        ).all()
                        assert len(tokens) == 1
                        assert len(reset_emails) == 1
                        first_token = tokens[0]
                        first_email = reset_emails[0]
                        assert first_email.status == "pending"
                        assert first_token.consumed_at is None
                        first_secret = get_email_payload_cipher().decrypt_token(
                            first_email.encrypted_payload
                        )
                        assert digest_secret(first_secret) == first_token.token_hash
                        assert first_secret not in first.text

                    # Advance the stored issuance time past the cooldown.
                    async with factory() as session:
                        async with session.begin():
                            token = await session.get(OneTimeToken, first_token.id)
                            assert token is not None
                            token.created_at = utcnow() - timedelta(seconds=70)

                    resent = await client.post(
                        endpoint,
                        json={"email": email},
                    )
                    assert resent.status_code == 202

                    async with factory() as session:
                        previous = await session.get(OneTimeToken, first_token.id)
                        obsolete_email = await session.get(
                            EmailOutbox, first_email.id
                        )
                        assert previous is not None
                        assert previous.expires_at <= utcnow()
                        assert obsolete_email is not None
                        assert obsolete_email.status == "failed"

                    async with factory() as session:
                        async with session.begin():
                            newest = await session.scalar(
                                select(OneTimeToken)
                                .where(
                                    OneTimeToken.user_id == user_id,
                                    OneTimeToken.purpose == "reset_password",
                                )
                                .order_by(
                                    OneTimeToken.created_at.desc(),
                                    OneTimeToken.id.desc(),
                                )
                                .limit(1)
                            )
                            assert newest is not None
                            newest.created_at = utcnow() - timedelta(seconds=70)

                    third = await client.post(endpoint, json={"email": email})
                    assert third.status_code == 202

                    async with factory() as session:
                        async with session.begin():
                            newest = await session.scalar(
                                select(OneTimeToken)
                                .where(
                                    OneTimeToken.user_id == user_id,
                                    OneTimeToken.purpose == "reset_password",
                                )
                                .order_by(
                                    OneTimeToken.created_at.desc(),
                                    OneTimeToken.id.desc(),
                                )
                                .limit(1)
                            )
                            assert newest is not None
                            newest.created_at = utcnow() - timedelta(seconds=70)

                    capped = await client.post(endpoint, json={"email": email})
                    assert capped.status_code == 202

                    async with factory() as session:
                        tokens = (
                            await session.scalars(
                                select(OneTimeToken).where(
                                    OneTimeToken.user_id == user_id,
                                    OneTimeToken.purpose == "reset_password",
                                )
                            )
                        ).all()
                        assert len(tokens) == 3

                        last_email = await session.scalar(
                            select(EmailOutbox)
                            .where(
                                EmailOutbox.user_id == user_id,
                                EmailOutbox.template == "reset_password",
                            )
                            .order_by(EmailOutbox.id.desc())
                            .limit(1)
                        )
                        assert last_email is not None
                        assert last_email.status == "pending"
                        last_secret = get_email_payload_cipher().decrypt_token(
                            last_email.encrypted_payload
                        )

                    delivered_reset = await dispatch_one(
                        sender=sender,
                        session_factory=factory,
                    )
                    assert delivered_reset is True
                    assert len(sender.messages) == 2
                    recipient, subject, body = sender.messages[-1]
                    assert recipient == email
                    assert "Reset" in subject
                    assert last_secret in body

                    async with factory() as session:
                        sent_email = await session.get(EmailOutbox, last_email.id)
                        assert sent_email is not None
                        assert sent_email.status == "sent"


                    async with factory() as session:
                        async with session.begin():
                            current = await session.get(User, user_id)
                            assert current is not None
                            current.is_active = False

                    disabled = await client.post(endpoint, json={"email": email})
                    assert disabled.status_code == 202
                    assert disabled.json() == unknown.json()

            finally:
                app.dependency_overrides.pop(get_db_session, None)
                await outer.rollback()
    finally:
        await engine.dispose()


def test_forgot_password_api() -> None:
    asyncio.run(verify_forgot_password_api())
