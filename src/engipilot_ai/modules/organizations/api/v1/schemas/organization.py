"""Organization API v1 request and response contracts."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class OrganizationCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(
        min_length=2,
        max_length=160,
    )

    code: str = Field(
        min_length=3,
        max_length=80,
        pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$",
    )


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: uuid.UUID
    name: str
    code: str
