"""Rotating refresh credentials."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from engipilot_ai.core.db_base import AbstractModel


class RefreshCredential(AbstractModel):
    __tablename__ = "refresh_credentials"

    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("auth_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
