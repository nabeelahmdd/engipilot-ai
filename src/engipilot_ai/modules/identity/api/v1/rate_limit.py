"""Public authentication rate-limit dependency."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.core.database import get_db_session
from engipilot_ai.modules.identity.services.rate_limit import (
    AuthRateLimitExceeded,
    AuthRateLimitService,
)


async def limit_public_auth(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    # Do not use untrusted X-Forwarded-For request headers here.
    source = request.client.host if request.client is not None else "unknown"
    try:
        await AuthRateLimitService.check(
            session,
            endpoint=request.url.path,
            source_ip=source,
        )
    except AuthRateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again later.",
            headers={
                "Retry-After": str(exc.retry_after),
                "Cache-Control": "no-store",
            },
        ) from exc
