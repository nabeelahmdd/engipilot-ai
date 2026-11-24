"""SMTP delivery adapter for local development."""

import asyncio
import smtplib
from email.message import EmailMessage

from engipilot_ai.core.config import get_settings


def _send_smtp_message(
    message: EmailMessage,
    *,
    host: str,
    port: int,
) -> None:
    """Perform blocking SMTP I/O with a bounded timeout."""
    with smtplib.SMTP(host=host, port=port, timeout=10) as smtp:
        smtp.send_message(message)


class LocalSMTPEmailSender:
    """Send development emails to a local SMTP catcher."""

    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
    ) -> None:
        settings = get_settings()

        if settings.app_env not in ("local", "test"):
            raise RuntimeError("Local SMTP sender is disabled outside development")

        message = EmailMessage()
        message["From"] = settings.smtp_from_address
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        await asyncio.to_thread(
            _send_smtp_message,
            message,
            host=settings.smtp_host,
            port=settings.smtp_port,
        )
