"""Integration tests for organization creation."""

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

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
from engipilot_ai.modules.organizations.service import (
    OrganizationCodeAlreadyExists,
    OrganizationService,
)


async def verify_organization_service() -> None:
    register_models()

    engine = create_async_engine(
        get_settings().database_url,
        poolclass=NullPool,
    )

    try:
        async with engine.connect() as connection:
            outer_transaction = await connection.begin()

            try:
                factory = async_sessionmaker(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                )

                # 1. Prepare a temporary owner.
                async with factory() as session:
                    async with session.begin():
                        user = User(
                            first_name="Test",
                            last_name="Owner",
                            email=f"test-{uuid.uuid4()}@example.com",
                        )
                        session.add(user)
                        await session.flush()
                        user_id = user.id

                code = f"engineering-{uuid.uuid4().hex[:8]}"

                # 2. Create organization and admin membership.
                async with factory() as session:
                    organization = await OrganizationService.create_organization(
                        session,
                        owner_user_id=user_id,
                        name="  Engineering Team  ",
                        code=code.upper(),
                    )
                    organization_id = organization.id
                    organization_uuid = organization.uuid

                # 3. Verify using a new session.
                async with factory() as session:
                    saved = await OrganizationRepository.get_by_uuid(
                        session,
                        organization_uuid,
                    )

                    assert saved is not None
                    assert saved.name == "Engineering Team"
                    assert saved.code == code
                    assert saved.owner_user_id == user_id

                    membership = await session.scalar(
                        select(OrganizationMembership).where(
                            OrganizationMembership.organization_id == organization_id,
                            OrganizationMembership.user_id == user_id,
                        )
                    )

                    assert membership is not None
                    assert membership.role == "admin"

                # 4. Duplicate organization code must fail.
                async with factory() as session:
                    with pytest.raises(OrganizationCodeAlreadyExists):
                        await OrganizationService.create_organization(
                            session,
                            owner_user_id=user_id,
                            name="Another Organization",
                            code=code,
                        )

                # 5. Simulate failure after organization insertion.
                rollback_code = f"rollback-{uuid.uuid4().hex[:8]}"

                with patch.object(
                    OrganizationRepository,
                    "add_admin_membership",
                    new=AsyncMock(side_effect=RuntimeError("Simulated failure")),
                ):
                    async with factory() as session:
                        with pytest.raises(
                            RuntimeError,
                            match="Simulated failure",
                        ):
                            await OrganizationService.create_organization(
                                session,
                                owner_user_id=user_id,
                                name="Rollback Organization",
                                code=rollback_code,
                            )

                # 6. Verify the incomplete organization was rolled back.
                async with factory() as session:
                    missing = await OrganizationRepository.get_by_code(
                        session,
                        rollback_code,
                    )
                    assert missing is None

            finally:
                # The test must not leave permanent records.
                await outer_transaction.rollback()

    finally:
        await engine.dispose()


def test_organization_creation_transaction() -> None:
    asyncio.run(verify_organization_service())
