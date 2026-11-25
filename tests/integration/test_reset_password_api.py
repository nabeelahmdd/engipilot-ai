"""Reset-password HTTP lifecycle and account-wide session invalidation."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import timedelta
from unittest.mock import patch

import pytest
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
from engipilot_ai.modules.identity.models.auth_session import AuthSession
from engipilot_ai.modules.identity.models.email_outbox import EmailOutbox
from engipilot_ai.modules.identity.models.one_time_token import OneTimeToken
from engipilot_ai.modules.identity.models.user import User
from engipilot_ai.modules.identity.services.authentication import (
    AuthenticationRejected,
    AuthenticationService,
)
from engipilot_ai.modules.identity.tokens import AccessClaims, digest_secret, utcnow


async def verify_reset_password_api() -> None:
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

                async def db_override() -> AsyncIterator[AsyncSession]:
                    async with factory() as session:
                        yield session

                app.dependency_overrides[get_db_session] = db_override
                email = f"reset-{uuid.uuid4().hex}@example.com"
                old_password = "FirstPassword@2026"
                new_password = "ChangedPassword@2026"
                reset_url = "/api/v1/auth/reset-password"
                login_url = "/api/v1/auth/login"

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    registered = await client.post(
                        "/api/v1/auth/register",
                        json={
                            "email": email,
                            "password": old_password,
                            "confirm_password": old_password,
                        },
                    )
                    assert registered.status_code == 201

                    async with factory() as session:
                        user = await session.scalar(
                            select(User).where(User.email == email)
                        )
                        assert user is not None
                        user_id = user.id
                        initial_version = user.auth_version
                        confirmation = await session.scalar(
                            select(EmailOutbox).where(
                                EmailOutbox.user_id == user_id,
                                EmailOutbox.template == "verify_email",
                            )
                        )
                        assert confirmation is not None
                        verification_token = get_email_payload_cipher().decrypt_token(
                            confirmation.encrypted_payload
                        )

                    verified = await client.post(
                        "/api/v1/auth/verify-email",
                        json={"token": verification_token},
                    )
                    assert verified.status_code == 200

                    # Existing active sessions must all be revoked at reset.
                    with patch(
                        "engipilot_ai.modules.identity.services.login.issue_access_token",
                        return_value="mock-access",
                    ):
                        first_login = await client.post(
                            login_url,
                            json={"email": email, "password": old_password},
                        )
                        second_login = await client.post(
                            login_url,
                            json={"email": email, "password": old_password},
                        )
                    assert first_login.status_code == 200
                    assert second_login.status_code == 200
                    old_cookie = second_login.cookies.get("cp_refresh")
                    csrf = second_login.json()["csrf_token"]
                    assert old_cookie is not None
                    old_claims = AccessClaims(
                        user_uuid=user.uuid,
                        session_uuid=uuid.UUID(first_login.json()["session_uuid"]),
                        token_uuid=uuid.uuid4(),
                        auth_version=initial_version,
                    )

                    forgot = await client.post(
                        "/api/v1/auth/forgot-password",
                        json={"email": email},
                    )
                    assert forgot.status_code == 202

                    async with factory() as session:
                        first_token = await session.scalar(
                            select(OneTimeToken).where(
                                OneTimeToken.user_id == user_id,
                                OneTimeToken.purpose == "reset_password",
                            )
                        )
                        first_email = await session.scalar(
                            select(EmailOutbox).where(
                                EmailOutbox.user_id == user_id,
                                EmailOutbox.template == "reset_password",
                            )
                        )
                        assert first_token is not None
                        assert first_email is not None
                        secret = get_email_payload_cipher().decrypt_token(
                            first_email.encrypted_payload
                        )
                        assert digest_secret(secret) == first_token.token_hash

                    def payload(token: str, pwd: str = new_password) -> dict[str, str]:
                        return {
                            "token": token,
                            "new_password": pwd,
                            "confirm_password": pwd,
                        }

                    malformed = await client.post(reset_url, json=payload("short"))
                    assert malformed.status_code == 422

                    unknown = await client.post(reset_url, json=payload("x" * 64))
                    assert unknown.status_code == 400

                    mismatch = await client.post(
                        reset_url,
                        json={
                            "token": secret,
                            "new_password": new_password,
                            "confirm_password": "DifferentPassword@2026",
                        },
                    )
                    assert mismatch.status_code == 422

                    weak = await client.post(reset_url, json=payload(secret, "weak"))
                    assert weak.status_code == 422

                    async with factory() as session:
                        async with session.begin():
                            record = await session.get(OneTimeToken, first_token.id)
                            assert record is not None
                            record.expires_at = utcnow() - timedelta(seconds=1)
                            record.created_at = utcnow() - timedelta(seconds=70)

                    expired = await client.post(reset_url, json=payload(secret))
                    assert expired.status_code == 400

                    new_request = await client.post(
                        "/api/v1/auth/forgot-password",
                        json={"email": email},
                    )
                    assert new_request.status_code == 202

                    async with factory() as session:
                        fresh_email = await session.scalar(
                            select(EmailOutbox)
                            .where(
                                EmailOutbox.user_id == user_id,
                                EmailOutbox.template == "reset_password",
                            )
                            .order_by(EmailOutbox.id.desc())
                            .limit(1)
                        )
                        assert fresh_email is not None
                        assert fresh_email.id != first_email.id
                        fresh_secret = get_email_payload_cipher().decrypt_token(
                            fresh_email.encrypted_payload
                        )

                    completed = await client.post(
                        reset_url,
                        json=payload(fresh_secret),
                    )
                    assert completed.status_code == 200, completed.text
                    assert completed.json() == {
                        "message": "Password reset successfully"
                    }
                    assert completed.headers["cache-control"] == "no-store"
                    assert "max-age=0" in completed.headers["set-cookie"].lower()
                    assert client.cookies.get("cp_refresh") is None

                    replay = await client.post(
                        reset_url,
                        json=payload(fresh_secret),
                    )
                    assert replay.status_code == 400
                    assert replay.json() == expired.json()

                    async with factory() as session:
                        updated_user = await session.get(User, user_id)
                        assert updated_user is not None
                        assert updated_user.auth_version == initial_version + 1
                        assert updated_user.password_hash is not None
                        assert updated_user.password_hash.startswith("$argon2id$")

                        reset_tokens = (
                            await session.scalars(
                                select(OneTimeToken).where(
                                    OneTimeToken.user_id == user_id,
                                    OneTimeToken.purpose == "reset_password",
                                )
                            )
                        ).all()
                        assert len(reset_tokens) == 2
                        used = next(
                            record
                            for record in reset_tokens
                            if record.token_hash == digest_secret(fresh_secret)
                        )
                        assert used.consumed_at is not None

                        sessions = (
                            await session.scalars(
                                select(AuthSession).where(
                                    AuthSession.user_id == user_id
                                )
                            )
                        ).all()
                        assert len(sessions) == 2
                        assert all(s.revoked_at is not None for s in sessions)

                        queued = await session.get(EmailOutbox, fresh_email.id)
                        assert queued is not None
                        assert queued.status == "failed"

                        with pytest.raises(AuthenticationRejected):
                            await AuthenticationService.require_authenticated_user(
                                session,
                                old_claims,
                            )

                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                        cookies={"cp_refresh": old_cookie},
                    ) as old_client:
                        denied = await old_client.post(
                            "/api/v1/auth/refresh",
                            headers={"X-CSRF-Token": csrf},
                        )
                        assert denied.status_code == 401

                    wrong_login = await client.post(
                        login_url,
                        json={"email": email, "password": old_password},
                    )
                    assert wrong_login.status_code == 401

                    with patch(
                        "engipilot_ai.modules.identity.services.login.issue_access_token",
                        return_value="new-access",
                    ):
                        new_login = await client.post(
                            login_url,
                            json={"email": email, "password": new_password},
                        )
                    assert new_login.status_code == 200
                    assert new_login.json()["access_token"] == "new-access"

            finally:
                app.dependency_overrides.pop(get_db_session, None)
                await outer.rollback()
    finally:
        await engine.dispose()


def test_reset_password_api() -> None:
    asyncio.run(verify_reset_password_api())
