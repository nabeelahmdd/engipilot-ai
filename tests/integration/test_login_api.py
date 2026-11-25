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

                    # Keep this HTTP test independent of filesystem JWT keys.
                    with patch(
                        "engipilot_ai.modules.identity.services.login.issue_access_token",
                        return_value="test-access-jwt",
                    ):
                        browser = await client.post(
                            login_url,
                            json={"email": email.upper(), "password": password},
                        )
                        native = await client.post(
                            login_url,
                            json={
                                "email": email,
                                "password": password,
                                "client_type": "native",
                            },
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

                    assert native.status_code == 200, native.text
                    native_data = native.json()
                    assert native_data["user_uuid"] == str(user.uuid)
                    assert native_data["access_token"] == "test-access-jwt"
                    assert native_data["refresh_token"]
                    assert "csrf_token" not in native_data
                    assert native.headers.get("set-cookie") is None
                    assert native.headers["cache-control"] == "no-store"

                    async with factory() as session:
                        devices = (
                            await session.scalars(
                                select(AuthSession).where(
                                    AuthSession.user_id == user.id
                                )
                            )
                        ).all()
                        assert len(devices) == 2

                        browser_device = next(
                            device for device in devices
                            if device.client_type == "browser"
                        )
                        native_device = next(
                            device for device in devices
                            if device.client_type == "native"
                        )
                        assert str(browser_device.uuid) == (
                            browser_data["session_uuid"]
                        )
                        assert str(native_device.uuid) == native_data["session_uuid"]
                        assert browser_device.csrf_hash == digest_secret(
                            browser_data["csrf_token"]
                        )
                        assert native_device.csrf_hash is None

                        browser_refresh = await session.scalar(
                            select(RefreshCredential).where(
                                RefreshCredential.session_id == browser_device.id
                            )
                        )
                        native_refresh = await session.scalar(
                            select(RefreshCredential).where(
                                RefreshCredential.session_id == native_device.id
                            )
                        )
                        assert browser_refresh is not None
                        assert native_refresh is not None
                        assert browser_refresh.token_hash == digest_secret(
                            browser_cookie
                        )
                        assert native_refresh.token_hash == digest_secret(
                            native_data["refresh_token"]
                        )

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
                        assert len(sessions_after) == 2

            finally:
                app.dependency_overrides.pop(get_db_session, None)
                await outer_transaction.rollback()
    finally:
        await engine.dispose()


def test_login_api() -> None:
    asyncio.run(verify_login_api())
