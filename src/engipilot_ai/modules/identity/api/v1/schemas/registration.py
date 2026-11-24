"""Registration request and response schemas."""

from uuid import UUID

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    SecretStr,
    ValidationInfo,
    field_validator,
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: SecretStr
    confirm_password: SecretStr

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(
        cls,
        value: SecretStr,
        info: ValidationInfo,
    ) -> SecretStr:
        password = info.data.get("password")

        if password is not None and (
            value.get_secret_value() != password.get_secret_value()
        ):
            raise ValueError("Passwords do not match")

        return value


class RegisterResponse(BaseModel):
    user_uuid: UUID
    email_verification_required: bool = True
