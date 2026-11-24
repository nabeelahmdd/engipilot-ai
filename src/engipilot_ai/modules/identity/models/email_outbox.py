"""Durable outbox for identity-related transactional emails."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from engipilot_ai.core.db_base import AbstractModel


class EmailOutbox(AbstractModel):
    __tablename__ = "identity_email_outbox"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    recipient_email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    template: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    # Store only encrypted content, never a plaintext token.
    encrypted_payload: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'pending'"),
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'sent', 'failed')",
            name="ck_identity_email_outbox_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_identity_email_outbox_attempt_count",
        ),
        Index(
            "ix_identity_email_outbox_dispatch",
            "status",
            "available_at",
        ),
    )
