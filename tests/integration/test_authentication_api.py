import pytest
from fastapi.testclient import TestClient

from astronaut_health_monitor.api.application import create_application
from astronaut_health_monitor.core.configuration import ApplicationSettings
from astronaut_health_monitor.core.field_encryption import generate_encryption_key
from astronaut_health_monitor.domain.enumerations import UserRole
from tests.conftest import TEST_PASSWORD, create_account, sign_in

PROTECTED_REQUESTS = [
    ("GET", "/health-indicators"),
    ("GET", "/health-status-rules"),
    ("GET", "/missions"),
    ("GET", "/astronauts"),
    ("GET", "/measurements?astronaut_id=1"),
    ("GET", "/measurements/1/assessment"),
    ("GET", "/astronauts/1/health-summary"),
    ("GET", "/auth/me"),
    ("GET", "/audit-log"),
    ("POST", "/missions"),
    ("POST", "/astronauts"),
    ("POST", "/measurements"),
    ("POST", "/measurements/batch"),
    ("POST", "/users"),
    ("POST", "/demo/sample-crew"),
]


@pytest.mark.parametrize(("method", "path"), PROTECTED_REQUESTS)
def test_every_protected_endpoint_refuses_anonymous_requests(raw_client: TestClient, method: str, path: str) -> None:
    response = raw_client.request(method, path, json={} if method == "POST" else None)
    assert response.status_code == 401, f"{method} {path} was reachable without signing in"


def test_public_endpoints_are_reachable_and_contain_no_health_data(raw_client: TestClient) -> None:
    assert raw_client.get("/health").status_code == 200
    assert raw_client.get("/").status_code == 200
    assert raw_client.get("/body-map.png").status_code == 200


def test_login_sets_a_protected_cookie_and_me_works(raw_client: TestClient) -> None:
    create_account(raw_client, "doc", UserRole.CLINICIAN)
    response = raw_client.post("/auth/login", json={"username": "doc", "password": TEST_PASSWORD})
    assert response.status_code == 200
    assert response.json() == {"username": "doc", "role": "clinician", "astronaut_id": None}
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "secure" not in cookie
    assert raw_client.get("/auth/me").json()["username"] == "doc"


def test_logout_ends_the_session_on_the_server(raw_client: TestClient) -> None:
    create_account(raw_client, "doc", UserRole.CLINICIAN)
    sign_in(raw_client, "doc")
    token = raw_client.cookies.get("astronaut_health_session")
    assert raw_client.post("/auth/logout").json() == {"signed_out": True}
    assert raw_client.get("/auth/me").status_code == 401
    raw_client.cookies.set("astronaut_health_session", token or "")  # an attacker who kept the old token
    assert raw_client.get("/auth/me").status_code == 401


def test_wrong_credentials_get_the_same_generic_error(raw_client: TestClient) -> None:
    create_account(raw_client, "doc", UserRole.CLINICIAN)
    wrong_password = raw_client.post("/auth/login", json={"username": "doc", "password": "wrong-passphrase-1"})
    unknown_user = raw_client.post("/auth/login", json={"username": "nobody", "password": TEST_PASSWORD})
    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json() == {"detail": "Invalid username or password."}
    assert "set-cookie" not in wrong_password.headers


def test_account_locks_after_five_wrong_passwords(raw_client: TestClient) -> None:
    create_account(raw_client, "doc", UserRole.CLINICIAN)
    for _ in range(5):
        assert (
            raw_client.post("/auth/login", json={"username": "doc", "password": "wrong-passphrase-1"}).status_code
            == 401
        )
    locked = raw_client.post("/auth/login", json={"username": "doc", "password": TEST_PASSWORD})
    assert locked.status_code == 429


def test_cookie_is_marked_secure_when_configured(test_settings: ApplicationSettings) -> None:
    settings = test_settings.model_copy(update={"secure_cookies": True})
    with TestClient(create_application("sqlite://", settings), base_url="https://testserver") as client:
        create_account(client, "doc", UserRole.CLINICIAN)
        response = client.post("/auth/login", json={"username": "doc", "password": TEST_PASSWORD})
        assert "secure" in response.headers["set-cookie"].lower()


def test_security_headers_and_cache_rules(api_client: TestClient) -> None:
    page = api_client.get("/")
    assert page.headers["x-content-type-options"] == "nosniff"
    assert page.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert "default-src 'self'" in page.headers["content-security-policy"]
    assert api_client.get("/astronauts").headers["cache-control"] == "no-store"


def test_cross_site_state_changing_requests_are_blocked(api_client: TestClient) -> None:
    hostile = api_client.post(
        "/astronauts",
        json={"full_name": "Mallory", "mission_role": "Intruder"},
        headers={"Origin": "https://evil.example"},
    )
    assert hostile.status_code == 403
    same_site = api_client.post(
        "/astronauts",
        json={"full_name": "Ada", "mission_role": "Pilot"},
        headers={"Origin": "http://testserver"},
    )
    assert same_site.status_code == 201


def test_demo_mode_creates_demo_accounts_for_every_role() -> None:
    settings = ApplicationSettings(encryption_key=generate_encryption_key(), demo_mode=True)
    with TestClient(create_application("sqlite://", settings)) as client:
        for username, role in (
            ("astronaut.demo", "astronaut"),
            ("clinician.demo", "clinician"),
            ("control.demo", "mission_control"),
        ):
            response = client.post("/auth/login", json={"username": username, "password": "Demo-Passphrase-2026!"})
            assert response.status_code == 200 and response.json()["role"] == role
        client.post("/auth/login", json={"username": "astronaut.demo", "password": "Demo-Passphrase-2026!"})
        own = client.get("/astronauts").json()
        assert len(own) == 1
        notes = {m["notes"] for m in client.get("/measurements", params={"astronaut_id": own[0]["id"]}).json()}
        assert notes == {"Simulated sample data"}


def test_demo_endpoint_is_unavailable_when_demo_mode_is_off(api_client: TestClient) -> None:
    assert api_client.post("/demo/sample-crew").status_code == 404
