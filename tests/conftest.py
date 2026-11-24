"""Shared SQLAlchemy initialization for the CommercePilot test suite."""

import engipilot_ai.models  # noqa: F401
from engipilot_ai.core.db_base import Base

# Import and validate the current ORM model graph before any tests execute.
Base.registry.configure()
