"""Request and response shapes of the HTTP API."""

from datetime import date, datetime
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from astronaut_health_monitor.domain.enumerations import (
    AuditOutcome,
    BatchItemOutcome,
    HealthIndicatorType,
    HealthStatus,
    MeasurementSource,
    MissionEnvironment,
    TrendDirection,
    UserRole,
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


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=200)


class UserResponse(BaseModel):
    username: str
    role: UserRole
    astronaut_id: int | None


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=200)
    role: UserRole
    astronaut_id: int | None = None


class RegistrationRequest(BaseModel):
    """Self-registration. The new account is always an astronaut account linked to a new crew record."""

    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=200)
    full_name: str = Field(min_length=1, max_length=120)
    mission_role: str = Field(default="Crew member", min_length=1, max_length=80)


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: datetime
    username: str | None
    user_role: str | None
    action: str
    target: str | None
    outcome: AuditOutcome
    detail: str


class AuditLogResponse(BaseModel):
    chain_is_valid: bool
    checked_event_count: int
    first_broken_event_id: int | None
    events: list[AuditEventResponse]


class UnusualDayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    anomaly_score: float
    main_contributors: list[str]


class IndicatorForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    indicator_type: HealthIndicatorType
    slope_per_day: float
    current_value: float
    projected_value: float
    horizon_days: int
    fit_quality: float
    risk: str
    message: str


class HealthAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    days_analyzed: int
    has_enough_data_for_unusual_days: bool
    has_enough_data_for_forecast: bool
    unusual_days: list[UnusualDayResponse]
    forecasts: list[IndicatorForecastResponse]
    method: str = (
        "Isolation Forest (unusual days) and linear regression (3-day risk forecast), trained only on this "
        "astronaut's own readings with scikit-learn. These are flags for review, not diagnoses."
    )
