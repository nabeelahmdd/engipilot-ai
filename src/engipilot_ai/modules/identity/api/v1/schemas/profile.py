"""Authenticated profile request and response contracts."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_uuid: UUID = Field(validation_alias="uuid")
    email: EmailStr | None
    mobile: str | None
    first_name: str | None
    last_name: str | None
    is_email_verified: bool
    is_mobile_verified: bool


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
