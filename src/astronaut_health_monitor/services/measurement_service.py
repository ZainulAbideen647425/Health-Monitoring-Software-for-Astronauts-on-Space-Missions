"""Business rules for recording and reading health measurements."""

from datetime import UTC, datetime, timedelta

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType, MeasurementSource
from astronaut_health_monitor.domain.exceptions import (
    AstronautNotFoundError,
    DeviceNotFoundError,
    ImplausibleMeasurementError,
    InvalidMeasurementTimeError,
)
from astronaut_health_monitor.domain.health_indicator_reference import get_health_indicator_reference
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.database_records import MeasurementRecord
from astronaut_health_monitor.repositories.device_repository import DeviceRepository
from astronaut_health_monitor.repositories.measurement_repository import MeasurementRepository

# Spacecraft device clocks can drift slightly, so a small amount of "future" time is tolerated.
ALLOWED_CLOCK_DRIFT = timedelta(minutes=5)


class MeasurementService:
    def __init__(
        self,
        measurement_repository: MeasurementRepository,
        astronaut_repository: AstronautRepository,
        device_repository: DeviceRepository,
    ) -> None:
        self._measurement_repository = measurement_repository
        self._astronaut_repository = astronaut_repository
        self._device_repository = device_repository

    def record_measurement(
        self,
        astronaut_id: int,
        indicator_type: HealthIndicatorType,
        measured_value: float,
        measured_at: datetime,
        measurement_source: MeasurementSource,
        device_id: int | None = None,
        notes: str | None = None,
    ) -> MeasurementRecord:
        if self._astronaut_repository.get_astronaut_by_id(astronaut_id) is None:
            raise AstronautNotFoundError(f"Astronaut {astronaut_id} does not exist.")
        if device_id is not None and self._device_repository.get_device_by_id(device_id) is None:
            raise DeviceNotFoundError(f"Device {device_id} does not exist.")

        reference = get_health_indicator_reference(indicator_type)
        if not reference.is_plausible(measured_value):
            raise ImplausibleMeasurementError(
                f"{reference.display_name} of {measured_value} {reference.unit} is outside the possible range "
                f"{reference.minimum_plausible_value} to {reference.maximum_plausible_value}."
            )
        if measured_at.tzinfo is None:
            raise InvalidMeasurementTimeError("Measurement time must include a timezone.")
        if measured_at > datetime.now(UTC) + ALLOWED_CLOCK_DRIFT:
            raise InvalidMeasurementTimeError("Measurement time is in the future.")

        return self._measurement_repository.add_measurement(
            astronaut_id=astronaut_id,
            indicator_type=indicator_type.value,
            measured_value=measured_value,
            measurement_unit=reference.unit,
            measured_at=measured_at,
            measurement_source=measurement_source.value,
            device_id=device_id,
            notes=notes,
        )

    def list_measurements(
        self, astronaut_id: int, indicator_type: HealthIndicatorType | None = None, limit: int = 100
    ) -> list[MeasurementRecord]:
        if self._astronaut_repository.get_astronaut_by_id(astronaut_id) is None:
            raise AstronautNotFoundError(f"Astronaut {astronaut_id} does not exist.")
        return self._measurement_repository.list_measurements(
            astronaut_id, indicator_type.value if indicator_type else None, limit
        )
