"""Business rules for missions."""

from datetime import datetime

from astronaut_health_monitor.domain.enumerations import MissionEnvironment
from astronaut_health_monitor.repositories.database_records import MissionRecord
from astronaut_health_monitor.repositories.mission_repository import MissionRepository


class MissionService:
    def __init__(self, mission_repository: MissionRepository) -> None:
        self._mission_repository = mission_repository

    def create_mission(
        self, mission_name: str, mission_environment: MissionEnvironment, mission_start_time: datetime
    ) -> MissionRecord:
        return self._mission_repository.add_mission(mission_name, mission_environment.value, mission_start_time)

    def list_missions(self) -> list[MissionRecord]:
        return self._mission_repository.list_missions()
