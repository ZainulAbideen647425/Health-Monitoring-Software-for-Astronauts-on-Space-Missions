from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType
from astronaut_health_monitor.offline_synchronization.offline_measurement_queue import OfflineMeasurementQueue


def create_astronaut(client: TestClient) -> int:
    return int(client.post("/astronauts", json={"full_name": "Demo", "mission_role": "Pilot"}).json()["id"])


def sender_for(client: TestClient) -> Any:
    def send(items: list[dict[str, Any]]) -> dict[str, Any]:
        response = client.post("/measurements/batch", json={"measurements": items})
        assert response.status_code == 200
        return dict(response.json())

    return send


def test_offline_queue_end_to_end(api_client: TestClient, tmp_path: Path) -> None:
    astronaut_id = create_astronaut(api_client)
    queue = OfflineMeasurementQueue(tmp_path / "queue.json")
    measured_at = datetime.now(UTC) - timedelta(hours=3)
    for value in (62, 64, 66):
        queue.enqueue_measurement(astronaut_id, HealthIndicatorType.HEART_RATE, value, measured_at)
    queue.enqueue_measurement(astronaut_id, HealthIndicatorType.HEART_RATE, 7000, measured_at)  # impossible value

    # first attempt: no connection, nothing is lost
    def offline(_: list[dict[str, Any]]) -> dict[str, Any]:
        raise ConnectionError("no link")

    assert queue.synchronize(offline).remaining_count == 4

    # connection returns
    report = queue.synchronize(sender_for(api_client))
    assert (report.created_count, report.rejected_count, report.remaining_count) == (3, 1, 0)
    assert "outside the possible range" in queue.rejected_measurements()[0]["rejection_reason"]
    stored = api_client.get("/measurements", params={"astronaut_id": astronaut_id}).json()
    assert len(stored) == 3


def test_resending_the_same_items_never_creates_duplicates(api_client: TestClient, tmp_path: Path) -> None:
    astronaut_id = create_astronaut(api_client)
    queue = OfflineMeasurementQueue(tmp_path / "queue.json")
    queue.enqueue_measurement(
        astronaut_id, HealthIndicatorType.BLOOD_GLUCOSE, 90, datetime.now(UTC) - timedelta(hours=1)
    )
    items = queue.pending_measurements()
    send = sender_for(api_client)
    first = send(items)
    second = send(items)  # simulates a lost reply followed by a retry
    assert first["created_count"] == 1
    assert second["duplicate_count"] == 1
    assert len(api_client.get("/measurements", params={"astronaut_id": astronaut_id}).json()) == 1


def test_one_malformed_item_does_not_block_the_batch(api_client: TestClient) -> None:
    astronaut_id = create_astronaut(api_client)
    good = {
        "astronaut_id": astronaut_id,
        "indicator_type": "mood_score",
        "measured_value": 7,
        "measured_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
        "client_reference": "good-reference-001",
    }
    unknown_indicator = {**good, "indicator_type": "luck", "client_reference": "bad-reference-0001"}
    missing_reference = {key: value for key, value in good.items() if key != "client_reference"}
    body = api_client.post(
        "/measurements/batch", json={"measurements": [good, unknown_indicator, missing_reference]}
    ).json()
    assert (body["created_count"], body["rejected_count"]) == (1, 2)
    assert body["results"][1]["client_reference"] == "bad-reference-0001"
    assert "indicator_type" in body["results"][1]["rejection_reason"]
    assert body["results"][2]["client_reference"] is None


def test_empty_or_oversized_batches_are_refused(api_client: TestClient) -> None:
    assert api_client.post("/measurements/batch", json={"measurements": []}).status_code == 422
    assert api_client.post("/measurements/batch", json={"measurements": [{}] * 501}).status_code == 422


def test_single_post_with_repeated_client_reference_returns_200_and_same_record(api_client: TestClient) -> None:
    astronaut_id = create_astronaut(api_client)
    payload = {
        "astronaut_id": astronaut_id,
        "indicator_type": "body_temperature",
        "measured_value": 36.8,
        "measured_at": (datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        "client_reference": "temperature-ref-0001",
    }
    first = api_client.post("/measurements", json=payload)
    second = api_client.post("/measurements", json=payload)
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["id"] == second.json()["id"]
