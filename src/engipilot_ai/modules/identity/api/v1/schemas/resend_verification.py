"""Resend verification email API schemas."""

from pydantic import BaseModel, EmailStr


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ResendVerificationResponse(BaseModel):
    message: str = "If your account requires verification, an email will be sent."
