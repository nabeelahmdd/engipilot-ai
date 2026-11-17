"""Unit tests for identity password security."""

from engipilot_ai.modules.identity.passwords import (
    hash_password,
    verify_password,
)


def test_password_hash_uses_argon2id() -> None:
    password = "MyStrongTestPassword@2026"

    encoded_hash = hash_password(password)

    assert encoded_hash.startswith("$argon2id$")
    assert encoded_hash != password


def test_correct_password_is_verified() -> None:
    password = "MyStrongTestPassword@2026"

    encoded_hash = hash_password(password)

    assert verify_password(password, encoded_hash) is True


def test_incorrect_password_is_rejected() -> None:
    encoded_hash = hash_password("CorrectPassword123!")

    assert verify_password("WrongPassword123!", encoded_hash) is False


def test_same_password_produces_different_hashes() -> None:
    password = "MyStrongTestPassword@2026"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash

    assert verify_password(password, first_hash)
    assert verify_password(password, second_hash)


def test_account_without_password_is_rejected() -> None:
    assert verify_password("AnyPassword123!", None) is False


def test_unicode_password_is_supported() -> None:
    password = "LongUnicodePassword🔐2026"

    encoded_hash = hash_password(password)

    assert verify_password(password, encoded_hash) is True
