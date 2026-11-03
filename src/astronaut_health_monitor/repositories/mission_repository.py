"""Database access for missions."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from astronaut_health_monitor.repositories.database_records import MissionRecord


class MissionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_mission(self, mission_name: str, mission_environment: str, mission_start_time: datetime) -> MissionRecord:
        record = MissionRecord(
            mission_name=mission_name,
            mission_environment=mission_environment,
            mission_start_time=mission_start_time,
        )
        self._session.add(record)
        self._session.commit()
        return record

    def get_mission_by_id(self, mission_id: int) -> MissionRecord | None:
        return self._session.get(MissionRecord, mission_id)

    def get_mission_by_name(self, mission_name: str) -> MissionRecord | None:
        return self._session.scalar(select(MissionRecord).where(MissionRecord.mission_name == mission_name))

    def list_missions(self) -> list[MissionRecord]:
        return list(self._session.scalars(select(MissionRecord).order_by(MissionRecord.id)))
