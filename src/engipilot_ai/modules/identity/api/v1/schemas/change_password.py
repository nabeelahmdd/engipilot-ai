"""Authenticated password-change request validation."""

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationInfo, field_validator


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: SecretStr
    new_password: SecretStr
    confirm_password: SecretStr

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(
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
