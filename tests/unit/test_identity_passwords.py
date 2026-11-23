"""Argon2id password security tests."""

import pytest

from engipilot_ai.modules.identity.passwords import (
    hash_password,
    validate_new_password,
    verify_and_update_password,
    verify_password,
)


def test_password_is_hashed_using_argon2id() -> None:
    password = "MySecurePassword123!"

    encoded = hash_password(password)

    assert encoded.startswith("$argon2id$")
    assert encoded != password


def test_correct_password_is_accepted() -> None:
    password = "MySecurePassword123!"
    encoded = hash_password(password)

    assert verify_password(password, encoded)


def test_wrong_password_is_rejected() -> None:
    encoded = hash_password("CorrectPassword123!")

    assert not verify_password(
        "IncorrectPassword123!",
        encoded,
    )


def test_salts_generate_different_hashes() -> None:
    password = "MySecurePassword123!"

    first = hash_password(password)
    second = hash_password(password)

    assert first != second

    assert verify_password(password, first)
    assert verify_password(password, second)


def test_missing_password_hash_is_rejected() -> None:
    assert not verify_password("AnyPassword123456", None)


def test_password_length_validation() -> None:
    # Minimum valid length: 8
    validate_new_password("abc123!x")

    # Maximum valid length: 128
    validate_new_password("Ab1!" + "x" * 124)

    # Below minimum
    with pytest.raises(ValueError):
        validate_new_password("Ab1!")

    # Above maximum: 129
    with pytest.raises(ValueError):
        validate_new_password("Ab1!" + "x" * 125)


def test_hash_upgrade_interface() -> None:
    password = "MySecurePassword123!"
    encoded = hash_password(password)

    valid, updated_hash = verify_and_update_password(
        password,
        encoded,
    )

    assert valid
    assert updated_hash is None


@pytest.mark.parametrize(
    "password",
    [
        "abc123!x",
        "EngiPilot@2026",
        "LongStrongPassword123!",
    ],
)
def test_valid_password_policy(password: str) -> None:
    validate_new_password(password)


@pytest.mark.parametrize(
    "password",
    [
        "Ab1!",
        "abcdefgh",
        "abcdefgh!",
        "1234567!",
        "abcdef12",
    ],
)
def test_invalid_password_policy(password: str) -> None:
    with pytest.raises(ValueError):
        validate_new_password(password)
