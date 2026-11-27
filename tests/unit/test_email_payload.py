"""Tests for identity email payload encryption."""

import pytest
from cryptography.fernet import Fernet, InvalidToken

from engipilot_ai.modules.identity.email_payload import EmailPayloadCipher


def test_email_payload_encryption_round_trip() -> None:
    cipher = EmailPayloadCipher(Fernet.generate_key().decode())
    token = "verification-secret-example"

    encrypted = cipher.encrypt_token(token)

    assert token.encode() not in encrypted
    assert cipher.decrypt_token(encrypted) == token


def test_tampered_email_payload_is_rejected() -> None:
    cipher = EmailPayloadCipher(Fernet.generate_key().decode())

    encrypted = bytearray(cipher.encrypt_token("verification-token"))
    encrypted[20] = ord("!")

    with pytest.raises(InvalidToken):
        cipher.decrypt_token(bytes(encrypted))


def test_invalid_encryption_key_is_rejected() -> None:
    with pytest.raises(ValueError):
        EmailPayloadCipher("invalid-key")
