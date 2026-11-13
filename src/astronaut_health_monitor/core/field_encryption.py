"""Encryption of sensitive stored data (Fernet: AES-128 with an integrity check).

A wrong key or any change to the stored data is detected and reported; it is never silently accepted.
"""

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from astronaut_health_monitor.domain.exceptions import EncryptionNotConfiguredError, FieldDecryptionError


class FieldEncryptor:
    def __init__(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    def encrypt_bytes(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, token: bytes) -> bytes:
        try:
            return self._fernet.decrypt(token)
        except InvalidToken as error:
            raise FieldDecryptionError(
                "Stored data could not be decrypted: wrong key or the data was altered."
            ) from error

    def encrypt_text(self, text: str) -> str:
        return self.encrypt_bytes(text.encode("utf-8")).decode("ascii")

    def decrypt_text(self, token: str) -> str:
        return self.decrypt_bytes(token.encode("ascii")).decode("utf-8")


_active_encryptor: FieldEncryptor | None = None


def configure_field_encryption(encryptor: FieldEncryptor | None) -> None:
    """Choose the key used by every encrypted database column in this process."""
    global _active_encryptor
    _active_encryptor = encryptor


def get_field_encryptor() -> FieldEncryptor:
    if _active_encryptor is None:
        raise EncryptionNotConfiguredError("No encryption key is configured.")
    return _active_encryptor


def generate_encryption_key() -> str:
    return Fernet.generate_key().decode("ascii")


def load_or_create_encryption_key(configured_key: str | None, key_file_path: Path) -> bytes:
    """Use the key from settings if given; otherwise read (or create, readable by the owner only) a key file."""
    if configured_key:
        return configured_key.encode("ascii")
    if key_file_path.exists():
        return key_file_path.read_bytes().strip()
    key = Fernet.generate_key()
    file_descriptor = os.open(key_file_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(file_descriptor, "wb") as key_file:
        key_file.write(key)
    return key
