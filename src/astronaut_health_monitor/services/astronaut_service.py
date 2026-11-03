"""Business rules for astronauts."""

from astronaut_health_monitor.domain.exceptions import AstronautNotFoundError, MissionNotFoundError
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.database_records import AstronautRecord
from astronaut_health_monitor.repositories.mission_repository import MissionRepository


class AstronautService:
    def __init__(self, astronaut_repository: AstronautRepository, mission_repository: MissionRepository) -> None:
        self._astronaut_repository = astronaut_repository
        self._mission_repository = mission_repository

    def register_astronaut(self, full_name: str, mission_role: str, mission_id: int | None) -> AstronautRecord:
        if mission_id is not None and self._mission_repository.get_mission_by_id(mission_id) is None:
            raise MissionNotFoundError(f"Mission {mission_id} does not exist.")
        return self._astronaut_repository.add_astronaut(full_name, mission_role, mission_id)

    def get_astronaut(self, astronaut_id: int) -> AstronautRecord:
        astronaut = self._astronaut_repository.get_astronaut_by_id(astronaut_id)
        if astronaut is None:
            raise AstronautNotFoundError(f"Astronaut {astronaut_id} does not exist.")
        return astronaut

    def list_astronauts(self) -> list[AstronautRecord]:
        return self._astronaut_repository.list_astronauts()
