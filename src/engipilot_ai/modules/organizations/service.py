"""Business rules and transactions for organizations."""

import re

from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.modules.identity.service import IdentityService
from engipilot_ai.modules.organizations.models.organization import (
    Organization,
)
from engipilot_ai.modules.organizations.repository import (
    OrganizationRepository,
)


class InvalidOrganizationData(ValueError):
    """Invalid organization name or code."""


class OrganizationCodeAlreadyExists(ValueError):
    """Organization code is already registered."""


class OrganizationService:
    @staticmethod
    async def create_organization(
        session: AsyncSession,
        *,
        owner_user_id: int,
        name: str,
        code: str,
    ) -> Organization:
        name = name.strip()
        code = code.strip().lower()

        if not 2 <= len(name) <= 160:
            raise InvalidOrganizationData(
                "Organization name must contain 2-160 characters"
            )

        if not re.fullmatch(
            r"[a-z][a-z0-9-]{1,78}[a-z0-9]",
            code,
        ):
            raise InvalidOrganizationData(
                "Organization code must be 3-80 characters, "
                "start with a letter, and use lowercase "
                "letters, numbers or hyphens"
            )

        async with session.begin():
            await IdentityService.require_active_user(
                session,
                owner_user_id,
            )

            existing = await OrganizationRepository.get_by_code(
                session,
                code,
            )

            if existing is not None:
                raise OrganizationCodeAlreadyExists("Organization code already exists")

            organization = await OrganizationRepository.create(
                session,
                name=name,
                code=code,
                owner_user_id=owner_user_id,
            )

            await OrganizationRepository.add_admin_membership(
                session,
                organization_id=organization.id,
                user_id=owner_user_id,
            )

        return organization
