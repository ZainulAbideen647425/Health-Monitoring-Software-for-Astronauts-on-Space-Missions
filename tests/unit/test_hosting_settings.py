from cryptography.fernet import Fernet

from astronaut_health_monitor.core.database import normalise_database_url
from astronaut_health_monitor.core.field_encryption import FieldEncryptor, load_or_create_encryption_key


def test_hosting_database_addresses_get_the_driver_named() -> None:
    assert normalise_database_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert normalise_database_url("postgresql://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert normalise_database_url("sqlite:///./a.db") == "sqlite:///./a.db"


def test_a_real_fernet_key_is_used_unchanged(tmp_path) -> None:  # type: ignore[no-untyped-def]
    key = Fernet.generate_key().decode()
    assert load_or_create_encryption_key(key, tmp_path / "unused") == key.encode()


def test_any_other_secret_text_becomes_a_stable_working_key(tmp_path) -> None:  # type: ignore[no-untyped-def]
    first = load_or_create_encryption_key("a-long-random-value-from-the-host", tmp_path / "unused")
    second = load_or_create_encryption_key("a-long-random-value-from-the-host", tmp_path / "unused")
    assert first == second
    encryptor = FieldEncryptor(first)
    assert encryptor.decrypt_text(encryptor.encrypt_text("kept after restart")) == "kept after restart"
    assert not (tmp_path / "unused").exists()
