"""Database access for astronauts."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from astronaut_health_monitor.repositories.database_records import AstronautRecord


class AstronautRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_astronaut(self, full_name: str, mission_role: str, mission_id: int | None) -> AstronautRecord:
        record = AstronautRecord(full_name=full_name, mission_role=mission_role, mission_id=mission_id)
        self._session.add(record)
        self._session.commit()
        return record

    def get_astronaut_by_id(self, astronaut_id: int) -> AstronautRecord | None:
        return self._session.get(AstronautRecord, astronaut_id)

    def list_astronauts(self) -> list[AstronautRecord]:
        return list(self._session.scalars(select(AstronautRecord).order_by(AstronautRecord.id)))
