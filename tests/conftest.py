"""Shared test fixtures."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from astronaut_health_monitor.api.application import create_application
from astronaut_health_monitor.core.configuration import ApplicationSettings
from astronaut_health_monitor.core.database import create_all_tables, create_database_engine, create_session_factory
from astronaut_health_monitor.core.field_encryption import (
    FieldEncryptor,
    configure_field_encryption,
    generate_encryption_key,
)
from astronaut_health_monitor.domain.enumerations import UserRole
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.audit_repository import AuditRepository
from astronaut_health_monitor.repositories.user_repository import UserRepository
from astronaut_health_monitor.services.audit_service import AuditService
from astronaut_health_monitor.services.authentication_service import AuthenticationService

TEST_PASSWORD = "a-long-test-passphrase"


@pytest.fixture(autouse=True)
def field_encryption() -> FieldEncryptor:
    """Every test gets a fresh encryption key, as an encrypted database column needs one."""
    encryptor = FieldEncryptor(generate_encryption_key().encode("ascii"))
    configure_field_encryption(encryptor)
    return encryptor


@pytest.fixture
def test_settings(field_encryption: FieldEncryptor) -> ApplicationSettings:
    return ApplicationSettings(encryption_key=generate_encryption_key(), demo_mode=False)


@pytest.fixture
def raw_client(test_settings: ApplicationSettings) -> Iterator[TestClient]:
    """An API client that has NOT signed in."""
    with TestClient(create_application("sqlite://", test_settings)) as client:
        yield client


def create_account(client: TestClient, username: str, role: UserRole, astronaut_id: int | None = None) -> None:
    """Create a user directly in the database of the client's application."""
    session = client.app.state.session_factory()  # type: ignore[attr-defined]
    try:
        audit_service = AuditService(AuditRepository(session))
        AuthenticationService(UserRepository(session), AstronautRepository(session), audit_service).create_user(
            username, TEST_PASSWORD, role, astronaut_id
        )
    finally:
        session.close()


def sign_in(client: TestClient, username: str) -> None:
    response = client.post("/auth/login", json={"username": username, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text


@pytest.fixture
def api_client(raw_client: TestClient) -> TestClient:
    """An API client signed in as mission control (every permission), for tests of the health features."""
    create_account(raw_client, "control.test", UserRole.MISSION_CONTROL)
    sign_in(raw_client, "control.test")
    return raw_client


@pytest.fixture
def database_session() -> Iterator[Session]:
    """A session on a fresh in-memory database, for tests that work below the API layer."""
    engine = create_database_engine("sqlite://")
    create_all_tables(engine)
    with create_session_factory(engine)() as session:
        yield session
