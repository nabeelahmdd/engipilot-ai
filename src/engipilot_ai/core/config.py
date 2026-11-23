"""Centralized environment configuration validated using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Compose may use additional local-only variables.
    )

    app_env: Literal["local", "test", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: str = Field(min_length=1)

    jwt_private_key_file: Path = Path(".secrets/jwt-private.pem")

    jwt_public_key_file: Path = Path(".secrets/jwt-public.pem")

    jwt_issuer: str = "engipilot-local"

    jwt_audience: str = "engipilot-api"

    jwt_key_id: str = "local-v1"

    jwt_access_minutes: int = Field(
        default=5,
        ge=1,
        le=15,
    )

    refresh_session_days: int = Field(
        default=14,
        ge=1,
        le=30,
    )

    email_verification_hours: int = Field(
        default=24,
        ge=1,
        le=72,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
