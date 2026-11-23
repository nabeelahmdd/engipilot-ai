import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch

from engipilot_ai.core.config import Settings


def test_settings_from_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5434/db")
    monkeypatch.setenv("APP_ENV", "test")
    settings = Settings(_env_file=None)
    assert settings.app_env == "test"
    assert settings.database_url.endswith("/db")


def test_reject_invalid_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="not-real",
            database_url="postgresql+asyncpg://u:p@localhost/db",
        )
