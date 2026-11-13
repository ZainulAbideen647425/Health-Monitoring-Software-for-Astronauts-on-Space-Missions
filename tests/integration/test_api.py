from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _iso(offset: timedelta = timedelta()) -> str:
    return (datetime.now(UTC) + offset).isoformat()


def _create_astronaut(client: TestClient) -> int:
    mission = client.post(
        "/missions",
        json={"mission_name": "Artemis Demo", "mission_environment": "lunar_base", "mission_start_time": _iso()},
    )
    assert mission.status_code == 201
    astronaut = client.post(
        "/astronauts",
        json={"full_name": "Demo Astronaut", "mission_role": "Commander", "mission_id": mission.json()["id"]},
    )
    assert astronaut.status_code == 201
    return int(astronaut.json()["id"])


def test_health_endpoint_reports_ok(api_client: TestClient) -> None:
    body = api_client.get("/health").json()
    assert body["status"] == "ok"
    assert body["database_reachable"] is True


def test_health_indicator_reference_lists_all_indicators(api_client: TestClient) -> None:
    body = api_client.get("/health-indicators").json()
    assert len(body) == 10
    assert {item["indicator_type"] for item in body} >= {"heart_rate", "blood_glucose", "mood_score"}


def test_missions_and_astronauts_can_be_created_and_listed(api_client: TestClient) -> None:
    astronaut_id = _create_astronaut(api_client)
    assert [a["id"] for a in api_client.get("/astronauts").json()] == [astronaut_id]
    assert api_client.get("/missions").json()[0]["mission_environment"] == "lunar_base"


def test_astronaut_with_unknown_mission_returns_404(api_client: TestClient) -> None:
    response = api_client.post("/astronauts", json={"full_name": "A", "mission_role": "B", "mission_id": 5})
    assert response.status_code == 404


def test_valid_measurement_is_stored_and_returned(api_client: TestClient) -> None:
    astronaut_id = _create_astronaut(api_client)
    created = api_client.post(
        "/measurements",
        json={
            "astronaut_id": astronaut_id,
            "indicator_type": "blood_glucose",
            "measured_value": 95,
            "measured_at": _iso(timedelta(minutes=-1)),
        },
    )
    assert created.status_code == 201
    assert created.json()["measurement_unit"] == "mg/dL"
    listed = api_client.get("/measurements", params={"astronaut_id": astronaut_id}).json()
    assert len(listed) == 1 and listed[0]["measured_value"] == 95


def test_implausible_value_is_rejected_with_422(api_client: TestClient) -> None:
    astronaut_id = _create_astronaut(api_client)
    response = api_client.post(
        "/measurements",
        json={
            "astronaut_id": astronaut_id,
            "indicator_type": "heart_rate",
            "measured_value": 7000,
            "measured_at": _iso(),
        },
    )
    assert response.status_code == 422


def test_unknown_indicator_type_is_rejected_with_422(api_client: TestClient) -> None:
    astronaut_id = _create_astronaut(api_client)
    response = api_client.post(
        "/measurements",
        json={"astronaut_id": astronaut_id, "indicator_type": "luck", "measured_value": 1, "measured_at": _iso()},
    )
    assert response.status_code == 422


def test_future_measurement_is_rejected_with_422(api_client: TestClient) -> None:
    astronaut_id = _create_astronaut(api_client)
    response = api_client.post(
        "/measurements",
        json={
            "astronaut_id": astronaut_id,
            "indicator_type": "heart_rate",
            "measured_value": 70,
            "measured_at": _iso(timedelta(days=1)),
        },
    )
    assert response.status_code == 422


def test_measurement_for_unknown_astronaut_returns_404(api_client: TestClient) -> None:
    response = api_client.post(
        "/measurements",
        json={"astronaut_id": 77, "indicator_type": "heart_rate", "measured_value": 70, "measured_at": _iso()},
    )
    assert response.status_code == 404
    assert api_client.get("/measurements", params={"astronaut_id": 77}).status_code == 404
