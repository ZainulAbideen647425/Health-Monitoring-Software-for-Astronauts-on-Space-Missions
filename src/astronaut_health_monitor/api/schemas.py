"""Request and response shapes of the HTTP API."""

from datetime import datetime
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from astronaut_health_monitor.domain.enumerations import (
    BatchItemOutcome,
    HealthIndicatorType,
    HealthStatus,
    MeasurementSource,
    MissionEnvironment,
    TrendDirection,
    ValueDirection,
)


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
    client_reference: str | None = Field(default=None, min_length=8, max_length=64)


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
    client_reference: str | None


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


class QueuedMeasurementItem(MeasurementCreateRequest):
    """One measurement inside a synchronization batch. The client reference is mandatory here."""

    client_reference: str = Field(min_length=8, max_length=64)


class MeasurementBatchRequest(BaseModel):
    """Items are validated one by one, so a single malformed item cannot block the whole batch."""

    measurements: list[dict[str, Any]] = Field(min_length=1, max_length=500)


class MeasurementBatchItemResponse(BaseModel):
    index: int
    client_reference: str | None
    outcome: BatchItemOutcome
    measurement_id: int | None
    rejection_reason: str | None


class MeasurementBatchResponse(BaseModel):
    created_count: int
    duplicate_count: int
    rejected_count: int
    results: list[MeasurementBatchItemResponse]


class HealthStatusRuleResponse(BaseModel):
    indicator_type: HealthIndicatorType
    unit: str
    normal_minimum: float
    normal_maximum: float
    critical_below: float | None
    critical_above: float | None
    minimum_meaningful_change: float
    measurement_conditions: str
    source_notes: str
    source_urls: list[str]


class PersonalBaselineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    has_enough_history: bool
    sample_count: int
    baseline_mean: float | None
    baseline_standard_deviation: float | None
    difference_from_baseline: float | None
    is_unusual_for_this_astronaut: bool
    trend: TrendDirection


class HealthAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    measurement_id: int
    astronaut_id: int
    indicator_type: HealthIndicatorType
    indicator_display_name: str
    measured_value: float
    measurement_unit: str
    measured_at: datetime
    rule_status: HealthStatus
    final_status: HealthStatus
    value_direction: ValueDirection
    headline: str
    explanation: str
    status_reasons: list[str]
    recommended_actions: list[str]
    warning_signs_requiring_escalation: str | None
    contact_flight_surgeon: bool
    personal_baseline: PersonalBaselineResponse


class AstronautHealthSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    astronaut_id: int
    overall_status: HealthStatus
    contact_flight_surgeon: bool
    assessments: list[HealthAssessmentResponse]
