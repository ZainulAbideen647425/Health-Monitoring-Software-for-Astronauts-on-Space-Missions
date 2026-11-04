from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from astronaut_health_monitor.domain.enumerations import BatchItemOutcome, HealthIndicatorType, MeasurementSource
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.device_repository import DeviceRepository
from astronaut_health_monitor.repositories.measurement_repository import MeasurementRepository
from astronaut_health_monitor.services.measurement_batch_service import (
    BatchMeasurementInput,
    InvalidBatchItem,
    MeasurementBatchService,
)
from astronaut_health_monitor.services.measurement_service import MeasurementService


@pytest.fixture
def batch_service(database_session: Session) -> MeasurementBatchService:
    return MeasurementBatchService(
        MeasurementService(
            MeasurementRepository(database_session),
            AstronautRepository(database_session),
            DeviceRepository(database_session),
        )
    )


@pytest.fixture
def astronaut_id(database_session: Session) -> int:
    return AstronautRepository(database_session).add_astronaut("Test Astronaut", "Pilot", None).id


def item(astronaut_id: int, reference: str, value: float = 64) -> BatchMeasurementInput:
    return BatchMeasurementInput(
        astronaut_id=astronaut_id,
        indicator_type=HealthIndicatorType.HEART_RATE,
        measured_value=value,
        measured_at=datetime.now(UTC) - timedelta(minutes=2),
        measurement_source=MeasurementSource.MANUAL_ENTRY,
        device_id=None,
        notes=None,
        client_reference=reference,
    )


def test_each_item_gets_its_own_outcome(batch_service: MeasurementBatchService, astronaut_id: int) -> None:
    results = batch_service.record_batch(
        [
            item(astronaut_id, "reference-000001"),
            item(astronaut_id, "reference-000001"),  # same reference again: duplicate
            item(999, "reference-000002"),  # unknown astronaut: rejected
            item(astronaut_id, "reference-000003", value=7000),  # impossible value: rejected
            InvalidBatchItem("reference-000004", "Invalid field 'indicator_type': bad value"),
        ]
    )
    assert [r.outcome for r in results] == [
        BatchItemOutcome.CREATED,
        BatchItemOutcome.DUPLICATE,
        BatchItemOutcome.REJECTED,
        BatchItemOutcome.REJECTED,
        BatchItemOutcome.REJECTED,
    ]
    assert results[0].measurement_id == results[1].measurement_id
    assert "does not exist" in (results[2].rejection_reason or "")
    assert "outside the possible range" in (results[3].rejection_reason or "")
    assert results[4].client_reference == "reference-000004"
    assert [r.index for r in results] == [0, 1, 2, 3, 4]
