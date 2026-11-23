"""Email/password login and initial credential issuance."""

import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.core.config import get_settings
from engipilot_ai.modules.identity.passwords import (
    MAX_PASSWORD_LENGTH,
    verify_password_async,
    verify_unknown_password_async,
)
from engipilot_ai.modules.identity.registration_service import (
    normalize_email,
)
from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.tokens import (
    digest_secret,
    issue_access_token,
    random_secret,
    utcnow,
)


class InvalidCredentials(Exception):
    """Email/password authentication failed."""


class AccountDisabled(Exception):
    """Correct credentials, but account is disabled."""


class EmailNotVerified(Exception):
    """Correct credentials, but email is not verified."""


@dataclass(frozen=True, slots=True)
class LoginResult:
    """Internal credential result, not yet an HTTP response."""

    user_uuid: uuid.UUID
    session_uuid: uuid.UUID
    access_token: str
    refresh_token: str
    csrf_token: str | None
    expires_in: int


class LoginService:
    @staticmethod
    async def login(
        session: AsyncSession,
        *,
        email: str,
        password: str,
        client_type: Literal["browser", "native"],
    ) -> LoginResult:
        """Authenticate and create a per-device login session."""

        if not password or len(password) > MAX_PASSWORD_LENGTH:
            raise InvalidCredentials()

        if client_type not in ("browser", "native"):
            raise ValueError("Unsupported client type")

        # Do not disclose email syntax or account existence
        # through this public authentication operation.
        try:
            normalized_email = normalize_email(email)
        except ValueError as exc:
            raise InvalidCredentials() from exc

        # First transaction: read password hash without
        # holding an exclusive row lock.
        async with session.begin():
            user = await IdentityRepository.get_user_by_email(
                session,
                normalized_email,
            )
            stored_hash = user.password_hash if user is not None else None

        if stored_hash is None:
            await verify_unknown_password_async(password)
            raise InvalidCredentials()

        valid = await verify_password_async(
            password,
            stored_hash,
        )

        if not valid:
            raise InvalidCredentials()

        now = utcnow()
        settings = get_settings()
        session_expiry = now + timedelta(days=settings.refresh_session_days)

        refresh_secret = random_secret()
        csrf_secret = random_secret() if client_type == "browser" else None

        # Second transaction: lock and reread current account
        # before issuing any credentials.
        async with session.begin():
            current_user = await IdentityRepository.get_user_by_email_for_update(
                session,
                normalized_email,
            )

            if current_user is None or current_user.password_hash != stored_hash:
                # Password or identity changed during verification.
                raise InvalidCredentials()

            if not current_user.is_active:
                raise AccountDisabled()

            if not current_user.is_email_verified:
                raise EmailNotVerified()

            auth_session = await IdentityRepository.create_auth_session(
                session,
                user_id=current_user.id,
                client_type=client_type,
                expires_at=session_expiry,
                csrf_hash=(
                    digest_secret(csrf_secret) if csrf_secret is not None else None
                ),
            )

            await IdentityRepository.create_refresh_credential(
                session,
                session_id=auth_session.id,
                token_hash=digest_secret(refresh_secret),
                expires_at=session_expiry,
            )

            access_token = issue_access_token(
                user_uuid=current_user.uuid,
                session_uuid=auth_session.uuid,
                auth_version=current_user.auth_version,
            )

            result = LoginResult(
                user_uuid=current_user.uuid,
                session_uuid=auth_session.uuid,
                access_token=access_token,
                refresh_token=refresh_secret,
                csrf_token=csrf_secret,
                expires_in=settings.jwt_access_minutes * 60,
            )

        return result
