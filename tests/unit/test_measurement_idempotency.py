from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType, MeasurementSource
from astronaut_health_monitor.domain.exceptions import DuplicateMeasurementReferenceError
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.database_records import MeasurementRecord
from astronaut_health_monitor.repositories.device_repository import DeviceRepository
from astronaut_health_monitor.repositories.measurement_repository import MeasurementRepository
from astronaut_health_monitor.services.measurement_service import MeasurementService

REFERENCE = "0123456789abcdef"


@pytest.fixture
def astronaut_id(database_session: Session) -> int:
    return AstronautRepository(database_session).add_astronaut("Test Astronaut", "Medical Officer", None).id


@pytest.fixture
def service(database_session: Session) -> MeasurementService:
    return MeasurementService(
        MeasurementRepository(database_session),
        AstronautRepository(database_session),
        DeviceRepository(database_session),
    )


def record(
    service: MeasurementService, astronaut_id: int, client_reference: str | None
) -> tuple[MeasurementRecord, bool]:
    return service.record_measurement_idempotently(
        astronaut_id,
        HealthIndicatorType.HEART_RATE,
        64,
        datetime.now(UTC) - timedelta(minutes=1),
        MeasurementSource.MANUAL_ENTRY,
        client_reference=client_reference,
    )


def test_same_client_reference_creates_only_one_record(service: MeasurementService, astronaut_id: int) -> None:
    first, first_created = record(service, astronaut_id, REFERENCE)
    second, second_created = record(service, astronaut_id, REFERENCE)
    assert first_created is True
    assert second_created is False
    assert first.id == second.id


def test_measurements_without_client_reference_are_never_treated_as_duplicates(
    service: MeasurementService, astronaut_id: int
) -> None:
    first, _ = record(service, astronaut_id, None)
    second, second_created = record(service, astronaut_id, None)
    assert second_created is True
    assert first.id != second.id


def test_record_measurement_returns_the_stored_record_for_a_known_reference(
    service: MeasurementService, astronaut_id: int
) -> None:
    first, _ = record(service, astronaut_id, REFERENCE)
    again = service.record_measurement(
        astronaut_id,
        HealthIndicatorType.HEART_RATE,
        64,
        datetime.now(UTC),
        MeasurementSource.MANUAL_ENTRY,
        client_reference=REFERENCE,
    )
    assert again.id == first.id


def test_repository_rejects_a_duplicate_reference_and_stays_usable(
    database_session: Session, astronaut_id: int
) -> None:
    repository = MeasurementRepository(database_session)
    arguments = dict(
        astronaut_id=astronaut_id,
        indicator_type="heart_rate",
        measured_value=64.0,
        measurement_unit="beats per minute",
        measured_at=datetime.now(UTC),
        measurement_source="manual_entry",
        device_id=None,
        notes=None,
    )
    repository.add_measurement(**arguments, client_reference=REFERENCE)  # type: ignore[arg-type]
    with pytest.raises(DuplicateMeasurementReferenceError):
        repository.add_measurement(**arguments, client_reference=REFERENCE)  # type: ignore[arg-type]
    # the failed insert was rolled back, so the session still works
    assert repository.add_measurement(**arguments, client_reference="another-reference-1").id  # type: ignore[arg-type]


def test_service_recovers_when_another_request_wins_the_race(
    service: MeasurementService, astronaut_id: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    winner, _ = record(service, astronaut_id, REFERENCE)
    repository = service._measurement_repository  # noqa: SLF001
    real_lookup = repository.get_measurement_by_client_reference
    calls = {"count": 0}

    def lookup_that_misses_the_first_time(client_reference: str) -> MeasurementRecord | None:
        calls["count"] += 1
        return None if calls["count"] == 1 else real_lookup(client_reference)

    monkeypatch.setattr(repository, "get_measurement_by_client_reference", lookup_that_misses_the_first_time)
    result, was_created = record(service, astronaut_id, REFERENCE)
    assert was_created is False
    assert result.id == winner.id
