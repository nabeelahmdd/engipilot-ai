"""PostgreSQL-backed fixed-window abuse controls for public auth APIs."""

import hashlib
import math
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.core.config import get_settings
from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.tokens import utcnow


class AuthRateLimitExceeded(Exception):
    """Request rate exceeded for this source and endpoint."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("Too many requests")


class AuthRateLimitService:
    @staticmethod
    async def check(
        session: AsyncSession,
        *,
        endpoint: str,
        source_ip: str,
    ) -> None:
        """Charge a request even if its downstream endpoint rejects it.

        Counter writes are committed in their own short transaction.
        """
        settings = get_settings()
        window = settings.auth_rate_limit_window_seconds
        maximum = settings.auth_rate_limit_max_requests
        now = utcnow()
        cutoff = now - timedelta(seconds=window)

        # Avoid storing raw IP addresses in the counter table.
        fingerprint = hashlib.sha256(
            f"{endpoint}\0{source_ip}".encode()
        ).hexdigest()

        async with session.begin():
            hits, started = await IdentityRepository.increment_auth_rate_bucket(
                session,
                bucket_key=fingerprint,
                now=now,
                cutoff=cutoff,
            )

        if hits > maximum:
            remaining = math.ceil(
                (started + timedelta(seconds=window) - now).total_seconds()
            )
            raise AuthRateLimitExceeded(retry_after=max(1, remaining))
