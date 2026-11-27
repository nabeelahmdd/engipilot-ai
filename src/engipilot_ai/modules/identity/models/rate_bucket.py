"""Durable per-source authentication request counters."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from engipilot_ai.core.db_base import Base


class AuthRateBucket(Base):
    __tablename__ = "identity_rate_buckets"

    bucket_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    hits: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        CheckConstraint("hits >= 0", name="ck_identity_rate_buckets_hits"),
        Index(
            "ix_identity_rate_buckets_window_started_at",
            "window_started_at",
        ),
    )
