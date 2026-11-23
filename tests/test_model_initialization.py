"""Verify the current CommercePilot identity model registry."""

from sqlalchemy import inspect

import engipilot_ai.models  # noqa: F401
from engipilot_ai.core.db_base import Base
from engipilot_ai.modules.identity.models.user import User


def test_identity_models_are_registered() -> None:
    expected_tables = {
        "users",
        "auth_sessions",
        "refresh_credentials",
        "identity_one_time_tokens",
    }
    assert expected_tables == set(Base.metadata.tables)


def test_orm_relationships_resolve_without_legacy_domains() -> None:
    Base.registry.configure()
    mapper = inspect(User)
    assert "owned_organizations" not in mapper.relationships
    assert "organization_memberships" not in mapper.relationships
