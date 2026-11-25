"""Password recovery email request orchestration."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.core.config import get_settings
from engipilot_ai.modules.identity.email_payload import get_email_payload_cipher
from engipilot_ai.modules.identity.passwords import (
    hash_password_async,
    validate_new_password,
)
from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.services.registration import normalize_email
from engipilot_ai.modules.identity.tokens import digest_secret, random_secret, utcnow


class InvalidPasswordResetToken(ValueError):
    """Reset token is invalid, expired, or already consumed."""


class InvalidPasswordResetData(ValueError):
    """New password does not satisfy password policy."""


class PasswordRecoveryService:
    @staticmethod
    async def request_reset(
        session: AsyncSession,
        *,
        email: str,
    ) -> None:
        """Queue a single-use recovery token without revealing account state."""
        normalized_email = normalize_email(email)

        async with session.begin():
            user = await IdentityRepository.get_user_by_email_for_update(
                session,
                normalized_email,
            )
            if (
                user is None
                or not user.is_active
                or not user.is_email_verified
                or user.email is None
                or user.password_hash is None
            ):
                return

            now = utcnow()
            latest = await IdentityRepository.get_latest_password_reset_token(
                session,
                user_id=user.id,
            )
            if latest is not None and latest.created_at > now - timedelta(seconds=60):
                return

            recent = await IdentityRepository.count_recent_password_reset_tokens(
                session,
                user_id=user.id,
                since=now - timedelta(hours=1),
            )
            if recent >= 3:
                return

            secret = random_secret()
            encrypted = get_email_payload_cipher().encrypt_token(secret)

            await IdentityRepository.expire_active_password_reset_tokens(
                session,
                user_id=user.id,
                now=now,
            )
            await IdentityRepository.cancel_pending_password_reset_emails(
                session,
                user_id=user.id,
            )
            await IdentityRepository.create_one_time_token(
                session,
                user_id=user.id,
                purpose="reset_password",
                token_hash=digest_secret(secret),
                expires_at=now
                + timedelta(minutes=get_settings().password_reset_minutes),
            )
            await IdentityRepository.create_email_outbox(
                session,
                user_id=user.id,
                recipient_email=user.email,
                template="reset_password",
                encrypted_payload=encrypted,
            )

    @staticmethod
    async def reset_password(
        session: AsyncSession,
        *,
        token: str,
        new_password: str,
    ) -> None:
        """Rotate the password and revoke all existing sessions atomically."""
        if not 16 <= len(token) <= 512 or not token.isascii():
            raise InvalidPasswordResetToken()

        try:
            validate_new_password(new_password)
        except ValueError as exc:
            raise InvalidPasswordResetData(str(exc)) from exc

        token_hash = digest_secret(token)

        # Cheap preflight: do not hash passwords for arbitrary invalid tokens.
        async with session.begin():
            preview = await IdentityRepository.get_password_reset_token(
                session,
                token_hash=token_hash,
            )
            if (
                preview is None
                or preview.consumed_at is not None
                or preview.expires_at <= utcnow()
            ):
                raise InvalidPasswordResetToken()

        new_hash = await hash_password_async(new_password)

        # Revalidate under locks after the expensive hash is computed.
        async with session.begin():
            user = await IdentityRepository.get_password_reset_user_for_update(
                session,
                token_hash=token_hash,
            )
            if (
                user is None
                or not user.is_active
                or not user.is_email_verified
                or user.password_hash is None
            ):
                raise InvalidPasswordResetToken()

            record = await IdentityRepository.get_password_reset_token_for_update(
                session,
                user_id=user.id,
                token_hash=token_hash,
            )
            now = utcnow()
            if (
                record is None
                or record.consumed_at is not None
                or record.expires_at <= now
            ):
                raise InvalidPasswordResetToken()

            user.password_hash = new_hash
            user.auth_version += 1
            record.consumed_at = now

            await IdentityRepository.expire_active_password_reset_tokens(
                session,
                user_id=user.id,
                now=now,
            )
            await IdentityRepository.cancel_pending_password_reset_emails(
                session,
                user_id=user.id,
            )
            await IdentityRepository.revoke_all_user_sessions(
                session,
                user_id=user.id,
                now=now,
            )
