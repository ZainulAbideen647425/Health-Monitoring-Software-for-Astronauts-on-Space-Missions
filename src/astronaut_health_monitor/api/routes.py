"""HTTP endpoints of the Astronaut Health Monitor."""

import logging

from fastapi import APIRouter, Query, Request
from sqlalchemy import text

from astronaut_health_monitor import __version__
from astronaut_health_monitor.api.dependencies import (
    AstronautServiceDependency,
    DatabaseSession,
    MeasurementServiceDependency,
    MissionServiceDependency,
)
from astronaut_health_monitor.api.schemas import (
    ApplicationHealthResponse,
    AstronautCreateRequest,
    AstronautResponse,
    HealthIndicatorReferenceResponse,
    MeasurementCreateRequest,
    MeasurementResponse,
    MissionCreateRequest,
    MissionResponse,
)
from astronaut_health_monitor.domain.enumerations import HealthIndicatorType
from astronaut_health_monitor.domain.health_indicator_reference import HEALTH_INDICATOR_REFERENCES

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=ApplicationHealthResponse, tags=["application"])
def check_application_health(request: Request, session: DatabaseSession) -> ApplicationHealthResponse:
    """Report whether the application and its database are working."""
    try:
        session.execute(text("SELECT 1"))
        database_reachable = True
    except Exception:  # noqa: BLE001 - health checks must never crash
        logger.exception("Database health check failed")
        database_reachable = False
    return ApplicationHealthResponse(
        status="ok" if database_reachable else "degraded",
        application_title=request.app.title,
        application_version=__version__,
        database_reachable=database_reachable,
    )


@router.get("/health-indicators", response_model=list[HealthIndicatorReferenceResponse], tags=["reference"])
def list_health_indicators() -> list[HealthIndicatorReferenceResponse]:
    """Explain every health indicator: unit, how to measure it, and why it matters in space."""
    return [
        HealthIndicatorReferenceResponse(
            indicator_type=reference.indicator_type,
            display_name=reference.display_name,
            unit=reference.unit,
            minimum_plausible_value=reference.minimum_plausible_value,
            maximum_plausible_value=reference.maximum_plausible_value,
            how_to_measure=reference.how_to_measure,
            why_it_matters_in_spaceflight=reference.why_it_matters_in_spaceflight,
        )
        for reference in HEALTH_INDICATOR_REFERENCES.values()
    ]


@router.post("/missions", response_model=MissionResponse, status_code=201, tags=["missions"])
def create_mission(request: MissionCreateRequest, service: MissionServiceDependency) -> MissionResponse:
    mission = service.create_mission(request.mission_name, request.mission_environment, request.mission_start_time)
    return MissionResponse.model_validate(mission)


@router.get("/missions", response_model=list[MissionResponse], tags=["missions"])
def list_missions(service: MissionServiceDependency) -> list[MissionResponse]:
    return [MissionResponse.model_validate(mission) for mission in service.list_missions()]


@router.post("/astronauts", response_model=AstronautResponse, status_code=201, tags=["astronauts"])
def register_astronaut(request: AstronautCreateRequest, service: AstronautServiceDependency) -> AstronautResponse:
    astronaut = service.register_astronaut(request.full_name, request.mission_role, request.mission_id)
    return AstronautResponse.model_validate(astronaut)


@router.get("/astronauts", response_model=list[AstronautResponse], tags=["astronauts"])
def list_astronauts(service: AstronautServiceDependency) -> list[AstronautResponse]:
    return [AstronautResponse.model_validate(astronaut) for astronaut in service.list_astronauts()]


@router.post("/measurements", response_model=MeasurementResponse, status_code=201, tags=["measurements"])
def record_measurement(request: MeasurementCreateRequest, service: MeasurementServiceDependency) -> MeasurementResponse:
    measurement = service.record_measurement(
        astronaut_id=request.astronaut_id,
        indicator_type=request.indicator_type,
        measured_value=request.measured_value,
        measured_at=request.measured_at,
        measurement_source=request.measurement_source,
        device_id=request.device_id,
        notes=request.notes,
    )
    return MeasurementResponse.model_validate(measurement)


@router.get("/measurements", response_model=list[MeasurementResponse], tags=["measurements"])
def list_measurements(
    service: MeasurementServiceDependency,
    astronaut_id: int,
    indicator_type: HealthIndicatorType | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[MeasurementResponse]:
    """Newest measurements first."""
    records = service.list_measurements(astronaut_id, indicator_type, limit)
    return [MeasurementResponse.model_validate(record) for record in records]
