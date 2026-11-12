
"""Register all ORM models for SQLAlchemy and Alembic."""



def register_models() -> None:
    """Import concrete ORM models into the shared metadata registry."""
    from engipilot_ai.modules.identity.models import User
    from engipilot_ai.modules.organizations.models import (
        Organization,
        OrganizationMembership,
    )
    from engipilot_ai.modules.projects.models import (
        Project,
        ProjectMembership,
    )

    # References prevent unused-import warnings and confirm registration.
    models = (
        User,
        Organization,
        OrganizationMembership,
        Project,
        ProjectMembership,
    )

    assert len(models) == 5
