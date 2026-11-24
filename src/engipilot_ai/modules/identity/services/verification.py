"""Single-use email verification business logic."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.tokens import digest_secret, utcnow


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
