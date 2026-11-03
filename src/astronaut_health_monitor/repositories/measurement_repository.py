"""Database access for health measurements."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from astronaut_health_monitor.repositories.database_records import MeasurementRecord


class MeasurementRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_measurement(
        self,
        astronaut_id: int,
        indicator_type: str,
        measured_value: float,
        measurement_unit: str,
        measured_at: datetime,
        measurement_source: str,
        device_id: int | None,
        notes: str | None,
    ) -> MeasurementRecord:
        record = MeasurementRecord(
            astronaut_id=astronaut_id,
            indicator_type=indicator_type,
            measured_value=measured_value,
            measurement_unit=measurement_unit,
            measured_at=measured_at,
            measurement_source=measurement_source,
            device_id=device_id,
            notes=notes,
        )
        self._session.add(record)
        self._session.commit()
        return record

    def list_measurements(
        self,
        astronaut_id: int,
        indicator_type: str | None = None,
        limit: int = 100,
    ) -> list[MeasurementRecord]:
        """Return the newest measurements first."""
        query = select(MeasurementRecord).where(MeasurementRecord.astronaut_id == astronaut_id)
        if indicator_type is not None:
            query = query.where(MeasurementRecord.indicator_type == indicator_type)
        query = query.order_by(MeasurementRecord.measured_at.desc(), MeasurementRecord.id.desc()).limit(limit)
        return list(self._session.scalars(query))
