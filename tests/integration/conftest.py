"""Shared configuration for database integration tests."""

from collections.abc import Iterator

import pytest
from cryptography.fernet import Fernet

from engipilot_ai.core.config import get_settings


@pytest.fixture(autouse=True)
def configure_test_email_key(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Provide a fresh, test-only email encryption key."""
    monkeypatch.setenv(
        "EMAIL_OUTBOX_KEY",
        Fernet.generate_key().decode("ascii"),
    )

    get_settings.cache_clear()

    yield

    get_settings.cache_clear()
