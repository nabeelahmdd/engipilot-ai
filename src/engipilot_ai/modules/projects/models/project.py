"""Project model scoped to an organization."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engipilot_ai.core.db_base import AbstractModel

if TYPE_CHECKING:
    from engipilot_ai.modules.organizations.models.organization import (
        Organization,
    )
    from engipilot_ai.modules.projects.models.membership import (
        ProjectMembership,
    )


class Project(AbstractModel):
    __tablename__ = "projects"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "code",
            name="uq_project_org_code",
        ),
        UniqueConstraint(
            "organization_id",
            "id",
            name="uq_project_org_id",
        ),
    )

    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)

    code: Mapped[str] = mapped_column(String(80), nullable=False)

    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="projects",
    )

    memberships: Mapped[list[ProjectMembership]] = relationship(
        "ProjectMembership",
        back_populates="project",
        viewonly=True,
    )
