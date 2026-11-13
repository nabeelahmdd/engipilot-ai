"""Database operations owned by the Organizations module."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.modules.organizations.models.membership import (
    OrganizationMembership,
)
from engipilot_ai.modules.organizations.models.organization import (
    Organization,
)


class OrganizationRepository:
    @staticmethod
    async def get_by_code(
        session: AsyncSession,
        code: str,
    ) -> Organization | None:
        statement = select(Organization).where(Organization.code == code)
        return await session.scalar(statement)

    @staticmethod
    async def get_by_uuid(
        session: AsyncSession,
        organization_uuid: uuid.UUID,
    ) -> Organization | None:
        statement = select(Organization).where(Organization.uuid == organization_uuid)
        return await session.scalar(statement)

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        name: str,
        code: str,
        owner_user_id: int,
    ) -> Organization:
        organization = Organization(
            name=name,
            code=code,
            owner_user_id=owner_user_id,
        )

        session.add(organization)
        await session.flush()

        return organization

    @staticmethod
    async def add_admin_membership(
        session: AsyncSession,
        *,
        organization_id: int,
        user_id: int,
    ) -> OrganizationMembership:
        membership = OrganizationMembership(
            organization_id=organization_id,
            user_id=user_id,
            role="admin",
        )

        session.add(membership)
        await session.flush()

        return membership
