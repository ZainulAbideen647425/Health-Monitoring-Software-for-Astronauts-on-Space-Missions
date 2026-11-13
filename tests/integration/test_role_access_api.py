from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from astronaut_health_monitor.domain.enumerations import UserRole
from tests.conftest import create_account, sign_in


def reading(astronaut_id: int, value: float = 70, reference: str | None = None) -> dict[str, object]:
    body: dict[str, object] = {
        "astronaut_id": astronaut_id,
        "indicator_type": "heart_rate",
        "measured_value": value,
        "measured_at": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
    }
    if reference:
        body["client_reference"] = reference
    return body


@pytest.fixture
def crew(api_client: TestClient) -> dict[str, Any]:
    """Two astronauts, each with one reading, and one signed-in client per role (separate cookie jars)."""
    ada = api_client.post("/astronauts", json={"full_name": "Ada", "mission_role": "Pilot"}).json()["id"]
    ben = api_client.post("/astronauts", json={"full_name": "Ben", "mission_role": "Engineer"}).json()["id"]
    ada_reading = api_client.post("/measurements", json=reading(ada)).json()["id"]
    ben_reading = api_client.post("/measurements", json=reading(ben, 65)).json()["id"]
    create_account(api_client, "ada", UserRole.ASTRONAUT, ada)
    create_account(api_client, "doc", UserRole.CLINICIAN)
    clients: dict[str, Any] = {
        "control": api_client,
        "ada_id": ada,
        "ben_id": ben,
        "ben_reading": ben_reading,
        "ada_reading": ada_reading,
    }
    for name in ("ada", "doc"):
        separate = TestClient(api_client.app)
        sign_in(separate, name)
        clients[name] = separate
    return clients


def test_astronaut_sees_only_their_own_crew_record_and_data(crew: dict[str, Any]) -> None:
    ada: TestClient = crew["ada"]
    assert [a["full_name"] for a in ada.get("/astronauts").json()] == ["Ada"]
    assert ada.get(f"/astronauts/{crew['ada_id']}/health-summary").status_code == 200
    assert len(ada.get("/measurements", params={"astronaut_id": crew["ada_id"]}).json()) == 1
    assert ada.get(f"/measurements/{crew['ada_reading']}/assessment").status_code == 200


def test_astronaut_cannot_read_another_astronauts_data_by_any_route(crew: dict[str, Any]) -> None:
    ada: TestClient = crew["ada"]
    ben = crew["ben_id"]
    assert ada.get(f"/astronauts/{ben}/health-summary").status_code == 403
    assert ada.get("/measurements", params={"astronaut_id": ben}).status_code == 403
    assert ada.get(f"/measurements/{crew['ben_reading']}/assessment").status_code == 403


def test_astronaut_can_only_write_their_own_data(crew: dict[str, Any]) -> None:
    ada: TestClient = crew["ada"]
    assert ada.post("/measurements", json=reading(crew["ada_id"], 68)).status_code == 201
    assert ada.post("/measurements", json=reading(crew["ben_id"], 68)).status_code == 403


def test_batch_rejects_items_for_other_astronauts_but_keeps_the_rest(crew: dict[str, Any]) -> None:
    ada: TestClient = crew["ada"]
    body = ada.post(
        "/measurements/batch",
        json={
            "measurements": [
                reading(crew["ada_id"], 66, "reference-own-1"),
                reading(crew["ben_id"], 66, "reference-other-1"),
            ]
        },
    ).json()
    assert (body["created_count"], body["rejected_count"]) == (1, 1)
    assert "only record your own" in body["results"][1]["rejection_reason"]


def test_astronaut_cannot_use_administrative_endpoints(crew: dict[str, Any]) -> None:
    ada: TestClient = crew["ada"]
    mission = {
        "mission_name": "M",
        "mission_environment": "spacecraft",
        "mission_start_time": datetime.now(UTC).isoformat(),
    }
    assert ada.post("/missions", json=mission).status_code == 403
    assert ada.post("/astronauts", json={"full_name": "X", "mission_role": "Y"}).status_code == 403
    assert (
        ada.post(
            "/users", json={"username": "evil.user", "password": "a-long-test-passphrase", "role": "mission_control"}
        ).status_code
        == 403
    )
    assert ada.get("/audit-log").status_code == 403


def test_clinician_reads_and_writes_all_crew_data_but_cannot_administer(crew: dict[str, Any]) -> None:
    doc: TestClient = crew["doc"]
    assert len(doc.get("/astronauts").json()) == 2
    assert doc.get(f"/astronauts/{crew['ben_id']}/health-summary").status_code == 200
    assert doc.post("/measurements", json=reading(crew["ben_id"], 72)).status_code == 201
    assert doc.post("/astronauts", json={"full_name": "X", "mission_role": "Y"}).status_code == 403
    assert (
        doc.post(
            "/users", json={"username": "evil.user", "password": "a-long-test-passphrase", "role": "mission_control"}
        ).status_code
        == 403
    )
    assert doc.get("/audit-log").status_code == 403


def test_mission_control_can_create_users_and_new_accounts_work(crew: dict[str, Any]) -> None:
    control: TestClient = crew["control"]
    created = control.post(
        "/users", json={"username": "new.doc", "password": "another-long-passphrase", "role": "clinician"}
    )
    assert created.status_code == 201 and created.json()["role"] == "clinician"
    assert (
        control.post(
            "/users", json={"username": "new.doc", "password": "another-long-passphrase", "role": "clinician"}
        ).status_code
        == 409
    )
    assert (
        control.post("/users", json={"username": "weak.one", "password": "short", "role": "clinician"}).status_code
        == 422
    )
    fresh = TestClient(control.app)
    assert (
        fresh.post("/auth/login", json={"username": "new.doc", "password": "another-long-passphrase"}).status_code
        == 200
    )


def test_audit_log_records_who_did_what_without_health_values(crew: dict[str, Any]) -> None:
    control: TestClient = crew["control"]
    ada: TestClient = crew["ada"]
    doc: TestClient = crew["doc"]
    ada.get(f"/astronauts/{crew['ben_id']}/health-summary")  # denied
    doc.get(f"/astronauts/{crew['ben_id']}/health-summary")  # permitted cross-read
    doc.post("/measurements", json=reading(crew["ben_id"], 83.5))
    log = control.get("/audit-log").json()
    assert log["chain_is_valid"] is True
    actions = {(e["username"], e["action"], e["outcome"]) for e in log["events"]}
    assert ("ada", "health_data.read", "denied") in actions
    assert ("doc", "health_data.viewed", "success") in actions
    assert ("doc", "measurement.recorded", "success") in actions
    assert ("ada", "login", "success") in actions
    assert "83.5" not in str(log["events"])


def test_sensitive_values_are_encrypted_in_the_database_file(crew: dict[str, Any]) -> None:
    control: TestClient = crew["control"]
    control.post("/measurements", json={**reading(crew["ada_id"], 123.5), "notes": "very private note"})
    session = control.app.state.session_factory()  # type: ignore[attr-defined]
    try:
        rows = session.execute(text("SELECT measured_value, notes FROM measurements")).all()
        names = session.execute(text("SELECT full_name FROM astronauts")).scalars().all()
        password_hashes = session.execute(text("SELECT password_hash FROM users")).scalars().all()
    finally:
        session.close()
    flat = " ".join(str(part) for row in rows for part in row) + " ".join(names)
    assert "123.5" not in flat and "very private note" not in flat and "Ada" not in flat
    assert all(h.startswith("scrypt$") and "a-long-test-passphrase" not in h for h in password_hashes)
