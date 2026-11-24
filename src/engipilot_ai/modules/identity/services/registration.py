"""Email/password user registration."""

import uuid
from dataclasses import dataclass
from datetime import timedelta

from email_validator import EmailNotValidError, validate_email
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from engipilot_ai.core.config import get_settings
from engipilot_ai.modules.identity.email_payload import (
    get_email_payload_cipher,
)
from engipilot_ai.modules.identity.passwords import (
    hash_password_async,
    validate_new_password,
)
from engipilot_ai.modules.identity.repository import IdentityRepository
from engipilot_ai.modules.identity.tokens import (
    digest_secret,
    random_secret,
    utcnow,
)


class InvalidRegistrationData(ValueError):
    """Invalid registration information."""


class EmailAlreadyRegistered(ValueError):
    """Email already belongs to a user."""


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    """Internal result, not a public API response."""

    user_uuid: uuid.UUID
    verification_secret: str


def normalize_email(email: str) -> str:
    """Validate and normalize the email identity."""
    try:
        result = validate_email(
            email.strip(),
            check_deliverability=False,
        )
    except EmailNotValidError as exc:
        raise InvalidRegistrationData("Invalid email address") from exc

    normalized = result.normalized.lower()

    if len(normalized) > 320:
        raise InvalidRegistrationData("Email address is too long")

    return normalized


def normalize_name(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    normalized = value.strip()

    if len(normalized) > 100:
        raise InvalidRegistrationData("Name cannot exceed 100 characters")

    return normalized or None


def is_email_unique_conflict(
    exc: IntegrityError,
) -> bool:
    """Recognize only our email uniqueness constraints."""
    driver_error = exc.orig
    original_error = getattr(
        driver_error,
        "__cause__",
        None,
    )

    sqlstate = getattr(driver_error, "sqlstate", None) or getattr(
        original_error, "sqlstate", None
    )

    constraint = getattr(driver_error, "constraint_name", None) or getattr(
        original_error, "constraint_name", None
    )

    return sqlstate == "23505" and constraint in {
        "uq_users_email_lower",
        "users_email_key",
    }


class RegistrationService:
    @staticmethod
    async def register(
        session: AsyncSession,
        *,
        email: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> RegistrationResult:
        """Create user and verification token atomically."""
        normalized_email = normalize_email(email)
        first_name = normalize_name(first_name)
        last_name = normalize_name(last_name)

        try:
            validate_new_password(password)
        except ValueError as exc:
            raise InvalidRegistrationData(str(exc)) from exc

        # Expensive hashing happens before opening
        # the database transaction.
        password_hash = await hash_password_async(password)

        verification_secret = random_secret()
        verification_hash = digest_secret(verification_secret)

        encrypted_payload = get_email_payload_cipher().encrypt_token(
            verification_secret
        )

        expires_at = utcnow() + timedelta(hours=get_settings().email_verification_hours)

        try:
            async with session.begin():
                existing = await IdentityRepository.get_user_by_email(
                    session,
                    normalized_email,
                )

                if existing is not None:
                    raise EmailAlreadyRegistered("Email already registered")

                user = await IdentityRepository.create_user(
                    session,
                    email=normalized_email,
                    password_hash=password_hash,
                    first_name=first_name,
                    last_name=last_name,
                )

                await IdentityRepository.create_one_time_token(
                    session,
                    user_id=user.id,
                    purpose="verify_email",
                    token_hash=verification_hash,
                    expires_at=expires_at,
                )

                await IdentityRepository.create_email_outbox(
                    session,
                    user_id=user.id,
                    recipient_email=normalized_email,
                    template="verify_email",
                    encrypted_payload=encrypted_payload,
                )

                user_uuid = user.uuid

        except IntegrityError as exc:
            # Handles a concurrent registration that passed
            # the initial existence check.
            if is_email_unique_conflict(exc):
                raise EmailAlreadyRegistered("Email already registered") from exc
            raise

        return RegistrationResult(
            user_uuid=user_uuid,
            verification_secret=verification_secret,
        )
