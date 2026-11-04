from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def create_astronaut(client: TestClient) -> int:
    response = client.post("/astronauts", json={"full_name": "Demo Astronaut", "mission_role": "Commander"})
    return int(response.json()["id"])


def record(client: TestClient, astronaut_id: int, indicator: str, value: float, days_ago: int) -> int:
    response = client.post(
        "/measurements",
        json={
            "astronaut_id": astronaut_id,
            "indicator_type": indicator,
            "measured_value": value,
            "measured_at": (datetime.now(UTC) - timedelta(days=days_ago, minutes=5)).isoformat(),
        },
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def test_health_status_rules_are_published_with_sources(api_client: TestClient) -> None:
    rules = api_client.get("/health-status-rules").json()
    assert len(rules) == 7
    heart_rate = next(rule for rule in rules if rule["indicator_type"] == "heart_rate")
    assert (heart_rate["normal_minimum"], heart_rate["normal_maximum"]) == (50, 100)
    assert heart_rate["unit"] == "beats per minute"
    assert heart_rate["source_notes"]
    assert all(rule["measurement_conditions"] for rule in rules)


def test_assessment_of_a_critical_measurement(api_client: TestClient) -> None:
    astronaut_id = create_astronaut(api_client)
    measurement_id = record(api_client, astronaut_id, "heart_rate", 135, days_ago=0)
    body = api_client.get(f"/measurements/{measurement_id}/assessment").json()
    assert body["final_status"] == "critical"
    assert body["contact_flight_surgeon"] is True
    assert body["value_direction"] == "above_expected_range"
    assert body["recommended_actions"][0].startswith("Contact the flight surgeon")
    assert body["personal_baseline"]["has_enough_history"] is False


def test_assessment_detects_personal_drift_even_when_value_is_in_normal_range(api_client: TestClient) -> None:
    astronaut_id = create_astronaut(api_client)
    for days_ago, value in zip(range(7, 1, -1), [60, 61, 60, 61, 60, 61], strict=True):
        record(api_client, astronaut_id, "heart_rate", value, days_ago)
    measurement_id = record(api_client, astronaut_id, "heart_rate", 82, days_ago=0)
    body = api_client.get(f"/measurements/{measurement_id}/assessment").json()
    assert body["rule_status"] == "normal"
    assert body["final_status"] == "caution"
    assert body["personal_baseline"]["is_unusual_for_this_astronaut"] is True


def test_unknown_measurement_assessment_returns_404(api_client: TestClient) -> None:
    assert api_client.get("/measurements/999/assessment").status_code == 404


def test_health_summary_combines_latest_readings(api_client: TestClient) -> None:
    astronaut_id = create_astronaut(api_client)
    record(api_client, astronaut_id, "heart_rate", 70, days_ago=0)
    record(api_client, astronaut_id, "sleep_duration", 5.5, days_ago=0)
    body = api_client.get(f"/astronauts/{astronaut_id}/health-summary").json()
    assert body["overall_status"] == "caution"
    assert body["contact_flight_surgeon"] is False
    assert {item["indicator_type"] for item in body["assessments"]} == {"heart_rate", "sleep_duration"}


def test_health_summary_for_unknown_astronaut_returns_404(api_client: TestClient) -> None:
    assert api_client.get("/astronauts/42/health-summary").status_code == 404
