"""Shared SQLAlchemy initialization for the EngiPilot test suite."""

import engipilot_ai.models  # noqa: F401
from engipilot_ai.core.db_base import Base

# Import and validate the complete ORM model graph
# before pytest executes any tests.
Base.registry.configure()
