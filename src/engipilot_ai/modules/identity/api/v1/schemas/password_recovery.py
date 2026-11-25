"""Password recovery public request and response schemas."""

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    SecretStr,
    ValidationInfo,
    field_validator,
)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str = "If an eligible account exists, a password reset email will be sent."


class ResetPasswordRequest(BaseModel):
    token: SecretStr = Field(min_length=16, max_length=512)
    new_password: SecretStr
    confirm_password: SecretStr

    @field_validator("confirm_password")
    @classmethod
    def validate_matching_password(
        cls,
        value: SecretStr,
        info: ValidationInfo,
    ) -> SecretStr:
        new_password = info.data.get("new_password")
        if new_password is not None and (
            value.get_secret_value() != new_password.get_secret_value()
        ):
            raise ValueError("Passwords do not match")
        return value


class ResetPasswordResponse(BaseModel):
    message: str = "Password reset successfully"
