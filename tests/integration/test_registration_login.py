"""Integration tests for registration and login."""

import asyncio
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from engipilot_ai.core.config import get_settings
from engipilot_ai.modules.identity.models.auth_session import AuthSession
from engipilot_ai.modules.identity.models.one_time_token import OneTimeToken
from engipilot_ai.modules.identity.models.refresh_credential import (
    RefreshCredential,
)
from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.services.login import (
    AccountDisabled,
    EmailNotVerified,
    InvalidCredentials,
    LoginService,
)
from engipilot_ai.modules.identity.services.registration import (
    RegistrationService,
)
from engipilot_ai.modules.identity.services.verification import (
    EmailVerificationService,
    InvalidVerificationToken,
)
from engipilot_ai.modules.identity.tokens import digest_secret


async def verify_registration_and_login() -> None:
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

                email = f"auth-{uuid.uuid4().hex}@example.com"
                password = "MySecurePassword@2026"

                # 1. Register an unverified user.
                async with factory() as session:
                    registered = await RegistrationService.register(
                        session,
                        email=email.upper(),
                        password=password,
                        first_name="Test",
                        last_name="User",
                    )

                # 2. Verify registration and one-time token storage.
                async with factory() as session:
                    user = await IdentityRepository.get_user_by_uuid(
                        session,
                        registered.user_uuid,
                    )

                    assert user is not None
                    assert user.email == email
                    assert not user.is_email_verified
                    assert user.password_hash is not None
                    assert user.password_hash != password

                    verification = await session.scalar(
                        select(OneTimeToken).where(
                            OneTimeToken.user_id == user.id,
                            OneTimeToken.purpose == "verify_email",
                        )
                    )

                    assert verification is not None
                    assert verification.token_hash == digest_secret(
                        registered.verification_secret
                    )

                # 3. Unverified user must not log in.
                async with factory() as session:
                    with pytest.raises(EmailNotVerified):
                        await LoginService.login(
                            session,
                            email=email,
                            password=password,
                            client_type="browser",
                        )

                # 4. Mark email verified for this test.
                # The actual verification service comes next.
                async with factory() as session:
                    async with session.begin():
                        user = await IdentityRepository.get_user_by_uuid(
                            session,
                            registered.user_uuid,
                        )
                        assert user is not None

                # 4. Verify email using the real verification service.
                async with factory() as session:
                    verified_uuid = await EmailVerificationService.verify_email(
                        session,
                        token=registered.verification_secret,
                    )

                assert verified_uuid == registered.user_uuid

                # 4a. The token must be single-use.
                async with factory() as session:
                    with pytest.raises(InvalidVerificationToken):
                        await EmailVerificationService.verify_email(
                            session,
                            token=registered.verification_secret,
                        )

                # 4b. Invalid token must also be rejected.
                async with factory() as session:
                    with pytest.raises(InvalidVerificationToken):
                        await EmailVerificationService.verify_email(
                            session,
                            token="invalid-verification-token",
                        )

                # 4c. Verification and consumption were persisted.
                async with factory() as session:
                    user = await IdentityRepository.get_user_by_uuid(
                        session,
                        registered.user_uuid,
                    )
                    assert user is not None
                    assert user.is_email_verified is True

                    verification = await session.scalar(
                        select(OneTimeToken).where(
                            OneTimeToken.user_id == user.id,
                            OneTimeToken.purpose == "verify_email",
                        )
                    )
                    assert verification is not None
                    assert verification.consumed_at is not None

                # 5. Invalid credentials must fail.
                async with factory() as session:
                    with pytest.raises(InvalidCredentials):
                        await LoginService.login(
                            session,
                            email=email,
                            password="WrongPassword@2026",
                            client_type="browser",
                        )

                # 6. Correct credentials create a device session.
                with patch(
                    "engipilot_ai.modules.identity.services.login.issue_access_token",
                    return_value="test-access-jwt",
                ):
                    async with factory() as session:
                        logged_in = await LoginService.login(
                            session,
                            email=email,
                            password=password,
                            client_type="browser",
                        )

                assert logged_in.access_token == "test-access-jwt"
                assert logged_in.user_uuid == registered.user_uuid
                assert logged_in.csrf_token is not None

                # 7. Confirm session and refresh credential persisted.
                async with factory() as session:
                    device = await session.scalar(
                        select(AuthSession).where(
                            AuthSession.uuid == logged_in.session_uuid
                        )
                    )

                    assert device is not None
                    assert device.revoked_at is None
                    assert device.client_type == "browser"

                    credential = await session.scalar(
                        select(RefreshCredential).where(
                            RefreshCredential.session_id == device.id
                        )
                    )

                    assert credential is not None
                    assert credential.token_hash == digest_secret(
                        logged_in.refresh_token
                    )

                # 8. A disabled account must not log in.
                async with factory() as session:
                    async with session.begin():
                        user = await IdentityRepository.get_user_by_uuid(
                            session,
                            registered.user_uuid,
                        )
                        assert user is not None
                        user.is_active = False
                        user.auth_version += 1

                async with factory() as session:
                    with pytest.raises(AccountDisabled):
                        await LoginService.login(
                            session,
                            email=email,
                            password=password,
                            client_type="browser",
                        )

            finally:
                await outer_transaction.rollback()

    finally:
        await engine.dispose()


def test_registration_login_lifecycle() -> None:
    asyncio.run(verify_registration_and_login())
