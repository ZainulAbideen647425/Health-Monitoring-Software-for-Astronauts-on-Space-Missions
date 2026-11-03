"""Request and response shapes of the HTTP API."""

from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType, MeasurementSource, MissionEnvironment


class MissionCreateRequest(BaseModel):
    mission_name: str = Field(min_length=1, max_length=120)
    mission_environment: MissionEnvironment
    mission_start_time: AwareDatetime


class MissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mission_name: str
    mission_environment: MissionEnvironment
    mission_start_time: datetime


class AstronautCreateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    mission_role: str = Field(min_length=1, max_length=80)
    mission_id: int | None = None


class AstronautResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    mission_role: str
    mission_id: int | None


class MeasurementCreateRequest(BaseModel):
    astronaut_id: int
    indicator_type: HealthIndicatorType
    measured_value: float
    measured_at: AwareDatetime
    measurement_source: MeasurementSource = MeasurementSource.MANUAL_ENTRY
    device_id: int | None = None
    notes: str | None = Field(default=None, max_length=500)


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    astronaut_id: int
    indicator_type: HealthIndicatorType
    measured_value: float
    measurement_unit: str
    measured_at: datetime
    measurement_source: MeasurementSource
    device_id: int | None
    notes: str | None


class HealthIndicatorReferenceResponse(BaseModel):
    indicator_type: HealthIndicatorType
    display_name: str
    unit: str
    minimum_plausible_value: float
    maximum_plausible_value: float
    how_to_measure: str
    why_it_matters_in_spaceflight: str


class ApplicationHealthResponse(BaseModel):
    status: str
    application_title: str
    application_version: str
    database_reachable: bool
