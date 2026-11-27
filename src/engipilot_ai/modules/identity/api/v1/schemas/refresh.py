"""Browser refresh response schema."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class RefreshResponse(BaseModel):
    user_uuid: UUID
    session_uuid: UUID
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
