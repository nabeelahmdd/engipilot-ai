"""End-to-end logout API and device revocation checks."""

import asyncio
import uuid
from collections.abc import AsyncIterator
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
from engipilot_ai.modules.identity.models.refresh_credential import (
    RefreshCredential,
)
from engipilot_ai.modules.identity.models.user import User
from engipilot_ai.modules.identity.services.authentication import (
    AuthenticationRejected,
    AuthenticationService,
)
from engipilot_ai.modules.identity.tokens import AccessClaims, digest_secret


async def verify_logout_api() -> None:
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
                email = f"logout-{uuid.uuid4().hex}@example.com"
                password = "SecurePassword@2026"
                logout_url = "/api/v1/auth/logout"
                refresh_url = "/api/v1/auth/refresh"

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    registration = await client.post(
                        "/api/v1/auth/register",
                        json={
                            "email": email,
                            "password": password,
                            "confirm_password": password,
                        },
                    )
                    assert registration.status_code == 201

                    async with factory() as session:
                        user = await session.scalar(
                            select(User).where(User.email == email)
                        )
                        assert user is not None
                        queued = await session.scalar(
                            select(EmailOutbox).where(
                                EmailOutbox.user_id == user.id
                            )
                        )
                        assert queued is not None
                        token = get_email_payload_cipher().decrypt_token(
                            queued.encrypted_payload
                        )

                    verified = await client.post(
                        "/api/v1/auth/verify-email",
                        json={"token": token},
                    )
                    assert verified.status_code == 200

                    with patch(
                        "engipilot_ai.modules.identity.services.login.issue_access_token",
                        return_value="initial-access-jwt",
                    ):
                        logged_in = await client.post(
                            "/api/v1/auth/login",
                            json={"email": email, "password": password},
                        )
                    assert logged_in.status_code == 200, logged_in.text
                    login_data = logged_in.json()
                    csrf = login_data["csrf_token"]
                    first_cookie = logged_in.cookies.get("cp_refresh")
                    assert first_cookie is not None

                    # A live session authenticates before logout.
                    claims = AccessClaims(
                        user_uuid=user.uuid,
                        session_uuid=uuid.UUID(login_data["session_uuid"]),
                        token_uuid=uuid.uuid4(),
                        auth_version=user.auth_version,
                    )
                    async with factory() as session:
                        authenticated = (
                            await AuthenticationService.require_authenticated_user(
                                session,
                                claims,
                            )
                        )
                        assert authenticated.uuid == user.uuid

                    # No cookie: idempotent success without a CSRF header.
                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                    ) as no_cookie_client:
                        empty = await no_cookie_client.post(logout_url)
                        assert empty.status_code == 204
                        assert empty.content == b""

                        unknown = await no_cookie_client.post(
                            logout_url,
                            headers={"X-CSRF-Token": csrf},
                            cookies={"cp_refresh": "x" * 32},
                        )
                        assert unknown.status_code == 204

                    missing_csrf = await client.post(logout_url)
                    assert missing_csrf.status_code == 403
                    bad_csrf = await client.post(
                        logout_url,
                        headers={"X-CSRF-Token": "wrong-proof-12345678901234567890"},
                    )
                    assert bad_csrf.status_code == 403
                    assert client.cookies.get("cp_refresh") == first_cookie

                    # Rotate the refresh token, then log out the rotated session.
                    with patch(
                        "engipilot_ai.modules.identity.services.refresh.issue_access_token",
                        return_value="rotated-access-jwt",
                    ):
                        rotated = await client.post(
                            refresh_url,
                            headers={"X-CSRF-Token": csrf},
                        )
                    assert rotated.status_code == 200, rotated.text
                    current_cookie = rotated.cookies.get("cp_refresh")
                    assert current_cookie is not None
                    assert current_cookie != first_cookie

                    async with factory() as session:
                        device = await session.scalar(
                            select(AuthSession).where(
                                AuthSession.uuid == claims.session_uuid
                            )
                        )
                        assert device is not None
                        device_id = device.id
                        assert device.revoked_at is None

                    logged_out = await client.post(
                        logout_url,
                        headers={"X-CSRF-Token": csrf},
                    )
                    assert logged_out.status_code == 204
                    assert logged_out.content == b""
                    assert logged_out.headers["cache-control"] == "no-store"
                    assert "max-age=0" in logged_out.headers["set-cookie"].lower()
                    assert "path=/api/v1/auth" in (
                        logged_out.headers["set-cookie"].lower()
                    )
                    assert client.cookies.get("cp_refresh") is None

                    async with factory() as session:
                        revoked = await session.get(AuthSession, device_id)
                        assert revoked is not None
                        assert revoked.revoked_at is not None
                        credentials = (
                            await session.scalars(
                                select(RefreshCredential).where(
                                    RefreshCredential.session_id == device_id
                                )
                            )
                        ).all()
                        assert len(credentials) == 2
                        assert any(
                            record.token_hash == digest_secret(current_cookie)
                            for record in credentials
                        )
                        with pytest.raises(AuthenticationRejected):
                            await AuthenticationService.require_authenticated_user(
                                session,
                                claims,
                            )

                    # The revoked device cannot rotate credentials again.
                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                        cookies={"cp_refresh": current_cookie},
                    ) as stale_client:
                        denied = await stale_client.post(
                            refresh_url,
                            headers={"X-CSRF-Token": csrf},
                        )
                        assert denied.status_code == 401

                        repeated = await stale_client.post(
                            logout_url,
                            headers={"X-CSRF-Token": csrf},
                        )
                        assert repeated.status_code == 204

                    repeated_empty = await client.post(logout_url)
                    assert repeated_empty.status_code == 204

            finally:
                app.dependency_overrides.pop(get_db_session, None)
                await outer.rollback()
    finally:
        await engine.dispose()


def test_logout_api() -> None:
    asyncio.run(verify_logout_api())
