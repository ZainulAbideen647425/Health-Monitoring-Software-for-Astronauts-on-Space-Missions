"""Result objects produced when a measurement is assessed."""

from dataclasses import dataclass
from datetime import datetime

from astronaut_health_monitor.domain.enumerations import (
    HealthIndicatorType,
    HealthStatus,
    TrendDirection,
    ValueDirection,
)


@dataclass(frozen=True)
class PersonalBaselineAssessment:
    """How a reading compares with the astronaut's own history."""

    has_enough_history: bool
    sample_count: int
    baseline_mean: float | None
    baseline_standard_deviation: float | None
    difference_from_baseline: float | None
    is_unusual_for_this_astronaut: bool
    trend: TrendDirection


@dataclass(frozen=True)
class HealthAssessment:
    """Complete judgement of one measurement."""

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
    status_reasons: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    warning_signs_requiring_escalation: str | None
    contact_flight_surgeon: bool
    personal_baseline: PersonalBaselineAssessment


@dataclass(frozen=True)
class AstronautHealthSummary:
    """The latest assessment of every indicator for one astronaut."""

    astronaut_id: int
    overall_status: HealthStatus
    contact_flight_surgeon: bool
    assessments: tuple[HealthAssessment, ...]
