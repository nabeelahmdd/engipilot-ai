"""Idempotent browser logout with CSRF-checked session revocation."""

import hmac

from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.tokens import digest_secret, utcnow


class InvalidLogoutCSRF(Exception):
    """Supplied CSRF proof is missing or does not match the browser session."""


class LogoutService:
    @staticmethod
    async def logout(
        session: AsyncSession,
        *,
        refresh_secret: str,
        csrf_secret: str,
    ) -> None:
        """Revoke the device session for a known refresh credential.

        Unknown and previously revoked credentials are deliberately idempotent.
        """
        if not 16 <= len(csrf_secret) <= 512 or not csrf_secret.isascii():
            raise InvalidLogoutCSRF()

        if not 16 <= len(refresh_secret) <= 512 or not refresh_secret.isascii():
            return

        refresh_hash = digest_secret(refresh_secret)
        csrf_hash = digest_secret(csrf_secret)

        async with session.begin():
            credential = await IdentityRepository.get_refresh_credential_for_update(
                session,
                refresh_hash,
            )
            if credential is None:
                return

            device = await IdentityRepository.get_auth_session_for_update(
                session,
                session_id=credential.session_id,
            )
            if (
                device is None
                or device.client_type != "browser"
                or device.csrf_hash is None
            ):
                return

            if not hmac.compare_digest(device.csrf_hash, csrf_hash):
                raise InvalidLogoutCSRF()

            if device.revoked_at is None:
                device.revoked_at = utcnow()
