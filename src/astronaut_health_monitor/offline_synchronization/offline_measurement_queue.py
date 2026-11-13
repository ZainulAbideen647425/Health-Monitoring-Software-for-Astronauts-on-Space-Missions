"""A durable local queue for measurements taken while the connection to the main system is unavailable.

How it works:
    1. The device calls `enqueue_measurement`. The measurement is written to a file immediately,
       together with a unique client reference, so nothing is lost if the device restarts.
    2. When a connection exists, `synchronize` sends the queued items in batches to POST /measurements/batch.
    3. Items reported as created or duplicate are removed. Items the server rejects are moved to a separate
       "rejected" list with the reason, so one bad item never blocks the rest and is never retried forever.
    4. If the connection fails, everything stays queued and the next call to `synchronize` tries again.

Because every item carries a client reference and the server ignores references it already stored,
sending the same item twice (for example after a lost reply) can never create a duplicate record.
"""

import json
import os
import tempfile
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from astronaut_health_monitor.core.field_encryption import FieldEncryptor
from astronaut_health_monitor.domain.enumerations import BatchItemOutcome, HealthIndicatorType, MeasurementSource
from astronaut_health_monitor.domain.exceptions import FieldDecryptionError

DEFAULT_BATCH_SIZE = 100

# A function that sends a list of measurement dictionaries to the server and returns the server's JSON reply.
# It must raise ConnectionError, TimeoutError or OSError when the connection is unavailable.
BatchSender = Callable[[list[dict[str, Any]]], Mapping[str, Any]]


class OfflineQueueCorruptedError(Exception):
    """The queue file exists but cannot be read as a queue."""


@dataclass(frozen=True)
class SynchronizationReport:
    """What happened during one call to `synchronize`."""

    created_count: int
    duplicate_count: int
    rejected_count: int
    remaining_count: int
    connection_failed: bool


class OfflineMeasurementQueue:
    def __init__(self, queue_file_path: Path, encryptor: FieldEncryptor | None = None) -> None:
        """With an encryptor the queue file is stored encrypted; without one it is readable JSON."""
        self._queue_file_path = queue_file_path
        self._encryptor = encryptor

    def enqueue_measurement(
        self,
        astronaut_id: int,
        indicator_type: HealthIndicatorType,
        measured_value: float,
        measured_at: datetime,
        measurement_source: MeasurementSource = MeasurementSource.MANUAL_ENTRY,
        device_id: int | None = None,
        notes: str | None = None,
    ) -> str:
        """Store a measurement locally and return its client reference."""
        if measured_at.tzinfo is None:
            raise ValueError("measured_at must include a timezone.")
        client_reference = uuid.uuid4().hex
        item: dict[str, Any] = {
            "astronaut_id": astronaut_id,
            "indicator_type": indicator_type.value,
            "measured_value": measured_value,
            "measured_at": measured_at.astimezone(UTC).isoformat(),
            "measurement_source": measurement_source.value,
            "device_id": device_id,
            "notes": notes,
            "client_reference": client_reference,
        }
        queue_contents = self._load()
        queue_contents["pending"].append(item)
        self._save(queue_contents)
        return client_reference

    def pending_measurements(self) -> list[dict[str, Any]]:
        return list(self._load()["pending"])

    def rejected_measurements(self) -> list[dict[str, Any]]:
        """Items the server refused, each with a `rejection_reason`."""
        return list(self._load()["rejected"])

    def synchronize(self, send_batch: BatchSender, batch_size: int = DEFAULT_BATCH_SIZE) -> SynchronizationReport:
        created_count = duplicate_count = rejected_count = 0
        connection_failed = False

        while True:
            queue_contents = self._load()
            batch = queue_contents["pending"][:batch_size]
            if not batch:
                break
            try:
                reply = send_batch(batch)
            except (ConnectionError, TimeoutError, OSError):
                connection_failed = True
                break

            outcome_by_index = {result["index"]: result for result in reply.get("results", [])}
            still_pending: list[dict[str, Any]] = []
            for index, item in enumerate(batch):
                result = outcome_by_index.get(index)
                if result is None:
                    still_pending.append(item)  # the server did not answer for this item: keep it
                    continue
                outcome = BatchItemOutcome(result["outcome"])
                if outcome is BatchItemOutcome.CREATED:
                    created_count += 1
                elif outcome is BatchItemOutcome.DUPLICATE:
                    duplicate_count += 1
                else:
                    rejected_count += 1
                    queue_contents["rejected"].append({**item, "rejection_reason": result.get("rejection_reason")})

            if len(still_pending) == len(batch):
                break  # no progress was possible; stop instead of looping forever
            queue_contents["pending"] = still_pending + queue_contents["pending"][len(batch) :]
            self._save(queue_contents)

        return SynchronizationReport(
            created_count=created_count,
            duplicate_count=duplicate_count,
            rejected_count=rejected_count,
            remaining_count=len(self._load()["pending"]),
            connection_failed=connection_failed,
        )

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        if not self._queue_file_path.exists():
            return {"pending": [], "rejected": []}
        try:
            raw = self._queue_file_path.read_bytes()
            text = (self._encryptor.decrypt_bytes(raw) if self._encryptor else raw).decode("utf-8")
            data = json.loads(text)
            return {"pending": list(data["pending"]), "rejected": list(data["rejected"])}
        except (json.JSONDecodeError, KeyError, TypeError, UnicodeDecodeError, FieldDecryptionError) as error:
            raise OfflineQueueCorruptedError(f"Queue file {self._queue_file_path} is not a valid queue.") from error

    def _save(self, queue_contents: dict[str, list[dict[str, Any]]]) -> None:
        """Write to a temporary file first, then replace, so a crash can never leave a half-written queue."""
        self._queue_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_path = tempfile.mkstemp(dir=self._queue_file_path.parent, suffix=".tmp")
        try:
            payload = json.dumps(queue_contents).encode("utf-8")
            if self._encryptor:
                payload = self._encryptor.encrypt_bytes(payload)
            with os.fdopen(file_descriptor, "wb") as temporary_file:
                temporary_file.write(payload)
            os.replace(temporary_path, self._queue_file_path)
        except BaseException:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise
