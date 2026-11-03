"""Shared test fixtures."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from astronaut_health_monitor.api.application import create_application


@pytest.fixture
def api_client() -> Iterator[TestClient]:
    """An API client backed by a fresh in-memory database."""
    with TestClient(create_application("sqlite://")) as client:
        yield client
