"""Shared public authentication rate-limit API checks."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from engipilot_ai.core.config import get_settings
from engipilot_ai.core.database import get_db_session
from engipilot_ai.main import app
from engipilot_ai.modules.identity.models.rate_bucket import AuthRateBucket
from engipilot_ai.modules.identity.tokens import utcnow


async def verify_public_rate_limit() -> None:
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

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    resend = "/api/v1/auth/resend-verification"
                    payload = {"email": "missing@example.com"}

                    for _ in range(2):
                        accepted = await client.post(resend, json=payload)
                        assert accepted.status_code == 202

                    blocked = await client.post(resend, json=payload)
                    assert blocked.status_code == 429
                    assert blocked.json()["detail"] == (
                        "Too many requests. Try again later."
                    )
                    assert 1 <= int(blocked.headers["retry-after"]) <= 60

                    # An untrusted forwarded-IP header cannot evade the bucket.
                    spoofed = await client.post(
                        resend,
                        json=payload,
                        headers={"X-Forwarded-For": "203.0.113.5"},
                    )
                    assert spoofed.status_code == 429

                    # Different endpoints keep independent counters.
                    forgot = "/api/v1/auth/forgot-password"
                    independent = await client.post(forgot, json=payload)
                    assert independent.status_code == 202

                    async with factory() as session:
                        buckets = (await session.scalars(select(AuthRateBucket))).all()
                        assert len(buckets) == 2
                        assert all(len(b.bucket_key) == 64 for b in buckets)
                        assert all("127.0.0.1" not in b.bucket_key for b in buckets)
                        assert sorted(b.hits for b in buckets) == [1, 4]

                    # Expired windows are reset to one request.
                    async with factory() as session:
                        async with session.begin():
                            await session.execute(
                                update(AuthRateBucket).values(
                                    window_started_at=utcnow() - timedelta(seconds=120)
                                )
                            )
                    reset = await client.post(resend, json=payload)
                    assert reset.status_code == 202

                    # Invalid login attempts also incur the same per-route limit.
                    login = "/api/v1/auth/login"
                    login_payload = {
                        "email": "nonexistent@example.com",
                        "password": "InvalidPassword@2026",
                    }
                    for _ in range(2):
                        denied = await client.post(login, json=login_payload)
                        assert denied.status_code == 401
                    throttled_login = await client.post(
                        login,
                        json=login_payload,
                    )
                    assert throttled_login.status_code == 429

                    # Token verification/reset have their own independent limits.
                    for endpoint in (
                        "/api/v1/auth/verify-email",
                        "/api/v1/auth/reset-password",
                    ):
                        data = {"token": "x" * 64}
                        if endpoint.endswith("reset-password"):
                            data.update(
                                new_password="NewPassword@2026",
                                confirm_password="NewPassword@2026",
                            )
                        for _ in range(2):
                            invalid = await client.post(endpoint, json=data)
                            assert invalid.status_code == 400
                        throttled = await client.post(endpoint, json=data)
                        assert throttled.status_code == 429

                    # Registration cannot be used to bypass throttling.
                    register = "/api/v1/auth/register"
                    for i in range(3):
                        created = await client.post(
                            register,
                            json={
                                "email": f"limit-{i}-{uuid.uuid4().hex}@example.com",
                                "password": "StrongPassword@2026",
                                "confirm_password": "StrongPassword@2026",
                            },
                        )
                        assert created.status_code == (201 if i < 2 else 429)

            finally:
                app.dependency_overrides.pop(get_db_session, None)
                await outer.rollback()
    finally:
        await engine.dispose()


def test_public_auth_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "2")
    monkeypatch.setenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60")
    get_settings.cache_clear()
    asyncio.run(verify_public_rate_limit())
