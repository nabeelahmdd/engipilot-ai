"""Dispatch encrypted identity emails from PostgreSQL."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from engipilot_ai.core.database import get_session_factory
from engipilot_ai.modules.identity.email_payload import (
    get_email_payload_cipher,
)
from engipilot_ai.modules.identity.email_sender import LocalSMTPEmailSender
from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.tokens import utcnow

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
    ) -> None: ...


@dataclass(frozen=True)
class ClaimedEmail:
    id: int
    recipient: str
    template: str
    payload: bytes
    attempt_count: int
    lease_until: datetime


async def dispatch_one(
    *,
    sender: EmailSender | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> bool:
    """Claim, deliver and acknowledge one due email."""

    factory = session_factory if session_factory is not None else get_session_factory()

    # Transaction 1: claim work and release DB locks.
    async with factory() as session:
        async with session.begin():
            record = await IdentityRepository.claim_next_email(
                session,
                utcnow(),
            )

            if record is None:
                return False

            assert record.locked_until is not None

            job = ClaimedEmail(
                id=record.id,
                recipient=record.recipient_email,
                template=record.template,
                payload=record.encrypted_payload,
                attempt_count=record.attempt_count,
                lease_until=record.locked_until,
            )

    success = False

    try:
        if job.template != "verify_email":
            raise ValueError("Unsupported email template")

        token = get_email_payload_cipher().decrypt_token(job.payload)

        await (sender or LocalSMTPEmailSender()).send(
            recipient=job.recipient,
            subject="Verify your CommercePilot AI email",
            body=(
                "Welcome to CommercePilot AI!\n\n"
                "Use this token to verify your email address:\n\n"
                f"{token}\n\n"
                "If you did not create an account, ignore this email."
            ),
        )

        success = True

    except Exception as exc:
        # Never log encrypted payloads or raw verification tokens.
        logger.warning(
            "Email job %s failed: %s",
            job.id,
            type(exc).__name__,
        )

    # Transaction 2: acknowledge the result.
    async with factory() as session:
        async with session.begin():
            acknowledged = await IdentityRepository.finish_email(
                session,
                email_id=job.id,
                lease_until=job.lease_until,
                attempt_count=job.attempt_count,
                success=success,
            )

            if not acknowledged:
                logger.warning(
                    "Email job %s lease is no longer current",
                    job.id,
                )

    return True


async def dispatch_pending() -> int:
    """Process currently available jobs and then exit."""
    processed = 0

    while await dispatch_one():
        processed += 1

    return processed


if __name__ == "__main__":
    count = asyncio.run(dispatch_pending())
    print(f"Processed {count} email jobs")
