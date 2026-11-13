"""Builds the FastAPI application."""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from astronaut_health_monitor import __version__
from astronaut_health_monitor.api.auth_routes import router as auth_router
from astronaut_health_monitor.api.routes import router
from astronaut_health_monitor.core.configuration import ApplicationSettings, get_application_settings
from astronaut_health_monitor.core.database import create_all_tables, create_database_engine, create_session_factory
from astronaut_health_monitor.core.field_encryption import (
    FieldEncryptor,
    configure_field_encryption,
    load_or_create_encryption_key,
)
from astronaut_health_monitor.domain.exceptions import (
    AccountLockedError,
    AstronautNotFoundError,
    AuthenticationFailedError,
    AuthenticationRequiredError,
    DemoModeDisabledError,
    DeviceNotFoundError,
    ImplausibleMeasurementError,
    InvalidMeasurementTimeError,
    InvalidUserDetailsError,
    MeasurementNotFoundError,
    MissionNotFoundError,
    PermissionDeniedError,
    RegistrationDisabledError,
    UserAlreadyExistsError,
)
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.audit_repository import AuditRepository
from astronaut_health_monitor.repositories.device_repository import DeviceRepository
from astronaut_health_monitor.repositories.measurement_repository import MeasurementRepository
from astronaut_health_monitor.repositories.mission_repository import MissionRepository
from astronaut_health_monitor.repositories.user_repository import UserRepository
from astronaut_health_monitor.services.astronaut_service import AstronautService
from astronaut_health_monitor.services.audit_service import AuditService
from astronaut_health_monitor.services.authentication_service import AuthenticationService
from astronaut_health_monitor.services.demo_data_service import DemoDataService
from astronaut_health_monitor.services.measurement_service import MeasurementService

logger = logging.getLogger(__name__)

STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _error_response(status_code: int, error: Exception) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": str(error)})


def _seed_demo_environment_if_empty(application: FastAPI) -> None:
    session = application.state.session_factory()
    try:
        user_repository = UserRepository(session)
        if user_repository.list_users():
            return
        astronaut_repository = AstronautRepository(session)
        audit_service = AuditService(AuditRepository(session))
        DemoDataService(
            AstronautService(astronaut_repository, MissionRepository(session)),
            MeasurementService(MeasurementRepository(session), astronaut_repository, DeviceRepository(session)),
            AuthenticationService(user_repository, astronaut_repository, audit_service),
        ).seed_demo_environment()
        logger.warning(
            "DEMO MODE: demo accounts with a public password were created. Never use real data in demo mode."
        )
    finally:
        session.close()


def create_application(database_url: str | None = None, settings: ApplicationSettings | None = None) -> FastAPI:
    """Create the application. Tests pass an in-memory database URL and their own settings."""
    settings = settings or get_application_settings()
    key = load_or_create_encryption_key(settings.encryption_key, Path(settings.encryption_key_file))
    configure_field_encryption(FieldEncryptor(key))
    engine = create_database_engine(database_url or settings.database_url)
    create_all_tables(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    application = FastAPI(title=settings.application_title, version=__version__, lifespan=lifespan)
    application.state.session_factory = create_session_factory(engine)
    application.state.settings = settings
    application.include_router(router)
    application.include_router(auth_router)

    @application.middleware("http")
    async def protect_requests(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.method in STATE_CHANGING_METHODS:
            origin = request.headers.get("origin")
            if origin and urlparse(origin).netloc != request.headers.get("host", ""):
                return JSONResponse(status_code=403, content={"detail": "Cross-site request blocked."})
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if response.headers.get("content-type", "").startswith("application/json"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(MissionNotFoundError)
    @application.exception_handler(MeasurementNotFoundError)
    @application.exception_handler(AstronautNotFoundError)
    @application.exception_handler(DeviceNotFoundError)
    @application.exception_handler(DemoModeDisabledError)
    async def handle_not_found(_: Request, error: Exception) -> JSONResponse:
        return _error_response(404, error)

    @application.exception_handler(ImplausibleMeasurementError)
    @application.exception_handler(InvalidMeasurementTimeError)
    @application.exception_handler(InvalidUserDetailsError)
    async def handle_invalid_input(_: Request, error: Exception) -> JSONResponse:
        return _error_response(422, error)

    @application.exception_handler(AuthenticationRequiredError)
    @application.exception_handler(AuthenticationFailedError)
    async def handle_not_signed_in(_: Request, error: Exception) -> JSONResponse:
        return _error_response(401, error)

    @application.exception_handler(PermissionDeniedError)
    @application.exception_handler(RegistrationDisabledError)
    async def handle_forbidden(_: Request, error: Exception) -> JSONResponse:
        return _error_response(403, error)

    @application.exception_handler(UserAlreadyExistsError)
    async def handle_conflict(_: Request, error: Exception) -> JSONResponse:
        return _error_response(409, error)

    @application.exception_handler(AccountLockedError)
    async def handle_locked(_: Request, error: Exception) -> JSONResponse:
        return _error_response(429, error)

    if settings.demo_mode:
        _seed_demo_environment_if_empty(application)
    return application
