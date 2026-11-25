"""Authenticated profile updates for non-sensitive account fields."""

from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.modules.identity.models.user import User
from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.services.authentication import (
    AuthenticationRejected,
    AuthenticationService,
    AuthRejectionReason,
)
from engipilot_ai.modules.identity.services.registration import normalize_name
from engipilot_ai.modules.identity.tokens import AccessClaims


class ProfileService:
    @staticmethod
    async def update_profile(
        session: AsyncSession,
        *,
        claims: AccessClaims,
        changes: dict[str, str | None],
    ) -> User:
        """Update names only, after validating the active login session."""
        async with session.begin():
            current = await AuthenticationService.require_authenticated_user(
                session,
                claims,
            )
            user = await IdentityRepository.get_user_by_id_for_update(
                session,
                user_id=current.id,
            )
            if (
                user is None
                or user.uuid != claims.user_uuid
                or not user.is_active
                or not user.is_email_verified
                or user.auth_version != claims.auth_version
            ):
                raise AuthenticationRejected(AuthRejectionReason.TOKEN_VERSION_MISMATCH)

            if "first_name" in changes:
                user.first_name = normalize_name(changes["first_name"])
            if "last_name" in changes:
                user.last_name = normalize_name(changes["last_name"])

            return user
