"""Shared test fixtures."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from astronaut_health_monitor.api.application import create_application
from astronaut_health_monitor.core.database import create_all_tables, create_database_engine, create_session_factory


@pytest.fixture
def api_client() -> Iterator[TestClient]:
    """An API client backed by a fresh in-memory database."""
    with TestClient(create_application("sqlite://")) as client:
        yield client


@pytest.fixture
def database_session() -> Iterator[Session]:
    """A session on a fresh in-memory database, for tests that work below the API layer."""
    engine = create_database_engine("sqlite://")
    create_all_tables(engine)
    with create_session_factory(engine)() as session:
        yield session
