"""Database access for the audit log."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from astronaut_health_monitor.repositories.database_records import AuditEventRecord


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_latest_event(self) -> AuditEventRecord | None:
        return self._session.scalar(select(AuditEventRecord).order_by(AuditEventRecord.id.desc()).limit(1))

    def add_event(self, event: AuditEventRecord) -> AuditEventRecord:
        self._session.add(event)
        self._session.commit()
        return event

    def list_events_newest_first(self, limit: int) -> list[AuditEventRecord]:
        return list(self._session.scalars(select(AuditEventRecord).order_by(AuditEventRecord.id.desc()).limit(limit)))

    def list_all_events_oldest_first(self) -> list[AuditEventRecord]:
        return list(self._session.scalars(select(AuditEventRecord).order_by(AuditEventRecord.id)))
