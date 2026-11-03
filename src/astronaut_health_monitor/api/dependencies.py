"""FastAPI dependencies that build services for each request."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.device_repository import DeviceRepository
from astronaut_health_monitor.repositories.measurement_repository import MeasurementRepository
from astronaut_health_monitor.repositories.mission_repository import MissionRepository
from astronaut_health_monitor.services.astronaut_service import AstronautService
from astronaut_health_monitor.services.measurement_service import MeasurementService
from astronaut_health_monitor.services.mission_service import MissionService


def get_database_session(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


DatabaseSession = Annotated[Session, Depends(get_database_session)]


def get_mission_service(session: DatabaseSession) -> MissionService:
    return MissionService(MissionRepository(session))


def get_astronaut_service(session: DatabaseSession) -> AstronautService:
    return AstronautService(AstronautRepository(session), MissionRepository(session))


def get_measurement_service(session: DatabaseSession) -> MeasurementService:
    return MeasurementService(MeasurementRepository(session), AstronautRepository(session), DeviceRepository(session))


MissionServiceDependency = Annotated[MissionService, Depends(get_mission_service)]
AstronautServiceDependency = Annotated[AstronautService, Depends(get_astronaut_service)]
MeasurementServiceDependency = Annotated[MeasurementService, Depends(get_measurement_service)]
