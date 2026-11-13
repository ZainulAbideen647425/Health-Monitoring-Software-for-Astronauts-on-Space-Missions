"""FastAPI dependencies that build services for each request."""

from collections.abc import Callable, Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from astronaut_health_monitor.domain.authenticated_user import AuthenticatedUser
from astronaut_health_monitor.domain.enumerations import AuditOutcome
from astronaut_health_monitor.domain.exceptions import PermissionDeniedError
from astronaut_health_monitor.domain.permissions import Permission, has_permission
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.audit_repository import AuditRepository
from astronaut_health_monitor.repositories.device_repository import DeviceRepository
from astronaut_health_monitor.repositories.measurement_repository import MeasurementRepository
from astronaut_health_monitor.repositories.mission_repository import MissionRepository
from astronaut_health_monitor.repositories.user_repository import UserRepository
from astronaut_health_monitor.services.astronaut_service import AstronautService
from astronaut_health_monitor.services.audit_service import AuditService
from astronaut_health_monitor.services.authentication_service import AuthenticationService
from astronaut_health_monitor.services.health_assessment_service import HealthAssessmentService
from astronaut_health_monitor.services.measurement_batch_service import MeasurementBatchService
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


def get_measurement_batch_service(session: DatabaseSession) -> MeasurementBatchService:
    return MeasurementBatchService(get_measurement_service(session))


def get_health_assessment_service(session: DatabaseSession) -> HealthAssessmentService:
    return HealthAssessmentService(MeasurementRepository(session), AstronautRepository(session))


MissionServiceDependency = Annotated[MissionService, Depends(get_mission_service)]
AstronautServiceDependency = Annotated[AstronautService, Depends(get_astronaut_service)]
MeasurementServiceDependency = Annotated[MeasurementService, Depends(get_measurement_service)]
MeasurementBatchServiceDependency = Annotated[MeasurementBatchService, Depends(get_measurement_batch_service)]
HealthAssessmentServiceDependency = Annotated[HealthAssessmentService, Depends(get_health_assessment_service)]


SESSION_COOKIE_NAME = "astronaut_health_session"


def get_audit_service(session: DatabaseSession) -> AuditService:
    return AuditService(AuditRepository(session))


AuditServiceDependency = Annotated[AuditService, Depends(get_audit_service)]


def get_authentication_service(
    session: DatabaseSession, audit_service: AuditServiceDependency
) -> AuthenticationService:
    return AuthenticationService(UserRepository(session), AstronautRepository(session), audit_service)


AuthenticationServiceDependency = Annotated[AuthenticationService, Depends(get_authentication_service)]


def get_current_user(request: Request, authentication_service: AuthenticationServiceDependency) -> AuthenticatedUser:
    """The signed-in user, or a 401 response when there is no valid session."""
    return authentication_service.authenticate(request.cookies.get(SESSION_COOKIE_NAME))


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


def require_permission(permission: Permission) -> Callable[..., AuthenticatedUser]:
    """Build a dependency that only lets users with the permission through. Refusals are audited."""

    def check_permission(user: CurrentUser, audit_service: AuditServiceDependency) -> AuthenticatedUser:
        if not has_permission(user, permission):
            audit_service.record("access_denied", AuditOutcome.DENIED, user=user, target=permission.value)
            raise PermissionDeniedError("Your role does not allow this action.")
        return user

    return check_permission
