"""JWT signing and verification unit tests."""

import uuid
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from engipilot_ai.modules.identity import tokens


@pytest.fixture
def configured_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[bytes]:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path = tmp_path / "private.pem"
    public_path = tmp_path / "public.pem"

    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)

    settings = SimpleNamespace(
        jwt_private_key_file=private_path,
        jwt_public_key_file=public_path,
        jwt_issuer="engipilot-test",
        jwt_audience="engipilot-api",
        jwt_key_id="test-key",
        jwt_access_minutes=5,
    )

    monkeypatch.setattr(
        tokens,
        "get_settings",
        lambda: settings,
    )

    tokens.signing_key.cache_clear()
    tokens.verification_key.cache_clear()

    yield private_pem

    tokens.signing_key.cache_clear()
    tokens.verification_key.cache_clear()


def test_valid_jwt_roundtrip(configured_keys: bytes) -> None:
    user_uuid = uuid.uuid4()
    session_uuid = uuid.uuid4()

    encoded = tokens.issue_access_token(
        user_uuid=user_uuid,
        session_uuid=session_uuid,
        auth_version=3,
    )

    claims = tokens.validate_access_token(encoded)

    assert claims.user_uuid == user_uuid
    assert claims.session_uuid == session_uuid
    assert claims.auth_version == 3
    assert isinstance(claims.token_uuid, uuid.UUID)

    header = jwt.get_unverified_header(encoded)
    assert header["alg"] == "RS256"
    assert header["kid"] == "test-key"


def test_tampered_jwt_is_rejected(
    configured_keys: bytes,
) -> None:
    encoded = tokens.issue_access_token(
        uuid.uuid4(),
        uuid.uuid4(),
        1,
    )

    header, payload, signature = encoded.split(".")

    modified = ("A" if payload[0] != "A" else "B") + payload[1:]

    tampered = f"{header}.{modified}.{signature}"

    with pytest.raises(tokens.InvalidAccessToken):
        tokens.validate_access_token(tampered)


def test_expired_jwt_is_rejected(
    configured_keys: bytes,
) -> None:
    encoded = tokens.issue_access_token(
        uuid.uuid4(),
        uuid.uuid4(),
        1,
    )

    claims = jwt.decode(
        encoded,
        options={"verify_signature": False},
        algorithms=["RS256"],
    )

    now = tokens.utcnow()

    claims["iat"] = now - timedelta(minutes=3)
    claims["nbf"] = now - timedelta(minutes=3)
    claims["exp"] = now - timedelta(minutes=1)

    expired = jwt.encode(
        claims,
        configured_keys,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    with pytest.raises(tokens.InvalidAccessToken):
        tokens.validate_access_token(expired)


def test_wrong_token_type_is_rejected(
    configured_keys: bytes,
) -> None:
    encoded = tokens.issue_access_token(
        uuid.uuid4(),
        uuid.uuid4(),
        1,
    )

    claims = jwt.decode(
        encoded,
        options={"verify_signature": False},
        algorithms=["RS256"],
    )

    claims["token_type"] = "refresh"

    invalid = jwt.encode(
        claims,
        configured_keys,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    with pytest.raises(tokens.InvalidAccessToken):
        tokens.validate_access_token(invalid)


def test_invalid_auth_version_is_rejected(
    configured_keys: bytes,
) -> None:
    encoded = tokens.issue_access_token(
        uuid.uuid4(),
        uuid.uuid4(),
        1,
    )

    claims = jwt.decode(
        encoded,
        options={"verify_signature": False},
        algorithms=["RS256"],
    )

    claims["auth_version"] = True

    invalid = jwt.encode(
        claims,
        configured_keys,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    with pytest.raises(tokens.InvalidAccessToken):
        tokens.validate_access_token(invalid)


def test_random_secret_hashing() -> None:
    first = tokens.random_secret()
    second = tokens.random_secret()

    assert first != second
    assert tokens.digest_secret(first) != tokens.digest_secret(second)
    assert len(tokens.digest_secret(first)) == 64
