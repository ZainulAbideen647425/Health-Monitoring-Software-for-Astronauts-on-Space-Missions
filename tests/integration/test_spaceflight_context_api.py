from fastapi.testclient import TestClient

from astronaut_health_monitor.api.application import create_application
from astronaut_health_monitor.core.configuration import ApplicationSettings


def test_spaceflight_context_lists_indicators_environments_and_sources(api_client: TestClient) -> None:
    body = api_client.get("/spaceflight-context").json()
    assert len(body["indicators"]) == 10 and len(body["environments"]) == 5
    heart = next(item for item in body["indicators"] if item["indicator_type"] == "heart_rate")
    assert heart["source"]["url"] == "https://www.nasa.gov/hrp/hazards" and heart["hazard_names"]
    mars = next(item for item in body["environments"] if item["key"] == "mars")
    assert len(mars["hazards"]) == 5 and {"High", "Moderate"} & {h["level_word"] for h in mars["hazards"]}
    assert "dosimeters" in body["radiation_note"] and "orientation" in body["disclaimer"]


def test_spaceflight_context_needs_sign_in(test_settings: ApplicationSettings) -> None:
    with TestClient(create_application("sqlite://", test_settings)) as anonymous:
        assert anonymous.get("/spaceflight-context").status_code == 401
