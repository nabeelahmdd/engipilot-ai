"""Integration tests for email verification and concurrency."""

import asyncio
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from engipilot_ai.core.config import get_settings
from engipilot_ai.modules.identity.models.one_time_token import OneTimeToken
from engipilot_ai.modules.identity.models.user import User
from engipilot_ai.modules.identity.registration_service import (
    RegistrationResult,
    RegistrationService,
)
from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.tokens import digest_secret, utcnow
from engipilot_ai.modules.identity.verification_service import (
    EmailVerificationService,
    InvalidVerificationToken,
)


async def register_user(
    factory: async_sessionmaker[AsyncSession],
) -> RegistrationResult:
    """Create a new temporary, unverified account."""
    async with factory() as session:
        return await RegistrationService.register(
            session,
            email=f"verify-{uuid.uuid4().hex}@example.com",
            password="SecurePassword@2026",
        )


async def cleanup_user(
    factory: async_sessionmaker[AsyncSession],
    user_uuid: uuid.UUID,
) -> None:
    """Remove only the test account; related tokens cascade."""
    async with factory() as session:
        async with session.begin():
            await session.execute(delete(User).where(User.uuid == user_uuid))


async def verify_expired_token_case() -> None:
    engine = create_async_engine(
        get_settings().database_url,
        poolclass=NullPool,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    registered = None

    try:
        registered = await register_user(factory)
        token_hash = digest_secret(registered.verification_secret)

        # Force this test token into the past.
        async with factory() as session:
            async with session.begin():
                token = await session.scalar(
                    select(OneTimeToken).where(OneTimeToken.token_hash == token_hash)
                )
                assert token is not None
                token.expires_at = utcnow() - timedelta(seconds=1)

        # The verification service must reject the expired token.
        async with factory() as session:
            with pytest.raises(InvalidVerificationToken):
                await EmailVerificationService.verify_email(
                    session,
                    token=registered.verification_secret,
                )

        # Verify that no account state was accidentally changed.
        async with factory() as session:
            user = await IdentityRepository.get_user_by_uuid(
                session,
                registered.user_uuid,
            )
            token = await session.scalar(
                select(OneTimeToken).where(OneTimeToken.token_hash == token_hash)
            )

            assert user is not None
            assert user.is_email_verified is False
            assert token is not None
            assert token.consumed_at is None

    finally:
        if registered is not None:
            await cleanup_user(factory, registered.user_uuid)
        await engine.dispose()


def test_expired_verification_token() -> None:
    asyncio.run(verify_expired_token_case())


async def verify_concurrent_token_case() -> None:
    engine = create_async_engine(
        get_settings().database_url,
        poolclass=NullPool,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    registered = None

    try:
        registered = await register_user(factory)

        # Both requests will wait until they are ready to start.
        start = asyncio.Event()
        both_ready = asyncio.Event()
        ready_count = 0

        async def attempt_verification() -> uuid.UUID | None:
            nonlocal ready_count

            ready_count += 1
            if ready_count == 2:
                both_ready.set()

            await start.wait()

            # Each request gets its own DB session/connection.
            async with factory() as session:
                try:
                    return await EmailVerificationService.verify_email(
                        session,
                        token=registered.verification_secret,
                    )
                except InvalidVerificationToken:
                    return None

        first = asyncio.create_task(attempt_verification())
        second = asyncio.create_task(attempt_verification())

        try:
            await asyncio.wait_for(both_ready.wait(), timeout=5)
        finally:
            start.set()

        results = await asyncio.wait_for(
            asyncio.gather(first, second),
            timeout=15,
        )

        # Exactly one request should succeed.
        assert results.count(registered.user_uuid) == 1
        assert results.count(None) == 1

        # Persisted state must be consistent.
        async with factory() as session:
            user = await IdentityRepository.get_user_by_uuid(
                session,
                registered.user_uuid,
            )

            token = await session.scalar(
                select(OneTimeToken).where(
                    OneTimeToken.token_hash
                    == digest_secret(registered.verification_secret)
                )
            )

            assert user is not None
            assert user.is_email_verified is True
            assert token is not None
            assert token.consumed_at is not None

    finally:
        if registered is not None:
            await cleanup_user(factory, registered.user_uuid)
        await engine.dispose()


def test_concurrent_verification_single_use() -> None:
    asyncio.run(verify_concurrent_token_case())
