from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from astronaut_health_monitor.core.database import create_all_tables, create_database_engine, create_session_factory
from astronaut_health_monitor.domain.enumerations import DeviceKind, HealthIndicatorType, MeasurementSource
from astronaut_health_monitor.domain.exceptions import (
    AstronautNotFoundError,
    DeviceNotFoundError,
    ImplausibleMeasurementError,
    InvalidMeasurementTimeError,
)
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.device_repository import DeviceRepository
from astronaut_health_monitor.repositories.measurement_repository import MeasurementRepository
from astronaut_health_monitor.services.measurement_service import MeasurementService


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_database_engine("sqlite://")
    create_all_tables(engine)
    with create_session_factory(engine)() as database_session:
        yield database_session


@pytest.fixture
def service(session: Session) -> MeasurementService:
    return MeasurementService(MeasurementRepository(session), AstronautRepository(session), DeviceRepository(session))


@pytest.fixture
def astronaut_id(session: Session) -> int:
    return AstronautRepository(session).add_astronaut("Test Astronaut", "Flight Engineer", None).id


NOW = datetime.now(UTC)


def test_records_valid_measurement_and_fills_unit_from_reference(
    service: MeasurementService, astronaut_id: int
) -> None:
    record = service.record_measurement(
        astronaut_id, HealthIndicatorType.HEART_RATE, 64, NOW - timedelta(minutes=1), MeasurementSource.MANUAL_ENTRY
    )
    assert record.measurement_unit == "beats per minute"
    assert record.measured_at.tzinfo is not None


def test_rejects_unknown_astronaut(service: MeasurementService) -> None:
    with pytest.raises(AstronautNotFoundError):
        service.record_measurement(999, HealthIndicatorType.HEART_RATE, 64, NOW, MeasurementSource.MANUAL_ENTRY)


def test_rejects_unknown_device(service: MeasurementService, astronaut_id: int) -> None:
    with pytest.raises(DeviceNotFoundError):
        service.record_measurement(
            astronaut_id, HealthIndicatorType.HEART_RATE, 64, NOW, MeasurementSource.WEARABLE_DEVICE, device_id=42
        )


def test_accepts_known_device(service: MeasurementService, astronaut_id: int, session: Session) -> None:
    device = DeviceRepository(session).add_device("Wrist Sensor A", DeviceKind.WEARABLE_SENSOR.value)
    record = service.record_measurement(
        astronaut_id,
        HealthIndicatorType.HEART_RATE,
        64,
        NOW - timedelta(minutes=1),
        MeasurementSource.WEARABLE_DEVICE,
        device_id=device.id,
    )
    assert record.device_id == device.id


def test_rejects_implausible_value(service: MeasurementService, astronaut_id: int) -> None:
    with pytest.raises(ImplausibleMeasurementError):
        service.record_measurement(
            astronaut_id, HealthIndicatorType.HEART_RATE, 7000, NOW, MeasurementSource.MANUAL_ENTRY
        )


def test_rejects_future_timestamp(service: MeasurementService, astronaut_id: int) -> None:
    with pytest.raises(InvalidMeasurementTimeError):
        service.record_measurement(
            astronaut_id, HealthIndicatorType.HEART_RATE, 64, NOW + timedelta(hours=2), MeasurementSource.MANUAL_ENTRY
        )


def test_rejects_timestamp_without_timezone(service: MeasurementService, astronaut_id: int) -> None:
    with pytest.raises(InvalidMeasurementTimeError):
        service.record_measurement(
            astronaut_id, HealthIndicatorType.HEART_RATE, 64, datetime(2026, 1, 1), MeasurementSource.MANUAL_ENTRY
        )


def test_lists_newest_first_and_filters_by_indicator(service: MeasurementService, astronaut_id: int) -> None:
    older = NOW - timedelta(hours=2)
    newer = NOW - timedelta(hours=1)
    service.record_measurement(astronaut_id, HealthIndicatorType.HEART_RATE, 60, older, MeasurementSource.MANUAL_ENTRY)
    service.record_measurement(astronaut_id, HealthIndicatorType.HEART_RATE, 70, newer, MeasurementSource.MANUAL_ENTRY)
    service.record_measurement(astronaut_id, HealthIndicatorType.MOOD_SCORE, 8, newer, MeasurementSource.MANUAL_ENTRY)

    heart_rates = service.list_measurements(astronaut_id, HealthIndicatorType.HEART_RATE)
    assert [record.measured_value for record in heart_rates] == [70, 60]
    assert len(service.list_measurements(astronaut_id)) == 3


def test_listing_for_unknown_astronaut_fails(service: MeasurementService) -> None:
    with pytest.raises(AstronautNotFoundError):
        service.list_measurements(404)
