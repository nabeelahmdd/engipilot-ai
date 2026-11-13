"""Integration tests for the OrganizationRepository."""

import asyncio
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from engipilot_ai.core.config import get_settings
from engipilot_ai.core.model_registry import register_models
from engipilot_ai.modules.identity.models.user import User
from engipilot_ai.modules.organizations.models.membership import (
    OrganizationMembership,
)
from engipilot_ai.modules.organizations.repository import (
    OrganizationRepository,
)


class ForceRollback(Exception):
    """Used to roll back our test transaction."""


async def verify_repository() -> None:
    register_models()

    # Isolated test engine avoids connection reuse across asyncio.run loops.
    engine = create_async_engine(
        get_settings().database_url,
        poolclass=NullPool,
    )
    factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    code = f"repository-{uuid.uuid4().hex[:10]}"

    try:
        async with factory() as session:
            with pytest.raises(ForceRollback):
                async with session.begin():
                    # Step 1: Initially no organization exists.
                    existing = await OrganizationRepository.get_by_code(session, code)
                    assert existing is None

                    # Step 2: Create a temporary owner.
                    owner = User(
                        email=f"repo-{uuid.uuid4().hex}@example.test",
                        first_name="Repository",
                        last_name="Test",
                    )
                    session.add(owner)
                    await session.flush()

                    assert owner.id is not None

                    # Step 3: Create organization.
                    organization = await OrganizationRepository.create(
                        session,
                        name="Repository Test Organization",
                        code=code,
                        owner_user_id=owner.id,
                    )

                    assert organization.id is not None
                    assert isinstance(organization.uuid, uuid.UUID)

                    # Step 4: Read by code and UUID.
                    by_code = await OrganizationRepository.get_by_code(session, code)

                    by_uuid = await OrganizationRepository.get_by_uuid(
                        session, organization.uuid
                    )

                    assert by_code is not None
                    assert by_code.id == organization.id

                    assert by_uuid is not None
                    assert by_uuid.id == organization.id

                    # Step 5: Create admin membership.
                    membership = await OrganizationRepository.add_admin_membership(
                        session,
                        organization_id=organization.id,
                        user_id=owner.id,
                    )
                    assert membership.id is not None
                    assert membership.role == "admin"

                    saved_membership = await session.scalar(
                        select(OrganizationMembership).where(
                            OrganizationMembership.organization_id == organization.id,
                            OrganizationMembership.user_id == owner.id,
                        )
                    )
                    assert saved_membership is not None

                    # Step 6: Roll back all changes.
                    raise ForceRollback()

        # Step 7: Check with a fresh session.
        async with factory() as session:
            missing = await OrganizationRepository.get_by_code(session, code)
            assert missing is None

    finally:
        await engine.dispose()


def test_repository_create_read_and_rollback() -> None:
    asyncio.run(verify_repository())
