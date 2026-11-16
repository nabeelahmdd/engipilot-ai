"""Global EngiPilot user record."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, false, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engipilot_ai.core.db_base import AbstractModel

if TYPE_CHECKING:
    from engipilot_ai.modules.organizations.models.membership import (
        OrganizationMembership,
    )
    from engipilot_ai.modules.organizations.models.organization import (
        Organization,
    )


class User(AbstractModel):
    __tablename__ = "users"

    mobile: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)

    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)

    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )

    is_mobile_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )

    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )

    owned_organizations: Mapped[list[Organization]] = relationship(
        "Organization",
        back_populates="owner",
        foreign_keys="Organization.owner_user_id",
    )

    organization_memberships: Mapped[list[OrganizationMembership]] = relationship(
        "OrganizationMembership",
        back_populates="user",
    )
