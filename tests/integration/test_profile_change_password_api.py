"""Authenticated profile and change-password API integration coverage."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
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


async def verify_profile_change_password() -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
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

                async def override_db() -> AsyncIterator[AsyncSession]:
                    async with factory() as session:
                        yield session

                app.dependency_overrides[get_db_session] = override_db
                email = f"profile-{uuid.uuid4().hex}@example.com"
                old_password = "OriginalPassword@2026"
                new_password = "ReplacementPassword@2026"
                change_url = "/api/v1/auth/change-password"
                profile_url = "/api/v1/auth/me"
                login_url = "/api/v1/auth/login"

                with (
                    patch(
                        "engipilot_ai.modules.identity.tokens.signing_key",
                        return_value=private,
                    ),
                    patch(
                        "engipilot_ai.modules.identity.tokens.verification_key",
                        return_value=public,
                    ),
                ):
                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                    ) as client:
                        registration = await client.post(
                            "/api/v1/auth/register",
                            json={
                                "email": email,
                                "password": old_password,
                                "confirm_password": old_password,
                                "first_name": "Original",
                                "last_name": "User",
                            },
                        )
                        assert registration.status_code == 201

                        async with factory() as session:
                            user = await session.scalar(
                                select(User).where(User.email == email)
                            )
                            assert user is not None
                            user_id = user.id
                            version = user.auth_version
                            outbox = await session.scalar(
                                select(EmailOutbox).where(
                                    EmailOutbox.user_id == user_id
                                )
                            )
                            assert outbox is not None
                            secret = get_email_payload_cipher().decrypt_token(
                                outbox.encrypted_payload
                            )

                        verified = await client.post(
                            "/api/v1/auth/verify-email",
                            json={"token": secret},
                        )
                        assert verified.status_code == 200

                        first = await client.post(
                            login_url,
                            json={"email": email, "password": old_password},
                        )
                        second = await client.post(
                            login_url,
                            json={"email": email, "password": old_password},
                        )
                        assert first.status_code == 200, first.text
                        assert second.status_code == 200, second.text

                        bearer = {
                            "Authorization": f"Bearer {first.json()['access_token']}"
                        }
                        bearer_two = {
                            "Authorization": f"Bearer {second.json()['access_token']}"
                        }
                        old_cookie = second.cookies.get("cp_refresh")
                        csrf = second.json()["csrf_token"]
                        assert old_cookie is not None

                        for headers in (
                            {},
                            {"Authorization": "Basic test"},
                            {"Authorization": "Bearer invalid-jwt"},
                        ):
                            denied = await client.get(
                                profile_url,
                                headers=headers,
                            )
                            assert denied.status_code == 401

                        profile = await client.get(
                            profile_url,
                            headers=bearer,
                        )
                        assert profile.status_code == 200, profile.text
                        data = profile.json()
                        assert data["user_uuid"] == registration.json()["user_uuid"]
                        assert data["email"] == email
                        assert data["first_name"] == "Original"
                        assert data["last_name"] == "User"
                        assert data["is_email_verified"] is True
                        assert "password_hash" not in data
                        assert "auth_version" not in data

                        forbidden = await client.patch(
                            profile_url,
                            headers=bearer,
                            json={"email": "someone-else@example.com"},
                        )
                        assert forbidden.status_code == 422

                        empty = await client.patch(
                            profile_url,
                            headers=bearer,
                            json={},
                        )
                        assert empty.status_code == 422

                        updated = await client.patch(
                            profile_url,
                            headers=bearer,
                            json={"first_name": "  Updated  ", "last_name": None},
                        )
                        assert updated.status_code == 200, updated.text
                        assert updated.json()["first_name"] == "Updated"
                        assert updated.json()["last_name"] is None

                        reset_request = await client.post(
                            "/api/v1/auth/forgot-password",
                            json={"email": email},
                        )
                        assert reset_request.status_code == 202

                        unauthenticated = await client.post(
                            change_url,
                            json={
                                "current_password": old_password,
                                "new_password": new_password,
                                "confirm_password": new_password,
                            },
                        )
                        assert unauthenticated.status_code == 401

                        incorrect = await client.post(
                            change_url,
                            headers=bearer,
                            json={
                                "current_password": "WrongPassword@2026",
                                "new_password": new_password,
                                "confirm_password": new_password,
                            },
                        )
                        assert incorrect.status_code == 400

                        unchanged = await client.post(
                            change_url,
                            headers=bearer,
                            json={
                                "current_password": old_password,
                                "new_password": old_password,
                                "confirm_password": old_password,
                            },
                        )
                        assert unchanged.status_code == 422

                        mismatch = await client.post(
                            change_url,
                            headers=bearer,
                            json={
                                "current_password": old_password,
                                "new_password": new_password,
                                "confirm_password": "DifferentPassword@2026",
                            },
                        )
                        assert mismatch.status_code == 422

                        weak = await client.post(
                            change_url,
                            headers=bearer,
                            json={
                                "current_password": old_password,
                                "new_password": "weak",
                                "confirm_password": "weak",
                            },
                        )
                        assert weak.status_code == 422

                        changed = await client.post(
                            change_url,
                            headers=bearer,
                            json={
                                "current_password": old_password,
                                "new_password": new_password,
                                "confirm_password": new_password,
                            },
                        )
                        assert changed.status_code == 204, changed.text
                        assert changed.content == b""
                        assert "max-age=0" in changed.headers["set-cookie"].lower()
                        assert client.cookies.get("cp_refresh") is None

                        async with factory() as session:
                            stored = await session.get(User, user_id)
                            assert stored is not None
                            assert stored.auth_version == version + 1
                            assert stored.password_hash is not None
                            assert stored.password_hash.startswith("$argon2id$")
                            assert stored.first_name == "Updated"
                            assert stored.last_name is None
                            assert stored.email == email

                            sessions = (
                                await session.scalars(
                                    select(AuthSession).where(
                                        AuthSession.user_id == user_id
                                    )
                                )
                            ).all()
                            assert len(sessions) == 2
                            assert all(item.revoked_at is not None for item in sessions)

                            reset = await session.scalar(
                                select(OneTimeToken).where(
                                    OneTimeToken.user_id == user_id,
                                    OneTimeToken.purpose == "reset_password",
                                )
                            )
                            assert reset is not None
                            assert reset.expires_at <= datetime.now(UTC)

                            pending = await session.scalar(
                                select(EmailOutbox).where(
                                    EmailOutbox.user_id == user_id,
                                    EmailOutbox.template == "reset_password",
                                )
                            )
                            assert pending is not None
                            assert pending.status == "failed"

                        stale = await client.get(
                            profile_url,
                            headers=bearer_two,
                        )
                        assert stale.status_code == 401

                        async with AsyncClient(
                            transport=ASGITransport(app=app),
                            base_url="http://test",
                            cookies={"cp_refresh": old_cookie},
                        ) as prior:
                            denied = await prior.post(
                                "/api/v1/auth/refresh",
                                headers={"X-CSRF-Token": csrf},
                            )
                            assert denied.status_code == 401

                        login_old = await client.post(
                            login_url,
                            json={"email": email, "password": old_password},
                        )
                        assert login_old.status_code == 401

                        login_new = await client.post(
                            login_url,
                            json={"email": email, "password": new_password},
                        )
                        assert login_new.status_code == 200, login_new.text

            finally:
                app.dependency_overrides.pop(get_db_session, None)
                await outer.rollback()
    finally:
        await engine.dispose()


def test_profile_change_password() -> None:
    asyncio.run(verify_profile_change_password())
