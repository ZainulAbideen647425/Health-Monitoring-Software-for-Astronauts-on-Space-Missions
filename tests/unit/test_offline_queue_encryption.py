from datetime import UTC, datetime
from pathlib import Path

import pytest

from astronaut_health_monitor.core.field_encryption import FieldEncryptor, generate_encryption_key
from astronaut_health_monitor.domain.enumerations import HealthIndicatorType
from astronaut_health_monitor.offline_synchronization.offline_measurement_queue import (
    OfflineMeasurementQueue,
    OfflineQueueCorruptedError,
)


def test_encrypted_queue_file_hides_its_content_but_works_normally(tmp_path: Path) -> None:
    encryptor = FieldEncryptor(generate_encryption_key().encode("ascii"))
    queue_file = tmp_path / "queue.bin"
    queue = OfflineMeasurementQueue(queue_file, encryptor)
    queue.enqueue_measurement(
        1, HealthIndicatorType.HEART_RATE, 61.5, datetime(2026, 11, 1, tzinfo=UTC), notes="private"
    )
    raw = queue_file.read_bytes()
    assert b"heart_rate" not in raw and b"private" not in raw and b"61.5" not in raw
    reopened = OfflineMeasurementQueue(queue_file, encryptor)
    assert reopened.pending_measurements()[0]["measured_value"] == 61.5


def test_wrong_key_or_tampered_queue_file_is_reported_not_silently_accepted(tmp_path: Path) -> None:
    queue_file = tmp_path / "queue.bin"
    right = FieldEncryptor(generate_encryption_key().encode("ascii"))
    OfflineMeasurementQueue(queue_file, right).enqueue_measurement(
        1, HealthIndicatorType.HEART_RATE, 61.5, datetime(2026, 11, 1, tzinfo=UTC)
    )
    wrong = FieldEncryptor(generate_encryption_key().encode("ascii"))
    with pytest.raises(OfflineQueueCorruptedError):
        OfflineMeasurementQueue(queue_file, wrong).pending_measurements()
    queue_file.write_bytes(queue_file.read_bytes()[:-6] + b"AAAAAA")
    with pytest.raises(OfflineQueueCorruptedError):
        OfflineMeasurementQueue(queue_file, right).pending_measurements()
