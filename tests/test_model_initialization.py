"""Verify the complete EngiPilot ORM model graph."""

from sqlalchemy import inspect

import engipilot_ai.models  # noqa: F401
from engipilot_ai.core.db_base import Base
from engipilot_ai.modules.identity.models.user import User


def test_all_models_are_registered() -> None:
    expected_tables = {
        "users",
        "auth_sessions",
        "refresh_credentials",
        "identity_one_time_tokens",
        "organizations",
        "organization_memberships",
        "projects",
        "project_memberships",
    }

    assert expected_tables <= set(Base.metadata.tables)


def test_user_organization_relationship_resolves() -> None:
    Base.registry.configure()

    mapper = inspect(User)

    assert "owned_organizations" in mapper.relationships
    assert "organization_memberships" in mapper.relationships
