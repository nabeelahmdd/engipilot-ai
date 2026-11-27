"""Create shared authentication rate buckets.

Revision ID: c79e25a7fd46
Revises: 9dcd20b05e96
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c79e25a7fd46"
down_revision: str | Sequence[str] | None = "9dcd20b05e96"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "identity_rate_buckets",
        sa.Column("bucket_key", sa.String(length=64), nullable=False),
        sa.Column(
            "hits",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("hits >= 0", name="ck_identity_rate_buckets_hits"),
        sa.PrimaryKeyConstraint("bucket_key"),
    )
    op.create_index(
        "ix_identity_rate_buckets_window_started_at",
        "identity_rate_buckets",
        ["window_started_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_rate_buckets_window_started_at",
        table_name="identity_rate_buckets",
    )
    op.drop_table("identity_rate_buckets")
