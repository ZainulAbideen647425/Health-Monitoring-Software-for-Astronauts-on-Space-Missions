"""Builds the FastAPI application."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from astronaut_health_monitor import __version__
from astronaut_health_monitor.api.routes import router
from astronaut_health_monitor.core.configuration import get_application_settings
from astronaut_health_monitor.core.database import create_all_tables, create_database_engine, create_session_factory
from astronaut_health_monitor.domain.exceptions import (
    AstronautNotFoundError,
    DeviceNotFoundError,
    ImplausibleMeasurementError,
    InvalidMeasurementTimeError,
    MeasurementNotFoundError,
    MissionNotFoundError,
)

logger = logging.getLogger(__name__)


def _error_response(status_code: int, error: Exception) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": str(error)})


def create_application(database_url: str | None = None) -> FastAPI:
    """Create the application. Tests pass an in-memory database URL."""
    settings = get_application_settings()
    engine = create_database_engine(database_url or settings.database_url)
    create_all_tables(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    application = FastAPI(title=settings.application_title, version=__version__, lifespan=lifespan)
    application.state.session_factory = create_session_factory(engine)
    application.include_router(router)

    @application.exception_handler(MissionNotFoundError)
    @application.exception_handler(MeasurementNotFoundError)
    @application.exception_handler(AstronautNotFoundError)
    @application.exception_handler(DeviceNotFoundError)
    async def handle_not_found(_: Request, error: Exception) -> JSONResponse:
        return _error_response(404, error)

    @application.exception_handler(ImplausibleMeasurementError)
    @application.exception_handler(InvalidMeasurementTimeError)
    async def handle_invalid_measurement(_: Request, error: Exception) -> JSONResponse:
        return _error_response(422, error)

    return application
