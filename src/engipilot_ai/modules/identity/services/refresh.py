"""Single-use browser refresh rotation and replay protection."""

import hmac
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.core.config import get_settings
from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.tokens import (
    digest_secret,
    issue_access_token,
    random_secret,
    utcnow,
)


class InvalidRefreshToken(Exception):
    """Refresh token is expired, invalid, revoked, or replayed."""


class InvalidRefreshCSRF(Exception):
    """CSRF proof does not match the browser session."""


@dataclass(frozen=True, slots=True)
class RefreshResult:
    user_uuid: uuid.UUID
    session_uuid: uuid.UUID
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_cookie_max_age: int


class RefreshService:
    @staticmethod
    async def rotate(
        session: AsyncSession,
        *,
        refresh_secret: str,
        csrf_secret: str,
    ) -> RefreshResult:
        """Consume a refresh credential, issue its replacement atomically."""
        if not 16 <= len(refresh_secret) <= 512 or not refresh_secret.isascii():
            raise InvalidRefreshToken()
        if not 16 <= len(csrf_secret) <= 512 or not csrf_secret.isascii():
            raise InvalidRefreshCSRF()

        refresh_hash = digest_secret(refresh_secret)
        csrf_hash = digest_secret(csrf_secret)
        next_secret = random_secret()

        invalid_csrf = False
        rotated: RefreshResult | None = None

        async with session.begin():
            credential = await IdentityRepository.get_refresh_credential_for_update(
                session,
                refresh_hash,
            )
            if credential is not None:
                device = await IdentityRepository.get_auth_session_for_update(
                    session,
                    session_id=credential.session_id,
                )
                if (
                    device is not None
                    and device.client_type == "browser"
                    and device.csrf_hash is not None
                ):
                    if not hmac.compare_digest(device.csrf_hash, csrf_hash):
                        invalid_csrf = True
                    elif credential.used_at is not None:
                        # Commit revocation even though the HTTP request fails.
                        device.revoked_at = utcnow()
                    else:
                        now = utcnow()
                        if (
                            device.revoked_at is None
                            and device.expires_at > now
                            and credential.expires_at > now
                        ):
                            user = await IdentityRepository.get_user_by_id_for_update(
                                session,
                                user_id=device.user_id,
                            )
                            if (
                                user is not None
                                and user.is_active
                                and user.is_email_verified
                            ):
                                credential.used_at = now
                                await IdentityRepository.create_refresh_credential(
                                    session,
                                    session_id=device.id,
                                    token_hash=digest_secret(next_secret),
                                    expires_at=device.expires_at,
                                )
                                access_token = issue_access_token(
                                    user_uuid=user.uuid,
                                    session_uuid=device.uuid,
                                    auth_version=user.auth_version,
                                )
                                settings = get_settings()
                                rotated = RefreshResult(
                                    user_uuid=user.uuid,
                                    session_uuid=device.uuid,
                                    access_token=access_token,
                                    refresh_token=next_secret,
                                    expires_in=settings.jwt_access_minutes * 60,
                                    refresh_cookie_max_age=max(
                                        1,
                                        int((device.expires_at - now).total_seconds()),
                                    ),
                                )

        if invalid_csrf:
            raise InvalidRefreshCSRF()
        if rotated is None:
            raise InvalidRefreshToken()
        return rotated
