"""Database access for health measurements."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from astronaut_health_monitor.domain.exceptions import DuplicateMeasurementReferenceError
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
        client_reference: str | None = None,
    ) -> MeasurementRecord:
        """Store a measurement. Raises DuplicateMeasurementReferenceError if the client reference is already used."""
        record = MeasurementRecord(
            astronaut_id=astronaut_id,
            indicator_type=indicator_type,
            measured_value=measured_value,
            measurement_unit=measurement_unit,
            measured_at=measured_at,
            measurement_source=measurement_source,
            device_id=device_id,
            notes=notes,
            client_reference=client_reference,
        )
        self._session.add(record)
        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            raise DuplicateMeasurementReferenceError(
                f"A measurement with client reference {client_reference!r} already exists."
            ) from error
        return record

    def get_measurement_by_id(self, measurement_id: int) -> MeasurementRecord | None:
        return self._session.get(MeasurementRecord, measurement_id)

    def get_measurement_by_client_reference(self, client_reference: str) -> MeasurementRecord | None:
        return self._session.scalar(
            select(MeasurementRecord).where(MeasurementRecord.client_reference == client_reference)
        )

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

    def list_measurements_before(
        self, astronaut_id: int, indicator_type: str, measured_before: datetime, limit: int
    ) -> list[MeasurementRecord]:
        """Return up to `limit` measurements strictly earlier than the given time, newest first."""
        query = (
            select(MeasurementRecord)
            .where(
                MeasurementRecord.astronaut_id == astronaut_id,
                MeasurementRecord.indicator_type == indicator_type,
                MeasurementRecord.measured_at < measured_before,
            )
            .order_by(MeasurementRecord.measured_at.desc(), MeasurementRecord.id.desc())
            .limit(limit)
        )
        return list(self._session.scalars(query))

    def get_latest_measurement(self, astronaut_id: int, indicator_type: str) -> MeasurementRecord | None:
        records = self.list_measurements(astronaut_id, indicator_type, limit=1)
        return records[0] if records else None
