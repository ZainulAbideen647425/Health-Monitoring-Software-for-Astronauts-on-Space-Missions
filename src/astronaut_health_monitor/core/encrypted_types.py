"""Database column types that encrypt on the way in and decrypt on the way out."""

from sqlalchemy import Text
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

from astronaut_health_monitor.core.field_encryption import get_field_encryptor


class EncryptedText(TypeDecorator[str]):
    """Text stored as an encrypted token."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        return None if value is None else get_field_encryptor().encrypt_text(value)

    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        return None if value is None else get_field_encryptor().decrypt_text(value)


class EncryptedFloat(TypeDecorator[float]):
    """A number stored as an encrypted token. It cannot be used in database filters or sorting."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: float | None, dialect: Dialect) -> str | None:
        return None if value is None else get_field_encryptor().encrypt_text(repr(float(value)))

    def process_result_value(self, value: str | None, dialect: Dialect) -> float | None:
        return None if value is None else float(get_field_encryptor().decrypt_text(value))
