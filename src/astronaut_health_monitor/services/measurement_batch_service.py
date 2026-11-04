"""Stores many measurements at once, as sent by a device that was offline.

One bad item never blocks the others: every item gets its own result (created, duplicate or rejected).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from astronaut_health_monitor.domain.enumerations import BatchItemOutcome, HealthIndicatorType, MeasurementSource
from astronaut_health_monitor.domain.exceptions import AstronautHealthMonitorError
from astronaut_health_monitor.services.measurement_service import MeasurementService


@dataclass(frozen=True)
class BatchMeasurementInput:
    """A measurement whose shape has already been validated."""

    astronaut_id: int
    indicator_type: HealthIndicatorType
    measured_value: float
    measured_at: datetime
    measurement_source: MeasurementSource
    device_id: int | None
    notes: str | None
    client_reference: str


@dataclass(frozen=True)
class InvalidBatchItem:
    """An item whose shape was invalid, so it could not even be interpreted."""

    client_reference: str | None
    reason: str


@dataclass(frozen=True)
class BatchItemResult:
    index: int
    client_reference: str | None
    outcome: BatchItemOutcome
    measurement_id: int | None
    rejection_reason: str | None


class MeasurementBatchService:
    def __init__(self, measurement_service: MeasurementService) -> None:
        self._measurement_service = measurement_service

    def record_batch(self, items: Sequence[BatchMeasurementInput | InvalidBatchItem]) -> list[BatchItemResult]:
        results: list[BatchItemResult] = []
        for index, item in enumerate(items):
            if isinstance(item, InvalidBatchItem):
                results.append(
                    BatchItemResult(index, item.client_reference, BatchItemOutcome.REJECTED, None, item.reason)
                )
                continue
            try:
                record, was_created = self._measurement_service.record_measurement_idempotently(
                    astronaut_id=item.astronaut_id,
                    indicator_type=item.indicator_type,
                    measured_value=item.measured_value,
                    measured_at=item.measured_at,
                    measurement_source=item.measurement_source,
                    device_id=item.device_id,
                    notes=item.notes,
                    client_reference=item.client_reference,
                )
            except AstronautHealthMonitorError as error:
                results.append(
                    BatchItemResult(index, item.client_reference, BatchItemOutcome.REJECTED, None, str(error))
                )
                continue
            outcome = BatchItemOutcome.CREATED if was_created else BatchItemOutcome.DUPLICATE
            results.append(BatchItemResult(index, item.client_reference, outcome, record.id, None))
        return results
