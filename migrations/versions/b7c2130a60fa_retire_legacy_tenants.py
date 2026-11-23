"""Retire legacy organization and project tables (only when empty).

Revision ID: b7c2130a60fa
Revises: 088229649077

This migration intentionally refuses to discard populated legacy tables. Back up
or manually migrate historical tenant data before applying to a non-empty DB.
Downgrade recreates empty legacy tables; it does not restore deleted data.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7c2130a60fa"
down_revision: str | Sequence[str] | None = "088229649077"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _common_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    """Remove obsolete tenant tables without losing populated user data."""
    connection = op.get_bind()
    tables = (
        "project_memberships",
        "projects",
        "organization_memberships",
        "organizations",
    )

    for table in tables:
        # Static table names only; reject populated tables before any DROP.
        populated = connection.execute(
            sa.text(f'SELECT EXISTS (SELECT 1 FROM "{table}")')
        ).scalar_one()
        if populated:
            raise RuntimeError(
                f"Refusing to drop populated legacy table {table!r}. "
                "Back up or migrate legacy data explicitly before upgrading."
            )

    for table in tables:
        op.drop_table(table)


def downgrade() -> None:
    """Recreate the old schema without restoring previously removed rows."""
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=False),
        *_common_columns(),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_organizations_owner_user_id",
        "organizations",
        ["owner_user_id"],
        unique=False,
    )

    op.create_table(
        "organization_memberships",
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="member", nullable=False),
        *_common_columns(),
        sa.CheckConstraint("role IN ('admin', 'member')", name="ck_org_member_role"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_org_member_org_user",
        ),
        sa.UniqueConstraint("uuid"),
    )

    op.create_table(
        "projects",
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        *_common_columns(),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_project_org_code"),
        sa.UniqueConstraint("organization_id", "id", name="uq_project_org_id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_projects_organization_id",
        "projects",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "project_memberships",
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "role", sa.String(length=20), server_default="developer", nullable=False
        ),
        *_common_columns(),
        sa.CheckConstraint(
            "role IN ('project_admin', 'developer', 'reviewer', 'viewer')",
            name="ck_project_member_role",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            name="fk_project_member_project_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.user_id",
            ],
            name="fk_project_member_user_org",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_member_project_user",
        ),
        sa.UniqueConstraint("uuid"),
    )
