"""Liveness and readiness; readiness verifies a real database connection."""

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from engipilot_ai.core.database import get_engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "engipilot-api"}


@router.get("/ready")
async def ready() -> dict[str, str]:
    try:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        # Do not leak passwords, database addresses, or internal errors to callers.
        logger.warning("Database readiness check failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ready"}
