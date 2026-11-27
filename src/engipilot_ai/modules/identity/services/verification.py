"""Single-use email verification business logic."""

import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.core.config import get_settings
from engipilot_ai.modules.identity.email_payload import get_email_payload_cipher
from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.services.registration import normalize_email
from engipilot_ai.modules.identity.tokens import digest_secret, random_secret, utcnow


class InvalidVerificationToken(ValueError):
    """Verification token is invalid, expired, or already used."""


class EmailVerificationService:
    @staticmethod
    async def verify_email(
        session: AsyncSession,
        *,
        token: str,
    ) -> uuid.UUID:
        """Verify email and consume the token in one DB transaction."""

        if (
            not isinstance(token, str)
            or not 16 <= len(token) <= 512
            or not token.isascii()
        ):
            raise InvalidVerificationToken("Invalid or expired verification token")

        token_hash = digest_secret(token)

        async with session.begin():
            user = await IdentityRepository.get_verification_user_for_update(
                session,
                token_hash,
            )

            if user is None or not user.is_active:
                raise InvalidVerificationToken("Invalid or expired verification token")

            record = await IdentityRepository.get_verification_token_for_update(
                session,
                token_hash=token_hash,
                user_id=user.id,
            )

            now = utcnow()

            if (
                record is None
                or record.consumed_at is not None
                or record.expires_at <= now
                or user.is_email_verified
            ):
                raise InvalidVerificationToken("Invalid or expired verification token")

            user.is_email_verified = True
            record.consumed_at = now

            return user.uuid

    @staticmethod
    async def resend_verification(
        session: AsyncSession,
        *,
        email: str,
    ) -> None:
        """Issue another verification email when allowed."""

        normalized_email = normalize_email(email)
        now = utcnow()

        # Prepare token and encrypted payload before the transaction.
        secret = random_secret()
        token_hash = digest_secret(secret)
        encrypted_payload = get_email_payload_cipher().encrypt_token(secret)

        expires_at = now + timedelta(hours=get_settings().email_verification_hours)

        async with session.begin():
            # Serializes concurrent resend requests for this account.
            user = await IdentityRepository.get_user_by_email_for_update(
                session,
                normalized_email,
            )

            # Do not reveal whether the account exists or is verified.
            if (
                user is None
                or not user.is_active
                or user.is_email_verified
                or user.email is None
            ):
                return

            latest = await IdentityRepository.get_latest_email_verification_token(
                session,
                user_id=user.id,
            )

            # Limit to one new token per 60 seconds.
            if latest is not None and latest.created_at > now - timedelta(seconds=60):
                return

            # Count registration token plus resend tokens.
            recent_count = await IdentityRepository.count_recent_verification_tokens(
                session,
                user_id=user.id,
                since=now - timedelta(hours=1),
            )

            if recent_count >= 5:
                return

            # Old verification links become invalid.
            await IdentityRepository.expire_active_email_verification_tokens(
                session,
                user_id=user.id,
                now=now,
            )

            # Don't dispatch old pending verification emails.
            await IdentityRepository.cancel_pending_verification_emails(
                session,
                user_id=user.id,
            )

            await IdentityRepository.create_one_time_token(
                session,
                user_id=user.id,
                purpose="verify_email",
                token_hash=token_hash,
                expires_at=expires_at,
            )

            await IdentityRepository.create_email_outbox(
                session,
                user_id=user.id,
                recipient_email=user.email,
                template="verify_email",
                encrypted_payload=encrypted_payload,
            )
