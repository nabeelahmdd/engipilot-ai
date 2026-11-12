"""Project membership with tenant-safe constraints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engipilot_ai.core.db_base import AbstractModel

if TYPE_CHECKING:
    from engipilot_ai.modules.organizations.models.membership import (
        OrganizationMembership,
    )
    from engipilot_ai.modules.projects.models.project import Project


class ProjectMembership(AbstractModel):
    __tablename__ = "project_memberships"

    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            name="fk_project_member_project_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "user_id"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.user_id",
            ],
            name="fk_project_member_user_org",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_member_project_user",
        ),
        CheckConstraint(
            "role IN ('project_admin', 'developer', 'reviewer', 'viewer')",
            name="ck_project_member_role",
        ),
    )

    organization_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    role: Mapped[str] = mapped_column(
        String(20),
        default="developer",
        server_default="developer",
        nullable=False,
    )

    project: Mapped[Project] = relationship(
        "Project",
        back_populates="memberships",
        viewonly=True,
    )

    organization_membership: Mapped[OrganizationMembership] = relationship(
        "OrganizationMembership",
        back_populates="project_memberships",
        viewonly=True,
    )
