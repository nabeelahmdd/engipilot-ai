"""Password recovery email request orchestration."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.core.config import get_settings
from engipilot_ai.modules.identity.email_payload import get_email_payload_cipher
from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.services.registration import normalize_email
from engipilot_ai.modules.identity.tokens import digest_secret, random_secret, utcnow


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
