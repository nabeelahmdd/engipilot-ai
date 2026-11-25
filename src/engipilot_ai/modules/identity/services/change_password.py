"""Authenticated password changes with account-wide session revocation."""

from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.modules.identity.passwords import (
    MAX_PASSWORD_LENGTH,
    hash_password_async,
    validate_new_password,
    verify_password_async,
)
from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.services.authentication import (
    AuthRejectionReason,
    AuthenticationRejected,
    AuthenticationService,
)
from engipilot_ai.modules.identity.tokens import AccessClaims, utcnow


class InvalidCurrentPassword(Exception):
    """Existing password is incorrect."""


class InvalidNewPassword(ValueError):
    """New password violates the policy or repeats the existing one."""


class ChangePasswordService:
    @staticmethod
    async def change_password(
        session: AsyncSession,
        *,
        claims: AccessClaims,
        current_password: str,
        new_password: str,
    ) -> None:
        """Verify old password, rotate hash, and invalidate all sessions."""
        if not current_password or len(current_password) > MAX_PASSWORD_LENGTH:
            raise InvalidCurrentPassword()

        try:
            validate_new_password(new_password)
        except ValueError as exc:
            raise InvalidNewPassword(str(exc)) from exc

        # Do not hold account-row locks during expensive Argon2id work.
        async with session.begin():
            user = await AuthenticationService.require_authenticated_user(
                session,
                claims,
            )
            user_id = user.id
            previous_hash = user.password_hash

        if previous_hash is None or not await verify_password_async(
            current_password,
            previous_hash,
        ):
            raise InvalidCurrentPassword()

        if current_password == new_password:
            raise InvalidNewPassword("New password must be different")

        replacement_hash = await hash_password_async(new_password)

        async with session.begin():
            current = await AuthenticationService.require_authenticated_user(
                session,
                claims,
            )
            locked = await IdentityRepository.get_user_by_id_for_update(
                session,
                user_id=current.id,
            )
            if (
                locked is None
                or locked.id != user_id
                or locked.uuid != claims.user_uuid
                or not locked.is_active
                or not locked.is_email_verified
                or locked.auth_version != claims.auth_version
                or locked.password_hash != previous_hash
            ):
                raise AuthenticationRejected(
                    AuthRejectionReason.TOKEN_VERSION_MISMATCH
                )

            now = utcnow()
            locked.password_hash = replacement_hash
            locked.auth_version += 1

            await IdentityRepository.expire_active_password_reset_tokens(
                session,
                user_id=locked.id,
                now=now,
            )
            await IdentityRepository.cancel_pending_password_reset_emails(
                session,
                user_id=locked.id,
            )
            await IdentityRepository.revoke_all_user_sessions(
                session,
                user_id=locked.id,
                now=now,
            )
