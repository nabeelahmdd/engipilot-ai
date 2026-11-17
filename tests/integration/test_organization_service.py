"""Integration tests for organization creation and transaction safety."""

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from engipilot_ai.core.config import get_settings
from engipilot_ai.modules.identity.models.user import User
from engipilot_ai.modules.organizations.models.membership import (
    OrganizationMembership,
)
from engipilot_ai.modules.organizations.repository import (
    OrganizationRepository,
)
from engipilot_ai.modules.organizations.service import (
    InvalidOrganizationData,
    OrganizationCodeAlreadyExists,
    OrganizationService,
)


async def verify_organization_service() -> None:

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

                # --------------------------------------------------
                # 1. Create a temporary active user.
                # --------------------------------------------------
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

                # --------------------------------------------------
                # 2. Validate organization name independently
                #    of the Pydantic API schema.
                # --------------------------------------------------
                async with factory() as session:
                    with pytest.raises(InvalidOrganizationData):
                        await OrganizationService.create_organization(
                            session,
                            owner_user_id=user_id,
                            name="X",
                            code="valid-company",
                        )

                # --------------------------------------------------
                # 3. Create organization and admin membership.
                # --------------------------------------------------
                async with factory() as session:
                    organization = await OrganizationService.create_organization(
                        session,
                        owner_user_id=user_id,
                        name="  Engineering Team  ",
                        code=code.upper(),
                    )

                    organization_id = organization.id
                    organization_uuid = organization.uuid

                # --------------------------------------------------
                # 4. Verify successful creation using a new session.
                # --------------------------------------------------
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

                # --------------------------------------------------
                # 5. Normal duplicate-code validation.
                # --------------------------------------------------
                async with factory() as session:
                    with pytest.raises(OrganizationCodeAlreadyExists):
                        await OrganizationService.create_organization(
                            session,
                            owner_user_id=user_id,
                            name="Another Organization",
                            code=code,
                        )

                # --------------------------------------------------
                # 6. Simulate stale lookup / race condition.
                #
                # Force get_by_code() to return None even though
                # the organization already exists in PostgreSQL.
                # --------------------------------------------------
                with patch.object(
                    OrganizationRepository,
                    "get_by_code",
                    new=AsyncMock(return_value=None),
                ):
                    async with factory() as session:
                        with pytest.raises(OrganizationCodeAlreadyExists) as error:
                            await OrganizationService.create_organization(
                                session,
                                owner_user_id=user_id,
                                name="Concurrent Organization",
                                code=code,
                            )

                        # Confirms the service translated an
                        # actual database IntegrityError.
                        assert isinstance(
                            error.value.__cause__,
                            IntegrityError,
                        )

                # --------------------------------------------------
                # 7. Simulate membership creation failure.
                #
                # Organization INSERT succeeds, but adding the
                # admin membership raises an exception.
                # --------------------------------------------------
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

                # --------------------------------------------------
                # 8. Verify the incomplete organization was
                #    rolled back and does not exist.
                # --------------------------------------------------
                async with factory() as session:
                    missing = await OrganizationRepository.get_by_code(
                        session,
                        rollback_code,
                    )

                    assert missing is None

            finally:
                # Roll back all temporary test data.
                await outer_transaction.rollback()

    finally:
        await engine.dispose()


def test_organization_creation_transaction() -> None:
    asyncio.run(verify_organization_service())
