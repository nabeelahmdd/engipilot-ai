"""Email verification request and response."""

from uuid import UUID

from pydantic import BaseModel, Field, SecretStr


class VerifyEmailRequest(BaseModel):
    token: SecretStr = Field(min_length=16, max_length=512)


class VerifyEmailResponse(BaseModel):
    user_uuid: UUID
    email_verified: bool = True
