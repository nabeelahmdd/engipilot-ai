"""Per-device authentication sessions."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from engipilot_ai.core.db_base import AbstractModel


class AuthSession(AbstractModel):
    __tablename__ = "auth_sessions"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    csrf_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    client_type: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
    )
