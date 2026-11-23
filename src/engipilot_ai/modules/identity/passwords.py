"""Password validation, hashing and verification."""

from functools import lru_cache

import anyio
from pwdlib import PasswordHash

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

_hasher = PasswordHash.recommended()

# Limits concurrent Argon2id operations per application process.
_password_limiter = anyio.CapacityLimiter(4)


def validate_new_password(password: str) -> None:
    """Validate EngiPilot's chosen password policy."""
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must contain "
            f"{MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters"
        )

    if not any(char.isalpha() for char in password):
        raise ValueError("Password must contain at least one letter")

    if not any(char.isdecimal() for char in password):
        raise ValueError("Password must contain at least one number")

    if not any(not char.isalnum() and not char.isspace() for char in password):
        raise ValueError("Password must contain at least one special character")


def hash_password(password: str) -> str:
    """Return an Argon2id encoded hash."""
    return _hasher.hash(password)


def verify_password(
    password: str,
    stored_hash: str | None,
) -> bool:
    """Verify a password against an existing hash."""
    if stored_hash is None:
        return False

    return _hasher.verify(password, stored_hash)


def verify_and_update_password(
    password: str,
    stored_hash: str,
) -> tuple[bool, str | None]:
    """Verify and optionally upgrade an outdated hash."""
    return _hasher.verify_and_update(
        password,
        stored_hash,
    )


async def hash_password_async(password: str) -> str:
    """Hash without blocking FastAPI's event loop."""
    return await anyio.to_thread.run_sync(
        hash_password,
        password,
        limiter=_password_limiter,
    )


async def verify_password_async(
    password: str,
    stored_hash: str,
) -> bool:
    """Verify using the bounded Argon2id worker capacity."""
    return await anyio.to_thread.run_sync(
        verify_password,
        password,
        stored_hash,
        limiter=_password_limiter,
    )


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    """Reusable hash used for unknown accounts."""
    return hash_password("EngiPilotDummyPassword@2026")


def _verify_unknown_password(password: str) -> None:
    """Perform password verification work for an unknown user."""
    verify_password(password, _dummy_password_hash())


async def verify_unknown_password_async(password: str) -> None:
    """Run unknown-account verification under the same limiter."""
    await anyio.to_thread.run_sync(
        _verify_unknown_password,
        password,
        limiter=_password_limiter,
    )
