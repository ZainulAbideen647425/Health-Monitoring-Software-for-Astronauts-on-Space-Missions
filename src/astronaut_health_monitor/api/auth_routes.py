"""Sign-in, sign-out, user management, the audit log and demo data."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from astronaut_health_monitor.api.dependencies import (
    SESSION_COOKIE_NAME,
    AstronautServiceDependency,
    AuditServiceDependency,
    AuthenticationServiceDependency,
    CurrentUser,
    MeasurementServiceDependency,
    require_permission,
)
from astronaut_health_monitor.api.schemas import (
    AstronautResponse,
    AuditEventResponse,
    AuditLogResponse,
    LoginRequest,
    UserCreateRequest,
    UserResponse,
)
from astronaut_health_monitor.domain.authenticated_user import AuthenticatedUser
from astronaut_health_monitor.domain.exceptions import DemoModeDisabledError
from astronaut_health_monitor.domain.permissions import Permission
from astronaut_health_monitor.services.authentication_service import SESSION_ABSOLUTE_LIFETIME
from astronaut_health_monitor.services.demo_data_service import DemoDataService

logger = logging.getLogger(__name__)
router = APIRouter()

UserManager = Annotated[AuthenticatedUser, Depends(require_permission(Permission.MANAGE_USERS))]
AuditLogViewer = Annotated[AuthenticatedUser, Depends(require_permission(Permission.VIEW_AUDIT_LOG))]
CrewManager = Annotated[AuthenticatedUser, Depends(require_permission(Permission.MANAGE_MISSIONS_AND_CREW))]


def _describe(user: AuthenticatedUser) -> UserResponse:
    return UserResponse(username=user.username, role=user.role, astronaut_id=user.astronaut_id)


@router.post("/auth/login", response_model=UserResponse, tags=["authentication"])
def sign_in(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    authentication_service: AuthenticationServiceDependency,
) -> UserResponse:
    """Check the username and password. On success a session cookie is set that scripts on the page cannot read."""
    token, user = authentication_service.login(credentials.username, credentials.password)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=int(SESSION_ABSOLUTE_LIFETIME.total_seconds()),
        httponly=True,
        samesite="strict",
        secure=request.app.state.settings.secure_cookies,
        path="/",
    )
    return _describe(user)


@router.post("/auth/logout", tags=["authentication"])
def sign_out(
    request: Request, response: Response, authentication_service: AuthenticationServiceDependency
) -> dict[str, bool]:
    """End the session on the server (it cannot be reused) and remove the cookie."""
    authentication_service.logout(request.cookies.get(SESSION_COOKIE_NAME))
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"signed_out": True}


@router.get("/auth/me", response_model=UserResponse, tags=["authentication"])
def describe_signed_in_user(user: CurrentUser) -> UserResponse:
    return _describe(user)


@router.post("/users", response_model=UserResponse, status_code=201, tags=["users"])
def create_user(
    request: UserCreateRequest,
    manager: UserManager,
    authentication_service: AuthenticationServiceDependency,
    audit_service: AuditServiceDependency,
) -> UserResponse:
    created = authentication_service.create_user(request.username, request.password, request.role, request.astronaut_id)
    audit_service.record("user.created", user=manager, target=f"user:{created.username}", detail=created.role)
    return UserResponse(username=created.username, role=request.role, astronaut_id=created.astronaut_id)


@router.get("/audit-log", response_model=AuditLogResponse, tags=["audit"])
def read_audit_log(
    viewer: AuditLogViewer,
    audit_service: AuditServiceDependency,
    limit: int = Query(default=100, ge=1, le=1000),
) -> AuditLogResponse:
    """The newest audit entries plus a check that the whole chain of hashes is intact."""
    verification = audit_service.verify_chain()
    return AuditLogResponse(
        chain_is_valid=verification.is_valid,
        checked_event_count=verification.checked_event_count,
        first_broken_event_id=verification.first_broken_event_id,
        events=[AuditEventResponse.model_validate(event) for event in audit_service.list_recent_events(limit)],
    )


@router.post("/demo/sample-crew", response_model=AstronautResponse, status_code=201, tags=["demo"])
def add_sample_crew_member(
    request: Request,
    manager: CrewManager,
    astronaut_service: AstronautServiceDependency,
    measurement_service: MeasurementServiceDependency,
    authentication_service: AuthenticationServiceDependency,
    audit_service: AuditServiceDependency,
) -> AstronautResponse:
    """Create a simulated astronaut with 14 days of readings. Only available when demo mode is on."""
    if not request.app.state.settings.demo_mode:
        raise DemoModeDisabledError("Demo mode is switched off.")
    astronaut = DemoDataService(
        astronaut_service, measurement_service, authentication_service
    ).seed_sample_crew_member()
    audit_service.record("demo.sample_crew_created", user=manager, target=f"astronaut:{astronaut.id}")
    return AstronautResponse.model_validate(astronaut)
