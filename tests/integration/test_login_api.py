"""HTTP login contract and persisted credential tests."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from unittest.mock import patch

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
from engipilot_ai.modules.identity.tokens import digest_secret


async def verify_login_api() -> None:
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

                async def override_db_session() -> AsyncIterator[AsyncSession]:
                    async with factory() as session:
                        yield session

                app.dependency_overrides[get_db_session] = override_db_session

                email = f"login-{uuid.uuid4().hex}@example.com"
                password = "SecurePassword@2026"
                login_url = "/api/v1/auth/login"

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

                    unverified = await client.post(
                        login_url,
                        json={"email": email, "password": password},
                    )
                    assert unverified.status_code == 403
                    assert unverified.json() == {
                        "detail": "Email verification required",
                    }

                    # Invalid credentials must not create a device session.
                    unknown = await client.post(
                        login_url,
                        json={
                            "email": "unknown@example.com",
                            "password": password,
                        },
                    )
                    assert unknown.status_code == 401

                    wrong = await client.post(
                        login_url,
                        json={"email": email, "password": "WrongPassword@2026"},
                    )
                    assert wrong.status_code == 401
                    assert wrong.json() == unknown.json()

                    async with factory() as session:
                        user = await session.scalar(
                            select(User).where(User.email == email)
                        )
                        assert user is not None

                        queued = await session.scalar(
                            select(EmailOutbox).where(
                                EmailOutbox.user_id == user.id,
                                EmailOutbox.template == "verify_email",
                            )
                        )
                        assert queued is not None
                        token = get_email_payload_cipher().decrypt_token(
                            queued.encrypted_payload
                        )

                        sessions_before = (
                            await session.scalars(
                                select(AuthSession).where(
                                    AuthSession.user_id == user.id
                                )
                            )
                        ).all()
                        assert not sessions_before

                    verified = await client.post(
                        "/api/v1/auth/verify-email",
                        json={"token": token},
                    )
                    assert verified.status_code == 200

                    unsupported_client = await client.post(
                        login_url,
                        json={
                            "email": email,
                            "password": password,
                            "client_type": "native",
                        },
                    )
                    assert unsupported_client.status_code == 422

                    # Keep this HTTP test independent of filesystem JWT keys.
                    with patch(
                        "engipilot_ai.modules.identity.services.login.issue_access_token",
                        return_value="test-access-jwt",
                    ):
                        browser = await client.post(
                            login_url,
                            json={"email": email.upper(), "password": password},
                        )

                    assert browser.status_code == 200, browser.text
                    browser_data = browser.json()
                    assert browser_data["user_uuid"] == str(user.uuid)
                    assert browser_data["access_token"] == "test-access-jwt"
                    assert browser_data["token_type"] == "bearer"
                    assert browser_data["expires_in"] > 0
                    assert browser_data["csrf_token"]
                    assert "refresh_token" not in browser_data
                    assert browser.headers["cache-control"] == "no-store"
                    assert browser.headers["pragma"] == "no-cache"

                    browser_cookie = browser.cookies.get("cp_refresh")
                    assert browser_cookie
                    set_cookie = browser.headers["set-cookie"].lower()
                    assert "httponly" in set_cookie
                    assert "samesite=lax" in set_cookie
                    assert "path=/api/v1/auth" in set_cookie

                    async with factory() as session:
                        devices = (
                            await session.scalars(
                                select(AuthSession).where(
                                    AuthSession.user_id == user.id
                                )
                            )
                        ).all()
                        assert len(devices) == 1

                        browser_device = next(
                            device for device in devices
                            if device.client_type == "browser"
                        )
                        assert str(browser_device.uuid) == (
                            browser_data["session_uuid"]
                        )
                        assert browser_device.csrf_hash == digest_secret(
                            browser_data["csrf_token"]
                        )

                        browser_refresh = await session.scalar(
                            select(RefreshCredential).where(
                                RefreshCredential.session_id == browser_device.id
                            )
                        )
                        assert browser_refresh is not None
                        assert browser_refresh.token_hash == digest_secret(
                            browser_cookie
                        )

                    # Browser refresh requires a cookie and CSRF proof.
                    refresh_url = "/api/v1/auth/refresh"
                    csrf = browser_data["csrf_token"]

                    without_csrf = await client.post(refresh_url)
                    assert without_csrf.status_code == 403

                    wrong_csrf = await client.post(
                        refresh_url,
                        headers={"X-CSRF-Token": "wrong-csrf-token-value-123456789"},
                    )
                    assert wrong_csrf.status_code == 403

                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                    ) as other_client:
                        missing_cookie = await other_client.post(
                            refresh_url,
                            headers={"X-CSRF-Token": csrf},
                        )
                        assert missing_cookie.status_code == 401

                        invalid_cookie = await other_client.post(
                            refresh_url,
                            headers={"X-CSRF-Token": csrf},
                            cookies={"cp_refresh": "x" * 32},
                        )
                        assert invalid_cookie.status_code == 401

                    with patch(
                        "engipilot_ai.modules.identity.services.refresh.issue_access_token",
                        return_value="rotated-access-jwt",
                    ):
                        refreshed = await client.post(
                            refresh_url,
                            headers={"X-CSRF-Token": csrf},
                        )

                    assert refreshed.status_code == 200, refreshed.text
                    refresh_data = refreshed.json()
                    assert refresh_data["user_uuid"] == browser_data["user_uuid"]
                    assert refresh_data["session_uuid"] == (
                        browser_data["session_uuid"]
                    )
                    assert refresh_data["access_token"] == "rotated-access-jwt"
                    assert refresh_data["token_type"] == "bearer"
                    assert refresh_data["expires_in"] > 0
                    assert "refresh_token" not in refresh_data
                    assert "csrf_token" not in refresh_data
                    assert refreshed.headers["cache-control"] == "no-store"
                    new_cookie = refreshed.cookies.get("cp_refresh")
                    assert new_cookie
                    assert new_cookie != browser_cookie

                    async with factory() as session:
                        credentials = (
                            await session.scalars(
                                select(RefreshCredential).where(
                                    RefreshCredential.session_id
                                    == browser_device.id
                                )
                            )
                        ).all()
                        assert len(credentials) == 2
                        original = next(
                            item for item in credentials
                            if item.token_hash == digest_secret(browser_cookie)
                        )
                        replacement = next(
                            item for item in credentials
                            if item.token_hash == digest_secret(new_cookie)
                        )
                        assert original.used_at is not None
                        assert replacement.used_at is None
                        current_device = await session.get(
                            AuthSession, browser_device.id
                        )
                        assert current_device is not None
                        assert current_device.revoked_at is None

                    # Wrong CSRF must never revoke a session, even on replay.
                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                        cookies={"cp_refresh": browser_cookie},
                    ) as replay_client:
                        tampered = await replay_client.post(
                            refresh_url,
                            headers={"X-CSRF-Token": "wrong-csrf-token-value-123456789"},
                        )
                        assert tampered.status_code == 403

                        replay = await replay_client.post(
                            refresh_url,
                            headers={"X-CSRF-Token": csrf},
                        )
                        assert replay.status_code == 401

                    async with factory() as session:
                        revoked_device = await session.get(
                            AuthSession, browser_device.id
                        )
                        assert revoked_device is not None
                        assert revoked_device.revoked_at is not None

                    rejected = await client.post(
                        refresh_url,
                        headers={"X-CSRF-Token": csrf},
                    )
                    assert rejected.status_code == 401

                    async with factory() as session:
                        async with session.begin():
                            current = await session.get(User, user.id)
                            assert current is not None
                            current.is_active = False

                    disabled = await client.post(
                        login_url,
                        json={"email": email, "password": password},
                    )
                    assert disabled.status_code == 401
                    assert disabled.json() == unknown.json()

                    async with factory() as session:
                        sessions_after = (
                            await session.scalars(
                                select(AuthSession).where(
                                    AuthSession.user_id == user.id
                                )
                            )
                        ).all()
                        assert len(sessions_after) == 1

            finally:
                app.dependency_overrides.pop(get_db_session, None)
                await outer_transaction.rollback()
    finally:
        await engine.dispose()


def test_login_api() -> None:
    asyncio.run(verify_login_api())
