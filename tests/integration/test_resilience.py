"""Phase 5: the system must fail safely. Bad input, broken storage and a flaky link never cause a 500 or lost data."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType
from astronaut_health_monitor.offline_synchronization.offline_measurement_queue import (
    OfflineMeasurementQueue,
    OfflineQueueCorruptedError,
)
from astronaut_health_monitor.services.authentication_service import MAXIMUM_FAILED_LOGINS
from tests.conftest import TEST_PASSWORD


def when() -> str:
    return (datetime.now(UTC) - timedelta(minutes=5)).isoformat()


@pytest.fixture
def astronaut_id(api_client: TestClient) -> int:
    return int(api_client.post("/astronauts", json={"full_name": "Ada", "mission_role": "Pilot"}).json()["id"])


def body(astronaut_id: int, **changes: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "astronaut_id": astronaut_id,
        "indicator_type": "heart_rate",
        "measured_value": 70,
        "measured_at": when(),
    }
    data.update(changes)
    return data


@pytest.mark.parametrize(
    "changes",
    [
        {"indicator_type": "not_a_real_indicator"},
        {"measured_value": "seventy"},
        {"measured_value": 99999},
        {"measured_value": -5},
        {"measured_at": "yesterday"},
        {"measured_at": "2026-01-01T10:00:00"},  # no timezone
        {"notes": "x" * 501},
        {"client_reference": "short"},
    ],
)
def test_invalid_readings_are_refused_with_a_client_error_never_a_crash(
    api_client: TestClient, astronaut_id: int, changes: dict[str, Any]
) -> None:
    response = api_client.post("/measurements", json=body(astronaut_id, **changes))
    assert 400 <= response.status_code < 500


def test_non_json_and_wrong_shaped_bodies_are_refused(api_client: TestClient) -> None:
    assert (
        api_client.post("/measurements", content=b"{not json", headers={"Content-Type": "application/json"}).status_code
        == 422
    )
    assert api_client.post("/measurements", json=[1, 2, 3]).status_code == 422
    assert api_client.post("/measurements/batch", json={"measurements": "nope"}).status_code == 422


def test_unknown_records_return_404_not_500(api_client: TestClient) -> None:
    assert api_client.get("/measurements/999999/assessment").status_code == 404
    assert api_client.get("/astronauts/999999/health-summary").status_code == 404
    assert api_client.post("/measurements", json=body(999999)).status_code in (403, 404)


def test_repeated_submissions_with_one_client_reference_store_a_single_reading(
    api_client: TestClient, astronaut_id: int
) -> None:
    ids = {
        api_client.post("/measurements", json=body(astronaut_id, client_reference="retry-0001")).json()["id"]
        for _ in range(10)
    }
    assert len(ids) == 1
    stored = api_client.get(f"/measurements?astronaut_id={astronaut_id}").json()
    assert len(stored) == 1


def test_a_batch_with_good_and_bad_items_keeps_the_good_ones(api_client: TestClient, astronaut_id: int) -> None:
    items = [
        body(astronaut_id, client_reference="batch-good-1"),
        body(astronaut_id, indicator_type="nope", client_reference="batch-bad-01"),
        body(astronaut_id, measured_value=72, client_reference="batch-good-2"),
    ]
    reply = api_client.post("/measurements/batch", json={"measurements": items}).json()
    assert (reply["created_count"], reply["rejected_count"]) == (2, 1)


def test_account_locks_after_repeated_wrong_passwords_and_recovers_nothing_by_guessing(
    raw_client: TestClient,
) -> None:
    from astronaut_health_monitor.domain.enumerations import UserRole
    from tests.conftest import create_account

    create_account(raw_client, "lock.test", UserRole.CLINICIAN)
    for _ in range(MAXIMUM_FAILED_LOGINS):
        assert raw_client.post(
            "/auth/login", json={"username": "lock.test", "password": "wrong-Password1!"}
        ).status_code in (
            401,
            423,
            429,
        )
    locked = raw_client.post("/auth/login", json={"username": "lock.test", "password": TEST_PASSWORD})
    assert locked.status_code != 200


def test_requests_without_a_session_are_refused(raw_client: TestClient) -> None:
    for path in ("/astronauts", "/measurements?astronaut_id=1", "/audit-log"):
        assert raw_client.get(path).status_code == 401


def test_offline_queue_survives_a_dropped_connection_and_resumes(tmp_path: Path) -> None:
    queue = OfflineMeasurementQueue(tmp_path / "queue.json")
    for value in (70, 71, 72):
        queue.enqueue_measurement(1, HealthIndicatorType.HEART_RATE, value, datetime.now(UTC))

    def link_down(_batch: list[dict[str, Any]]) -> dict[str, Any]:
        raise ConnectionError("link lost")

    report = queue.synchronize(link_down)
    assert report.connection_failed and report.remaining_count == 3  # nothing lost

    def link_up(batch: list[dict[str, Any]]) -> dict[str, Any]:
        return {"results": [{"index": i, "outcome": "created"} for i in range(len(batch))]}

    report = queue.synchronize(link_up)
    assert report.created_count == 3 and report.remaining_count == 0


def test_a_half_answered_batch_keeps_the_unanswered_items(tmp_path: Path) -> None:
    queue = OfflineMeasurementQueue(tmp_path / "queue.json")
    for value in (70, 71):
        queue.enqueue_measurement(1, HealthIndicatorType.HEART_RATE, value, datetime.now(UTC))
    calls: list[int] = []

    def answers_only_the_first_item(batch: list[dict[str, Any]]) -> dict[str, Any]:
        calls.append(len(batch))
        if len(calls) > 1:
            raise ConnectionError("link lost")
        return {"results": [{"index": 0, "outcome": "created"}]}

    report = queue.synchronize(answers_only_the_first_item)
    assert report.created_count == 1 and report.remaining_count == 1


def test_a_damaged_queue_file_is_reported_not_silently_discarded(tmp_path: Path) -> None:
    path = tmp_path / "queue.json"
    path.write_bytes(b"\x00\x01 garbage")
    with pytest.raises(OfflineQueueCorruptedError):
        OfflineMeasurementQueue(path).pending_measurements()
    assert path.read_bytes() == b"\x00\x01 garbage"  # the evidence is kept for recovery
