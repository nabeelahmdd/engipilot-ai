"""Password recovery public request and response schemas."""

from pydantic import BaseModel, EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str = "If an eligible account exists, a password reset email will be sent."
