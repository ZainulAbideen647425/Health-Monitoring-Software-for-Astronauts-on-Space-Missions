"""HTTP endpoints for health data. Every endpoint except the page, its image and /health requires sign-in."""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import text

from astronaut_health_monitor import __version__
from astronaut_health_monitor.api.authorization import authorize_health_data_read, authorize_health_data_write
from astronaut_health_monitor.api.dependencies import (
    AstronautServiceDependency,
    AuditServiceDependency,
    CurrentUser,
    DatabaseSession,
    HealthAnalyticsServiceDependency,
    HealthAssessmentServiceDependency,
    MeasurementBatchServiceDependency,
    MeasurementServiceDependency,
    MissionServiceDependency,
    require_permission,
)
from astronaut_health_monitor.api.schemas import (
    ApplicationHealthResponse,
    AstronautCreateRequest,
    AstronautHealthSummaryResponse,
    AstronautResponse,
    HealthAnalyticsResponse,
    HealthAssessmentResponse,
    HealthIndicatorReferenceResponse,
    HealthStatusRuleResponse,
    MeasurementBatchItemResponse,
    MeasurementBatchRequest,
    MeasurementBatchResponse,
    MeasurementCreateRequest,
    MeasurementResponse,
    MissionCreateRequest,
    MissionResponse,
    QueuedMeasurementItem,
)
from astronaut_health_monitor.domain.authenticated_user import AuthenticatedUser
from astronaut_health_monitor.domain.enumerations import BatchItemOutcome, HealthIndicatorType
from astronaut_health_monitor.domain.health_indicator_reference import HEALTH_INDICATOR_REFERENCES
from astronaut_health_monitor.domain.health_status_rules import HEALTH_STATUS_RULES
from astronaut_health_monitor.domain.permissions import Permission, can_write_health_data_of, has_permission
from astronaut_health_monitor.services.measurement_batch_service import BatchMeasurementInput, InvalidBatchItem

logger = logging.getLogger(__name__)
router = APIRouter()

DASHBOARD_PAGE = Path(__file__).resolve().parent.parent / "web" / "index.html"
BODY_MAP_IMAGE = DASHBOARD_PAGE.parent / "body_map.png"
DASHBOARD_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; frame-ancestors 'none'"
    )
}

ManageCrewUser = Annotated[AuthenticatedUser, Depends(require_permission(Permission.MANAGE_MISSIONS_AND_CREW))]


@router.get("/body-map.png", include_in_schema=False)
def show_body_map_image() -> FileResponse:
    """The anatomy illustration used behind the clickable body map."""
    return FileResponse(BODY_MAP_IMAGE, media_type="image/png")


@router.get("/", include_in_schema=False)
def show_dashboard() -> FileResponse:
    """The dashboard page. It contains no health data; the data is loaded after sign-in."""
    return FileResponse(DASHBOARD_PAGE, media_type="text/html", headers=DASHBOARD_SECURITY_HEADERS)


@router.get("/health", response_model=ApplicationHealthResponse, tags=["application"])
def check_application_health(request: Request, session: DatabaseSession) -> ApplicationHealthResponse:
    """Report whether the application and its database are working. Public and reveals no health data."""
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
def list_health_indicators(_: CurrentUser) -> list[HealthIndicatorReferenceResponse]:
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


@router.get("/health-status-rules", response_model=list[HealthStatusRuleResponse], tags=["reference"])
def list_health_status_rules(_: CurrentUser) -> list[HealthStatusRuleResponse]:
    """The expected ranges, critical limits and sources used to judge each indicator."""
    return [
        HealthStatusRuleResponse(
            indicator_type=rule.indicator_type,
            unit=HEALTH_INDICATOR_REFERENCES[rule.indicator_type].unit,
            normal_minimum=rule.normal_minimum,
            normal_maximum=rule.normal_maximum,
            critical_below=rule.critical_below,
            critical_above=rule.critical_above,
            minimum_meaningful_change=rule.minimum_meaningful_change,
            measurement_conditions=rule.measurement_conditions,
            source_notes=rule.source_notes,
            source_urls=list(rule.source_urls),
        )
        for rule in HEALTH_STATUS_RULES.values()
    ]


