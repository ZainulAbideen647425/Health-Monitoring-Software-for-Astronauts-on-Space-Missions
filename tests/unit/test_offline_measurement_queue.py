import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType
from astronaut_health_monitor.offline_synchronization.offline_measurement_queue import (
    OfflineMeasurementQueue,
    OfflineQueueCorruptedError,
)

MEASURED_AT = datetime(2026, 11, 1, 8, 0, tzinfo=UTC)


@pytest.fixture
def queue_file(tmp_path: Path) -> Path:
    return tmp_path / "queue" / "offline_queue.json"


@pytest.fixture
def queue(queue_file: Path) -> OfflineMeasurementQueue:
    return OfflineMeasurementQueue(queue_file)


def add_items(queue: OfflineMeasurementQueue, count: int) -> list[str]:
    return [
        queue.enqueue_measurement(1, HealthIndicatorType.HEART_RATE, 60 + index, MEASURED_AT) for index in range(count)
    ]


def reply_all(outcome: str) -> Callable[[list[dict[str, Any]]], dict[str, Any]]:
    def send(items: list[dict[str, Any]]) -> dict[str, Any]:
        return {"results": [{"index": i, "outcome": outcome, "rejection_reason": None} for i in range(len(items))]}

    return send


def test_enqueued_measurements_survive_a_restart(queue: OfflineMeasurementQueue, queue_file: Path) -> None:
    references = add_items(queue, 2)
    restarted_queue = OfflineMeasurementQueue(queue_file)
    pending = restarted_queue.pending_measurements()
    assert [item["client_reference"] for item in pending] == references
    assert len(set(references)) == 2
    assert pending[0]["measured_at"] == "2026-11-01T08:00:00+00:00"


def test_measurement_time_must_include_a_timezone(queue: OfflineMeasurementQueue) -> None:
    with pytest.raises(ValueError, match="timezone"):
        queue.enqueue_measurement(1, HealthIndicatorType.HEART_RATE, 60, datetime(2026, 11, 1, 8, 0))


def test_successful_synchronization_empties_the_queue(queue: OfflineMeasurementQueue) -> None:
    add_items(queue, 3)
    report = queue.synchronize(reply_all("created"))
    assert (report.created_count, report.remaining_count, report.connection_failed) == (3, 0, False)
    assert queue.pending_measurements() == []


def test_duplicates_count_as_delivered(queue: OfflineMeasurementQueue) -> None:
    add_items(queue, 2)
    report = queue.synchronize(reply_all("duplicate"))
    assert (report.duplicate_count, report.remaining_count) == (2, 0)


def test_lost_connection_keeps_everything_queued(queue: OfflineMeasurementQueue) -> None:
    add_items(queue, 3)

    def offline_sender(items: list[dict[str, Any]]) -> dict[str, Any]:
        raise ConnectionError("no link to Earth")

    report = queue.synchronize(offline_sender)
    assert report.connection_failed is True
    assert report.remaining_count == 3
    assert len(queue.pending_measurements()) == 3
    # connection returns later
    assert queue.synchronize(reply_all("created")).created_count == 3


def test_rejected_items_move_to_the_rejected_list_and_are_not_retried(queue: OfflineMeasurementQueue) -> None:
    add_items(queue, 3)

    def sender(items: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "results": [
                {"index": 0, "outcome": "created", "rejection_reason": None},
                {"index": 1, "outcome": "rejected", "rejection_reason": "Astronaut 99 does not exist."},
                {"index": 2, "outcome": "created", "rejection_reason": None},
            ]
        }

    report = queue.synchronize(sender)
    assert (report.created_count, report.rejected_count, report.remaining_count) == (2, 1, 0)
    rejected = queue.rejected_measurements()
    assert len(rejected) == 1
    assert rejected[0]["rejection_reason"] == "Astronaut 99 does not exist."
    assert queue.synchronize(reply_all("created")).created_count == 0


def test_large_queues_are_sent_in_batches(queue: OfflineMeasurementQueue) -> None:
    add_items(queue, 5)
    batch_sizes: list[int] = []

    def sender(items: list[dict[str, Any]]) -> dict[str, Any]:
        batch_sizes.append(len(items))
        return reply_all("created")(items)

    report = queue.synchronize(sender, batch_size=2)
    assert batch_sizes == [2, 2, 1]
    assert report.created_count == 5


def test_items_the_server_did_not_answer_stay_queued_and_loop_ends(queue: OfflineMeasurementQueue) -> None:
    add_items(queue, 2)
    calls = {"count": 0}

    def silent_sender(items: list[dict[str, Any]]) -> dict[str, Any]:
        calls["count"] += 1
        return {"results": []}

    report = queue.synchronize(silent_sender)
    assert calls["count"] == 1
    assert report.remaining_count == 2


def test_corrupted_queue_file_is_reported_clearly(queue: OfflineMeasurementQueue, queue_file: Path) -> None:
    queue_file.parent.mkdir(parents=True)
    queue_file.write_text("this is not json", encoding="utf-8")
    with pytest.raises(OfflineQueueCorruptedError):
        queue.pending_measurements()
    queue_file.write_text(json.dumps({"unexpected": []}), encoding="utf-8")
    with pytest.raises(OfflineQueueCorruptedError):
        queue.pending_measurements()


def test_failed_save_leaves_the_previous_queue_intact(
    queue: OfflineMeasurementQueue, queue_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    add_items(queue, 1)

    def broken_replace(source: str, destination: str) -> None:
        raise OSError("disk error")

    monkeypatch.setattr(os, "replace", broken_replace)
    with pytest.raises(OSError, match="disk error"):
        add_items(queue, 1)
    monkeypatch.undo()
    assert len(queue.pending_measurements()) == 1
    assert [path.name for path in queue_file.parent.iterdir()] == ["offline_queue.json"]  # no temporary files left
