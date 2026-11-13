import os
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from astronaut_health_monitor.core.field_encryption import (
    FieldEncryptor,
    configure_field_encryption,
    generate_encryption_key,
    get_field_encryptor,
    load_or_create_encryption_key,
)
from astronaut_health_monitor.domain.exceptions import EncryptionNotConfiguredError, FieldDecryptionError
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.measurement_repository import MeasurementRepository


def new_encryptor() -> FieldEncryptor:
    return FieldEncryptor(generate_encryption_key().encode("ascii"))


def test_text_round_trip_and_ciphertext_hides_the_text() -> None:
    encryptor = new_encryptor()
    token = encryptor.encrypt_text("heart rate 72 for Ada Lovelace")
    assert "Ada" not in token and "72" not in token
    assert encryptor.decrypt_text(token) == "heart rate 72 for Ada Lovelace"
    assert encryptor.encrypt_text("same") != encryptor.encrypt_text("same")  # fresh randomness each time


def test_wrong_key_and_tampering_are_detected() -> None:
    token = new_encryptor().encrypt_text("secret")
    with pytest.raises(FieldDecryptionError):
        new_encryptor().decrypt_text(token)
    encryptor = new_encryptor()
    good = encryptor.encrypt_text("secret")
    altered = good[:-4] + ("AAAA" if not good.endswith("AAAA") else "BBBB")
    with pytest.raises(FieldDecryptionError):
        encryptor.decrypt_text(altered)


def test_using_encrypted_data_without_a_key_is_an_error() -> None:
    configure_field_encryption(None)
    with pytest.raises(EncryptionNotConfiguredError):
        get_field_encryptor()


def test_configured_key_wins_and_a_key_file_is_created_once_and_reused(tmp_path: Path) -> None:
    key_file = tmp_path / "data.key"
    configured = generate_encryption_key()
    assert load_or_create_encryption_key(configured, key_file) == configured.encode("ascii")
    assert not key_file.exists()
    created = load_or_create_encryption_key(None, key_file)
    assert key_file.exists()
    assert load_or_create_encryption_key(None, key_file) == created
    if os.name == "posix":
        assert stat.S_IMODE(key_file.stat().st_mode) == 0o600


def test_database_stores_only_ciphertext_for_names_values_and_notes(database_session: Session) -> None:
    astronaut = AstronautRepository(database_session).add_astronaut("Ada Lovelace", "Commander", None)
    MeasurementRepository(database_session).add_measurement(
        astronaut_id=astronaut.id,
        indicator_type="heart_rate",
        measured_value=73.25,
        measurement_unit="beats per minute",
        measured_at=datetime(2026, 11, 1, 8, 0, tzinfo=UTC),
        measurement_source="manual_entry",
        device_id=None,
        notes="felt dizzy after exercise",
    )
    stored_name: str = database_session.execute(text("SELECT full_name FROM astronauts")).scalar_one()
    stored_value, stored_notes = database_session.execute(text("SELECT measured_value, notes FROM measurements")).one()
    assert "Ada" not in stored_name
    assert "73.25" not in stored_value
    assert "dizzy" not in stored_notes
    database_session.expire_all()
    assert AstronautRepository(database_session).get_astronaut_by_id(astronaut.id).full_name == "Ada Lovelace"  # type: ignore[union-attr]
    reloaded = MeasurementRepository(database_session).list_measurements(astronaut.id)[0]
    assert reloaded.measured_value == 73.25
    assert reloaded.notes == "felt dizzy after exercise"
