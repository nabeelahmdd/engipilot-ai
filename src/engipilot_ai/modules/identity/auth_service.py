"""Authentication-state business rules."""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.modules.identity.models.user import User
from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.tokens import AccessClaims


class AuthRejectionReason(StrEnum):
    """Internal authentication failure reasons."""

    CONTEXT_NOT_FOUND = "context_not_found"
    ACCOUNT_DISABLED = "account_disabled"
    TOKEN_VERSION_MISMATCH = "token_version_mismatch"
    SESSION_REVOKED = "session_revoked"
    SESSION_EXPIRED = "session_expired"
    EMAIL_NOT_VERIFIED = "email_not_verified"


class AuthenticationRejected(Exception):
    """Authentication failed for a known internal reason."""

    def __init__(self, reason: AuthRejectionReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


class AuthenticationService:
    @staticmethod
    async def require_authenticated_user(
        session: AsyncSession,
        claims: AccessClaims,
    ) -> User:
        """Validate current user and device-session state."""
        context = await IdentityRepository.get_auth_context(
            session,
            user_uuid=claims.user_uuid,
            session_uuid=claims.session_uuid,
        )

        if context is None:
            raise AuthenticationRejected(AuthRejectionReason.CONTEXT_NOT_FOUND)

        user, auth_session = context

        if not user.is_active:
            raise AuthenticationRejected(AuthRejectionReason.ACCOUNT_DISABLED)

        if not user.is_email_verified:
            raise AuthenticationRejected(AuthRejectionReason.EMAIL_NOT_VERIFIED)

        if user.auth_version != claims.auth_version:
            raise AuthenticationRejected(AuthRejectionReason.TOKEN_VERSION_MISMATCH)

        if auth_session.revoked_at is not None:
            raise AuthenticationRejected(AuthRejectionReason.SESSION_REVOKED)

        if auth_session.expires_at <= datetime.now(UTC):
            raise AuthenticationRejected(AuthRejectionReason.SESSION_EXPIRED)

        return user
