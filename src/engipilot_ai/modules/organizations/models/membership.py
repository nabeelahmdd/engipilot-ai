"""Organization membership and roles."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engipilot_ai.core.db_base import AbstractModel

if TYPE_CHECKING:
    from engipilot_ai.modules.identity.models.user import User
    from engipilot_ai.modules.organizations.models.organization import (
        Organization,
    )
    from engipilot_ai.modules.projects.models.membership import (
        ProjectMembership,
    )


class OrganizationMembership(AbstractModel):
    __tablename__ = "organization_memberships"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_org_member_org_user",
        ),
        CheckConstraint(
            "role IN ('admin', 'member')",
            name="ck_org_member_role",
        ),
    )

    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default="member",
        server_default="member",
        nullable=False,
    )

    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="memberships",
    )

    user: Mapped[User] = relationship(
        "User",
        back_populates="organization_memberships",
    )

    project_memberships: Mapped[list[ProjectMembership]] = relationship(
        "ProjectMembership",
        back_populates="organization_membership",
        viewonly=True,
    )