@router.post("/missions", response_model=MissionResponse, status_code=201, tags=["missions"])
def create_mission(
    request: MissionCreateRequest,
    service: MissionServiceDependency,
    user: ManageCrewUser,
    audit_service: AuditServiceDependency,
) -> MissionResponse:
    mission = service.create_mission(request.mission_name, request.mission_environment, request.mission_start_time)
    audit_service.record("mission.created", user=user, target=f"mission:{mission.id}")
    return MissionResponse.model_validate(mission)


@router.get("/missions", response_model=list[MissionResponse], tags=["missions"])
def list_missions(_: CurrentUser, service: MissionServiceDependency) -> list[MissionResponse]:
    return [MissionResponse.model_validate(mission) for mission in service.list_missions()]


@router.post("/astronauts", response_model=AstronautResponse, status_code=201, tags=["astronauts"])
def register_astronaut(
    request: AstronautCreateRequest,
    service: AstronautServiceDependency,
    user: ManageCrewUser,
    audit_service: AuditServiceDependency,
) -> AstronautResponse:
    astronaut = service.register_astronaut(request.full_name, request.mission_role, request.mission_id)
    audit_service.record("astronaut.registered", user=user, target=f"astronaut:{astronaut.id}")
    return AstronautResponse.model_validate(astronaut)


@router.get("/astronauts", response_model=list[AstronautResponse], tags=["astronauts"])
def list_astronauts(user: CurrentUser, service: AstronautServiceDependency) -> list[AstronautResponse]:
    """Crew the user may see: everyone for clinicians and mission control, only themselves for astronauts."""
    astronauts = service.list_astronauts()
    if not has_permission(user, Permission.READ_ALL_HEALTH_DATA):
        astronauts = [astronaut for astronaut in astronauts if astronaut.id == user.astronaut_id]
    return [AstronautResponse.model_validate(astronaut) for astronaut in astronauts]


@router.post("/measurements", response_model=MeasurementResponse, status_code=201, tags=["measurements"])
def record_measurement(
    request: MeasurementCreateRequest,
    response: Response,
    user: CurrentUser,
    service: MeasurementServiceDependency,
    audit_service: AuditServiceDependency,
) -> MeasurementResponse:
    """Record one measurement. Returns 201 when stored, or 200 if the client reference was already stored."""
    authorize_health_data_write(user, request.astronaut_id, audit_service)
    measurement, was_created = service.record_measurement_idempotently(
        astronaut_id=request.astronaut_id,
        indicator_type=request.indicator_type,
        measured_value=request.measured_value,
        measured_at=request.measured_at,
        measurement_source=request.measurement_source,
        device_id=request.device_id,
        notes=request.notes,
        client_reference=request.client_reference,
    )
    if was_created:
        audit_service.record(
            "measurement.recorded",
            user=user,
            target=f"astronaut:{request.astronaut_id}",
            detail=request.indicator_type.value,
        )
    else:
        response.status_code = 200
    return MeasurementResponse.model_validate(measurement)


