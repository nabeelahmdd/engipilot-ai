"""Login request and public credential response."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=1, max_length=320)
    password: SecretStr


class LoginResponse(BaseModel):
    user_uuid: UUID
    session_uuid: UUID
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    csrf_token: str | None = None
