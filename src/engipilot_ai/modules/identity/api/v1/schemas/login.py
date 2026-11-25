"""Login request and public credential response."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: SecretStr
    client_type: Literal["browser", "native"] = "browser"


class LoginResponse(BaseModel):
    user_uuid: UUID
    session_uuid: UUID
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    refresh_token: str | None = None
    csrf_token: str | None = None
