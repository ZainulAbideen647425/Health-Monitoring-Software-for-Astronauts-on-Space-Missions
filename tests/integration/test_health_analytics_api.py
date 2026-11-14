from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from astronaut_health_monitor.api.application import create_application
from astronaut_health_monitor.core.configuration import ApplicationSettings


def make_astronaut(client: TestClient) -> int:
    return int(client.post("/astronauts", json={"full_name": "Ada", "mission_role": "Pilot"}).json()["id"])


def item(astronaut_id: int, indicator: str, value: float, moment: str, reference: str) -> dict[str, object]:
    return {
        "astronaut_id": astronaut_id,
        "indicator_type": indicator,
        "measured_value": value,
        "measured_at": moment,
        "client_reference": reference,
    }


def test_analytics_for_an_astronaut_without_readings_says_there_is_not_enough_data(api_client: TestClient) -> None:
    body = api_client.get(f"/astronauts/{make_astronaut(api_client)}/health-analytics").json()
    assert body["days_analyzed"] == 0
    assert not body["has_enough_data_for_unusual_days"] and not body["has_enough_data_for_forecast"]
    assert body["unusual_days"] == [] and body["forecasts"] == [] and "scikit-learn" in body["method"]


def test_analytics_flags_a_rising_heart_rate_and_an_unusual_day(api_client: TestClient) -> None:
    astronaut_id = make_astronaut(api_client)
    start = datetime.now(UTC) - timedelta(days=14)
    items = []
    for day in range(14):
        moment = (start + timedelta(days=day)).isoformat()
        items.append(
            {
                "astronaut_id": astronaut_id,
                "indicator_type": "heart_rate",
                "measured_value": 72 + 3 * day,
                "measured_at": moment,
                "client_reference": f"hr-{day:04d}-test",
            }
        )
        sleep = 3.0 if day == 7 else 8.0 + (day % 2) * 0.2
        items.append(
            {
                "astronaut_id": astronaut_id,
                "indicator_type": "sleep_duration",
                "measured_value": sleep,
                "measured_at": moment,
                "client_reference": f"sl-{day:04d}-test",
            }
        )
    assert api_client.post("/measurements/batch", json={"measurements": items}).json()["created_count"] == 28
    body = api_client.get(f"/astronauts/{astronaut_id}/health-analytics").json()
    assert body["days_analyzed"] == 14 and body["has_enough_data_for_unusual_days"]
    heart = next(item for item in body["forecasts"] if item["indicator_type"] == "heart_rate")
    assert heart["risk"] in ("watch", "high") and heart["projected_value"] > 100
    assert body["unusual_days"], "the three-hour sleep day should be flagged"


def test_analytics_needs_sign_in_and_unknown_astronauts_are_404(
    api_client: TestClient, test_settings: ApplicationSettings
) -> None:
    assert api_client.get("/astronauts/999999/health-analytics").status_code == 404
    with TestClient(create_application("sqlite://", test_settings)) as anonymous:
        assert anonymous.get("/astronauts/1/health-analytics").status_code == 401


def test_sample_data_differs_by_mission_environment(api_client: TestClient) -> None:
    from astronaut_health_monitor.domain.enumerations import HealthIndicatorType
    from astronaut_health_monitor.services.demo_data_service import _simulated_value

    stress = HealthIndicatorType.STRESS_LEVEL
    assert _simulated_value(3, stress, "mars") > _simulated_value(3, stress, "station")
    assert 1 <= _simulated_value(13, HealthIndicatorType.MOOD_SCORE, "mars") <= 10


def test_demo_endpoint_creates_a_named_sample_for_each_environment(test_settings: ApplicationSettings) -> None:
    from astronaut_health_monitor.services.demo_data_service import DEMO_PASSWORD

    settings = test_settings.model_copy(update={"demo_mode": True})
    with TestClient(create_application("sqlite://", settings)) as client:
        client.post("/auth/login", json={"username": "control.demo", "password": DEMO_PASSWORD})
        for key, suffix in (("mars", " (Mars base)"), ("station", "")):
            reply = client.post(f"/demo/sample-crew?environment={key}")
            assert reply.status_code == 201 and reply.json()["full_name"] == f"Demo Astronaut{suffix}"
        assert client.post("/demo/sample-crew?environment=venus").status_code == 422
