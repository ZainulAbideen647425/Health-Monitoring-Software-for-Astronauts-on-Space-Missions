from fastapi.testclient import TestClient

from astronaut_health_monitor.api.application import create_application
from astronaut_health_monitor.core.configuration import ApplicationSettings
from astronaut_health_monitor.domain.enumerations import UserRole
from tests.conftest import TEST_PASSWORD, create_account, sign_in

REGISTRATION = {"username": "New.Crew", "password": TEST_PASSWORD, "full_name": "Nora Crew", "mission_role": "Pilot"}


def test_registering_creates_an_astronaut_account_and_signs_in(raw_client: TestClient) -> None:
    response = raw_client.post("/auth/register", json=REGISTRATION)
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "new.crew"
    assert body["role"] == "astronaut"
    assert body["astronaut_id"] is not None
    assert raw_client.get("/auth/me").json()["username"] == "new.crew"


def test_a_registered_astronaut_sees_only_their_own_record(raw_client: TestClient) -> None:
    raw_client.post("/auth/register", json=REGISTRATION)
    names = [crew["full_name"] for crew in raw_client.get("/astronauts").json()]
    assert names == ["Nora Crew"]


def test_registered_account_can_sign_in_again_after_signing_out(raw_client: TestClient) -> None:
    raw_client.post("/auth/register", json=REGISTRATION)
    raw_client.post("/auth/logout")
    assert raw_client.get("/auth/me").status_code == 401
    sign_in(raw_client, "new.crew")
    assert raw_client.get("/auth/me").status_code == 200


def test_username_already_taken_is_refused_and_no_extra_crew_record_is_left(
    raw_client: TestClient, api_client: TestClient
) -> None:
    create_account(api_client, "taken.name", UserRole.CLINICIAN)
    before = len(api_client.get("/astronauts").json())
    anonymous = TestClient(api_client.app)
    response = anonymous.post("/auth/register", json={**REGISTRATION, "username": "taken.name"})
    assert response.status_code == 409
    assert len(api_client.get("/astronauts").json()) == before


def test_weak_password_and_bad_username_are_refused(raw_client: TestClient) -> None:
    assert raw_client.post("/auth/register", json={**REGISTRATION, "password": "short"}).status_code == 422
    assert raw_client.post("/auth/register", json={**REGISTRATION, "username": "no spaces!"}).status_code == 422
    assert raw_client.post("/auth/register", json={**REGISTRATION, "full_name": "   "}).status_code == 422


def test_registration_cannot_choose_a_role(raw_client: TestClient) -> None:
    response = raw_client.post("/auth/register", json={**REGISTRATION, "role": "mission_control"})
    assert response.status_code == 201
    assert response.json()["role"] == "astronaut"
    assert raw_client.get("/audit-log").status_code == 403


def test_registration_can_be_switched_off(test_settings: ApplicationSettings) -> None:
    settings = test_settings.model_copy(update={"allow_self_registration": False})
    with TestClient(create_application("sqlite://", settings)) as client:
        response = client.post("/auth/register", json=REGISTRATION)
    assert response.status_code == 403


def test_registration_is_recorded_in_the_audit_log(raw_client: TestClient, api_client: TestClient) -> None:
    TestClient(api_client.app).post("/auth/register", json=REGISTRATION)
    actions = [event["action"] for event in api_client.get("/audit-log").json()["events"]]
    assert "user.self_registered" in actions


def test_dashboard_offers_registration(raw_client: TestClient) -> None:
    page = raw_client.get("/").text
    assert 'id="showRegister"' in page
    assert 'id="registerBtn"' in page
