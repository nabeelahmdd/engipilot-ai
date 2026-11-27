"""Encryption of sensitive identity email payloads."""

from cryptography.fernet import Fernet

from engipilot_ai.core.config import get_settings


class EmailPayloadCipher:
    """Encrypt and decrypt short-lived email secrets."""

    def __init__(self, key: str) -> None:
        try:
            self._fernet = Fernet(key.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise ValueError("Invalid email outbox encryption key") from exc

    def encrypt_token(self, token: str) -> bytes:
        """Encrypt a verification or recovery token."""
        return self._fernet.encrypt(token.encode("ascii"))

    def decrypt_token(self, payload: bytes) -> str:
        """Decrypt a token for the email delivery worker."""
        return self._fernet.decrypt(payload).decode("ascii")


def get_email_payload_cipher() -> EmailPayloadCipher:
    """Build the cipher from the configured application secret."""
    key = get_settings().email_outbox_key

    if key is None:
        raise RuntimeError("EMAIL_OUTBOX_KEY is not configured")

    return EmailPayloadCipher(key.get_secret_value())
