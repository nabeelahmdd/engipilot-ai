"""Organization tenant model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engipilot_ai.core.db_base import AbstractModel

if TYPE_CHECKING:
    from engipilot_ai.modules.identity.models.user import User
    from engipilot_ai.modules.organizations.models.membership import (
        OrganizationMembership,
    )
    from engipilot_ai.modules.projects.models.project import Project


class Organization(AbstractModel):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(160), nullable=False)

    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)

    owner_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    owner: Mapped[User] = relationship(
        "User",
        back_populates="owned_organizations",
        foreign_keys=[owner_user_id],
    )

    memberships: Mapped[list[OrganizationMembership]] = relationship(
        "OrganizationMembership",
        back_populates="organization",
    )

    projects: Mapped[list[Project]] = relationship(
        "Project",
        back_populates="organization",
    )
