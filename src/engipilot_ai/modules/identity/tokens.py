"""JWT access tokens and random authentication credentials."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt
from jwt import InvalidTokenError

from engipilot_ai.core.config import get_settings


@dataclass(frozen=True, slots=True)
class AccessClaims:
    """Trusted claims returned after JWT validation."""

    user_uuid: uuid.UUID
    session_uuid: uuid.UUID
    token_uuid: uuid.UUID
    auth_version: int


class InvalidAccessToken(Exception):
    """JWT failed authentication validation."""


def utcnow() -> datetime:
    return datetime.now(UTC)


def random_secret() -> str:
    """Generate an unpredictable opaque credential."""
    return secrets.token_urlsafe(48)


def digest_secret(secret: str) -> str:
    """Produce a SHA-256 digest for random credentials."""
    return hashlib.sha256(secret.encode("ascii")).hexdigest()


@lru_cache(maxsize=1)
def signing_key() -> bytes:
    """Load the RSA private key for signing."""
    return get_settings().jwt_private_key_file.read_bytes()


@lru_cache(maxsize=1)
def verification_key() -> bytes:
    """Load the RSA public key for verification."""
    return get_settings().jwt_public_key_file.read_bytes()


def issue_access_token(
    user_uuid: uuid.UUID,
    session_uuid: uuid.UUID,
    auth_version: int,
) -> str:
    """Sign a short-lived JWT using our RSA private key."""
    if type(auth_version) is not int or auth_version < 1:
        raise ValueError("Invalid authentication version")

    settings = get_settings()
    private_key = signing_key()

    now = utcnow()

    claims = {
        "sub": str(user_uuid),
        "sid": str(session_uuid),
        "jti": str(uuid.uuid4()),
        "auth_version": auth_version,
        "token_type": "access",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=settings.jwt_access_minutes),
    }

    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": settings.jwt_key_id},
    )


def validate_access_token(token: str) -> AccessClaims:
    """Verify a JWT and return typed trusted identity claims."""
    if not token or len(token) > 8192:
        raise InvalidAccessToken("Invalid access token")

    settings = get_settings()
    public_key = verification_key()

    try:
        header = jwt.get_unverified_header(token)

        # Compare untrusted key metadata against our configured
        # trusted key identifier. Do not fetch a key from the
        # URL or other arbitrary token-header field.
        if header.get("kid") != settings.jwt_key_id:
            raise InvalidAccessToken("Unknown JWT signing key")

        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            leeway=5,
            options={
                "require": [
                    "sub",
                    "sid",
                    "jti",
                    "auth_version",
                    "token_type",
                    "iss",
                    "aud",
                    "iat",
                    "nbf",
                    "exp",
                ],
            },
        )

        if claims["token_type"] != "access":
            raise InvalidAccessToken("Wrong JWT token type")

        version = claims["auth_version"]

        if type(version) is not int or version < 1:
            raise InvalidAccessToken("Invalid auth version")

        for field in ("iat", "nbf", "exp"):
            if type(claims[field]) is not int:
                raise InvalidAccessToken("Invalid JWT timestamp")

        if claims["exp"] <= claims["iat"]:
            raise InvalidAccessToken("Invalid JWT lifetime")

        max_age = settings.jwt_access_minutes * 60

        if claims["exp"] - claims["iat"] > max_age:
            raise InvalidAccessToken("JWT lifetime too long")

        for field in ("sub", "sid", "jti"):
            if type(claims[field]) is not str:
                raise InvalidAccessToken("Invalid JWT identity")

        return AccessClaims(
            user_uuid=uuid.UUID(claims["sub"]),
            session_uuid=uuid.UUID(claims["sid"]),
            token_uuid=uuid.UUID(claims["jti"]),
            auth_version=version,
        )

    except (InvalidTokenError, ValueError, TypeError, KeyError) as exc:
        raise InvalidAccessToken("Invalid access token") from exc