@router.post("/measurements/batch", response_model=MeasurementBatchResponse, tags=["offline synchronization"])
def record_measurement_batch(
    request: MeasurementBatchRequest,
    user: CurrentUser,
    service: MeasurementBatchServiceDependency,
    audit_service: AuditServiceDependency,
) -> MeasurementBatchResponse:
    """Store measurements collected while offline. Each item succeeds or fails on its own."""
    items: list[BatchMeasurementInput | InvalidBatchItem] = []
    for raw_item in request.measurements:
        raw_reference = raw_item.get("client_reference")
        known_reference = raw_reference if isinstance(raw_reference, str) else None
        try:
            parsed = QueuedMeasurementItem.model_validate(raw_item)
        except ValidationError as error:
            first_problem = error.errors()[0]
            location = ".".join(str(part) for part in first_problem["loc"])
            items.append(InvalidBatchItem(known_reference, f"Invalid field '{location}': {first_problem['msg']}"))
            continue
        if not can_write_health_data_of(user, parsed.astronaut_id):
            items.append(InvalidBatchItem(known_reference, "You may only record your own health data."))
            continue
        items.append(
            BatchMeasurementInput(
                astronaut_id=parsed.astronaut_id,
                indicator_type=parsed.indicator_type,
                measured_value=parsed.measured_value,
                measured_at=parsed.measured_at,
                measurement_source=parsed.measurement_source,
                device_id=parsed.device_id,
                notes=parsed.notes,
                client_reference=parsed.client_reference,
            )
        )
    results = service.record_batch(items)
    created = sum(1 for r in results if r.outcome is BatchItemOutcome.CREATED)
    duplicate = sum(1 for r in results if r.outcome is BatchItemOutcome.DUPLICATE)
    rejected = sum(1 for r in results if r.outcome is BatchItemOutcome.REJECTED)
    audit_service.record(
        "measurement.batch_recorded", user=user, detail=f"created={created} duplicate={duplicate} rejected={rejected}"
    )
    return MeasurementBatchResponse(
        created_count=created,
        duplicate_count=duplicate,
        rejected_count=rejected,
        results=[
            MeasurementBatchItemResponse(
                index=r.index,
                client_reference=r.client_reference,
                outcome=r.outcome,
                measurement_id=r.measurement_id,
                rejection_reason=r.rejection_reason,
            )
            for r in results
        ],
    )


@router.get("/measurements", response_model=list[MeasurementResponse], tags=["measurements"])
def list_measurements(
    user: CurrentUser,
    service: MeasurementServiceDependency,
    audit_service: AuditServiceDependency,
    astronaut_id: int,
    indicator_type: HealthIndicatorType | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[MeasurementResponse]:
    """Newest measurements first."""
    authorize_health_data_read(user, astronaut_id, audit_service)
    records = service.list_measurements(astronaut_id, indicator_type, limit)
    return [MeasurementResponse.model_validate(record) for record in records]


@router.get("/measurements/{measurement_id}/assessment", response_model=HealthAssessmentResponse, tags=["assessment"])
def assess_measurement(
    measurement_id: int,
    user: CurrentUser,
    service: HealthAssessmentServiceDependency,
    audit_service: AuditServiceDependency,
) -> HealthAssessmentResponse:
    """Judge one stored measurement: status, personal baseline, trend and guidance."""
    assessment = service.assess_measurement(measurement_id)
    authorize_health_data_read(user, assessment.astronaut_id, audit_service)
    return HealthAssessmentResponse.model_validate(assessment)


@router.get(
    "/astronauts/{astronaut_id}/health-summary", response_model=AstronautHealthSummaryResponse, tags=["assessment"]
)
def summarize_astronaut_health(
    astronaut_id: int,
    user: CurrentUser,
    service: HealthAssessmentServiceDependency,
    audit_service: AuditServiceDependency,
) -> AstronautHealthSummaryResponse:
    """Latest assessment of every indicator, with an overall status for the astronaut."""
    authorize_health_data_read(user, astronaut_id, audit_service)
    return AstronautHealthSummaryResponse.model_validate(service.summarize_astronaut_health(astronaut_id))


@router.get("/astronauts/{astronaut_id}/health-analytics", response_model=HealthAnalyticsResponse, tags=["analytics"])
def analyze_astronaut_health(
    astronaut_id: int,
    user: CurrentUser,
    service: HealthAnalyticsServiceDependency,
    audit_service: AuditServiceDependency,
) -> HealthAnalyticsResponse:
    """Machine-learning flags: unusual days and a three-day risk forecast, from this astronaut's own history."""
    authorize_health_data_read(user, astronaut_id, audit_service)
    return HealthAnalyticsResponse.model_validate(service.analyze_astronaut(astronaut_id))
