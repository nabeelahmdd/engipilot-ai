"""Unit tests for authentication rejection reasons."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.services.authentication import (
    AuthenticationRejected,
    AuthenticationService,
    AuthRejectionReason,
)
from engipilot_ai.modules.identity.tokens import AccessClaims


@pytest.mark.parametrize(
    ("active", "db_version", "revoked", "expired", "expected"),
    [
        (
            False,
            1,
            False,
            False,
            AuthRejectionReason.ACCOUNT_DISABLED,
        ),
        (
            True,
            2,
            False,
            False,
            AuthRejectionReason.TOKEN_VERSION_MISMATCH,
        ),
        (
            True,
            1,
            True,
            False,
            AuthRejectionReason.SESSION_REVOKED,
        ),
        (
            True,
            1,
            False,
            True,
            AuthRejectionReason.SESSION_EXPIRED,
        ),
    ],
)
def test_authentication_rejection_reason(
    active: bool,
    db_version: int,
    revoked: bool,
    expired: bool,
    expected: AuthRejectionReason,
) -> None:
    async def scenario() -> None:
        now = datetime.now(UTC)

        user = SimpleNamespace(
            is_active=active, auth_version=db_version, is_email_verified=True
        )

        device_session = SimpleNamespace(
            expires_at=(
                now - timedelta(minutes=1) if expired else now + timedelta(hours=1)
            ),
            revoked_at=now if revoked else None,
        )

        claims = AccessClaims(
            user_uuid=uuid.uuid4(),
            session_uuid=uuid.uuid4(),
            token_uuid=uuid.uuid4(),
            auth_version=1,
        )

        with patch.object(
            IdentityRepository,
            "get_auth_context",
            new=AsyncMock(return_value=(user, device_session)),
        ):
            with pytest.raises(AuthenticationRejected) as error:
                await AuthenticationService.require_authenticated_user(
                    session=None,  # type: ignore[arg-type]
                    claims=claims,
                )

            assert error.value.reason == expected

    asyncio.run(scenario())


def test_unverified_email_rejects_existing_session() -> None:
    async def scenario() -> None:
        now = datetime.now(UTC)

        user = SimpleNamespace(
            is_active=True,
            is_email_verified=False,
            auth_version=1,
        )

        auth_session = SimpleNamespace(
            revoked_at=None,
            expires_at=now + timedelta(hours=1),
        )

        claims = AccessClaims(
            user_uuid=uuid.uuid4(),
            session_uuid=uuid.uuid4(),
            token_uuid=uuid.uuid4(),
            auth_version=1,
        )

        with patch.object(
            IdentityRepository,
            "get_auth_context",
            new=AsyncMock(return_value=(user, auth_session)),
        ):
            with pytest.raises(AuthenticationRejected) as error:
                await AuthenticationService.require_authenticated_user(
                    session=None,  # type: ignore[arg-type]
                    claims=claims,
                )

            assert error.value.reason == AuthRejectionReason.EMAIL_NOT_VERIFIED

    asyncio.run(scenario())
