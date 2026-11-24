import asyncio
import uuid
from collections.abc import AsyncIterator

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
from engipilot_ai.modules.identity.services.email_dispatcher import (
    dispatch_one,
)
from engipilot_ai.modules.identity.tokens import digest_secret


async def verify_registration_api() -> None:
    """Test real HTTP registration against isolated PostgreSQL data."""

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

                async def override_db_session() -> AsyncIterator[AsyncSession]:
                    async with factory() as session:
                        yield session

                app.dependency_overrides[get_db_session] = override_db_session

                email = f"customer-{uuid.uuid4().hex}@example.com"
                password = "SecurePassword@2026"

                payload = {
                    "email": email,
                    "password": password,
                    "confirm_password": password,
                    "first_name": "Test",
                    "last_name": "Customer",
                }

                transport = ASGITransport(app=app)

                async with AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    # 1. Successful registration.
                    response = await client.post(
                        "/api/v1/auth/register",
                        json=payload,
                    )

                    assert response.status_code == 201, response.text

                    data = response.json()
                    assert data["email_verification_required"] is True
                    assert "user_uuid" in data
                    assert "password" not in data
                    assert "verification_secret" not in data

                    # 2. Duplicate email must fail.
                    duplicate = await client.post(
                        "/api/v1/auth/register",
                        json=payload,
                    )

                    assert duplicate.status_code == 409

                    # 3. Weak password must fail.
                    weak = await client.post(
                        "/api/v1/auth/register",
                        json={
                            **payload,
                            "email": f"weak-{uuid.uuid4().hex}@example.com",
                            "password": "weak",
                            "confirm_password": "weak",
                        },
                    )

                    assert weak.status_code == 422

                # 4. Verify actual database persistence.
                async with factory() as session:
                    user = await session.scalar(select(User).where(User.email == email))

                    assert user is not None
                    assert str(user.uuid) == data["user_uuid"]
                    assert user.is_email_verified is False

                    assert user.password_hash is not None
                    assert user.password_hash != password
                    assert user.password_hash.startswith("$argon2id$")

                    token = await session.scalar(
                        select(OneTimeToken).where(
                            OneTimeToken.user_id == user.id,
                            OneTimeToken.purpose == "verify_email",
                        )
                    )

                    assert token is not None
                    assert len(token.token_hash) == 64
                    assert token.consumed_at is None

                    # 5. Registration also queues the email atomically.
                    outbox = await session.scalar(
                        select(EmailOutbox).where(
                            EmailOutbox.user_id == user.id,
                            EmailOutbox.template == "verify_email",
                        )
                    )

                    assert outbox is not None
                    assert outbox.recipient_email == email
                    assert outbox.status == "pending"
                    assert outbox.attempt_count == 0
                    assert outbox.sent_at is None

                    # The raw token must not be stored as plaintext.
                    raw_token = get_email_payload_cipher().decrypt_token(
                        outbox.encrypted_payload
                    )

                    assert raw_token.encode() not in outbox.encrypted_payload

                    # The encrypted email token matches the token
                    # that will later be validated by verify-email.
                    assert digest_secret(raw_token) == token.token_hash

                    # Registration must never reveal the token.
                    assert raw_token not in response.text

                fake_sender = FakeEmailSender()

                processed = await dispatch_one(
                    sender=fake_sender,
                    session_factory=factory,
                )

                assert processed is True
                assert len(fake_sender.messages) == 1

                recipient, subject, body = fake_sender.messages[0]

                assert recipient == email
                assert "Verify" in subject
                assert raw_token in body

                async with factory() as session:
                    sent_email = await session.get(
                        EmailOutbox,
                        outbox.id,
                    )

                    assert sent_email is not None
                    assert sent_email.status == "sent"
                    assert sent_email.sent_at is not None
                    assert sent_email.attempt_count == 1
                    assert sent_email.locked_until is None

            finally:
                app.dependency_overrides.pop(get_db_session, None)
                await transaction.rollback()

    finally:
        await engine.dispose()


def test_registration_api_database_flow() -> None:
    asyncio.run(verify_registration_api())


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
