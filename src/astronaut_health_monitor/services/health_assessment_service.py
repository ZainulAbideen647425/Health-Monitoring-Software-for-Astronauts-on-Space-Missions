"""Judges measurements: expected-range rules, personal baseline, trend, and guidance."""

from astronaut_health_monitor.domain.enumerations import (
    HealthIndicatorType,
    HealthStatus,
    TrendDirection,
    ValueDirection,
)
from astronaut_health_monitor.domain.exceptions import AstronautNotFoundError, MeasurementNotFoundError
from astronaut_health_monitor.domain.guidance import FLIGHT_SURGEON_INSTRUCTION, GuidanceEntry, get_guidance
from astronaut_health_monitor.domain.health_assessment import (
    AstronautHealthSummary,
    HealthAssessment,
    PersonalBaselineAssessment,
)
from astronaut_health_monitor.domain.health_indicator_reference import get_health_indicator_reference
from astronaut_health_monitor.domain.health_status_rules import HealthStatusRule, get_health_status_rule
from astronaut_health_monitor.domain.personal_baseline import (
    BASELINE_WINDOW_SIZE,
    TREND_WINDOW_SIZE,
    calculate_personal_baseline,
    detect_trend,
    is_unusual_for_astronaut,
)
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.database_records import MeasurementRecord
from astronaut_health_monitor.repositories.measurement_repository import MeasurementRepository

_STATUS_SEVERITY = {HealthStatus.NORMAL: 0, HealthStatus.CAUTION: 1, HealthStatus.CRITICAL: 2}
_ROUTINE_ACTIONS = ("Keep measuring on your routine schedule.",)
_UNUSUAL_FOR_YOU_ACTIONS = (
    "Measure again at the next scheduled time to see whether the change continues.",
    "Think about recent sleep, hydration, workload and stress.",
    "Log how you feel so the pattern is easier to review.",
)


class HealthAssessmentService:
    def __init__(
        self, measurement_repository: MeasurementRepository, astronaut_repository: AstronautRepository
    ) -> None:
        self._measurement_repository = measurement_repository
        self._astronaut_repository = astronaut_repository

    def assess_measurement(self, measurement_id: int) -> HealthAssessment:
        measurement = self._measurement_repository.get_measurement_by_id(measurement_id)
        if measurement is None:
            raise MeasurementNotFoundError(f"Measurement {measurement_id} does not exist.")
        return self._assess(measurement)

    def summarize_astronaut_health(self, astronaut_id: int) -> AstronautHealthSummary:
        """Assess the newest reading of every indicator that the astronaut has recorded."""
        if self._astronaut_repository.get_astronaut_by_id(astronaut_id) is None:
            raise AstronautNotFoundError(f"Astronaut {astronaut_id} does not exist.")
        assessments: list[HealthAssessment] = []
        for indicator_type in HealthIndicatorType:
            latest = self._measurement_repository.get_latest_measurement(astronaut_id, indicator_type.value)
            if latest is not None:
                assessments.append(self._assess(latest))
        overall_status = max(
            (a.final_status for a in assessments), key=_STATUS_SEVERITY.__getitem__, default=HealthStatus.NORMAL
        )
        return AstronautHealthSummary(
            astronaut_id=astronaut_id,
            overall_status=overall_status,
            contact_flight_surgeon=overall_status is HealthStatus.CRITICAL,
            assessments=tuple(assessments),
        )

    def _assess(self, measurement: MeasurementRecord) -> HealthAssessment:
        indicator_type = HealthIndicatorType(measurement.indicator_type)
        reference = get_health_indicator_reference(indicator_type)
        rule = get_health_status_rule(indicator_type)
        evaluation = rule.evaluate(measurement.measured_value)

        previous_records = self._measurement_repository.list_measurements_before(
            measurement.astronaut_id, measurement.indicator_type, measurement.measured_at, BASELINE_WINDOW_SIZE
        )
        previous_values = [record.measured_value for record in reversed(previous_records)]  # oldest first
        baseline_assessment = self._assess_against_personal_baseline(measurement.measured_value, previous_values, rule)

        reasons: list[str] = []
        if evaluation.status is not HealthStatus.NORMAL:
            reasons.append(
                self._describe_rule_result(
                    reference.display_name, reference.unit, measurement.measured_value, rule, evaluation.direction
                )
            )
        if baseline_assessment.is_unusual_for_this_astronaut and baseline_assessment.baseline_mean is not None:
            side = "above" if (baseline_assessment.difference_from_baseline or 0) > 0 else "below"
            reasons.append(
                f"This is {abs(baseline_assessment.difference_from_baseline or 0):.1f} {side} your usual average of "
                f"{baseline_assessment.baseline_mean:.1f} (your last {baseline_assessment.sample_count} readings)."
            )
        if baseline_assessment.trend is not TrendDirection.STABLE:
            reasons.append(f"Your last {TREND_WINDOW_SIZE} readings show a {baseline_assessment.trend.value} trend.")

        personal_alert = (
            baseline_assessment.is_unusual_for_this_astronaut or baseline_assessment.trend is not TrendDirection.STABLE
        )
        final_status = evaluation.status
        if final_status is HealthStatus.NORMAL and personal_alert:
            final_status = HealthStatus.CAUTION

        guidance = get_guidance(indicator_type, evaluation.direction)
        explanation, actions, warning_signs = self._compose_guidance(
            final_status, evaluation.status, guidance, reference.display_name
        )
        if final_status is HealthStatus.CRITICAL:
            actions = (FLIGHT_SURGEON_INSTRUCTION, *actions)

        return HealthAssessment(
            measurement_id=measurement.id,
            astronaut_id=measurement.astronaut_id,
            indicator_type=indicator_type,
            indicator_display_name=reference.display_name,
            measured_value=measurement.measured_value,
            measurement_unit=measurement.measurement_unit,
            measured_at=measurement.measured_at,
            rule_status=evaluation.status,
            final_status=final_status,
            value_direction=evaluation.direction,
            headline=self._compose_headline(reference.display_name, final_status, evaluation.status),
            explanation=explanation,
            status_reasons=tuple(reasons),
            recommended_actions=actions,
            warning_signs_requiring_escalation=warning_signs,
            contact_flight_surgeon=final_status is HealthStatus.CRITICAL,
            personal_baseline=baseline_assessment,
        )

    @staticmethod
    def _assess_against_personal_baseline(
        value: float, previous_values: list[float], rule: HealthStatusRule
    ) -> PersonalBaselineAssessment:
        baseline = calculate_personal_baseline(previous_values)
        trend = detect_trend([*previous_values, value], rule.minimum_meaningful_change)
        if baseline is None:
            return PersonalBaselineAssessment(
                has_enough_history=False,
                sample_count=len(previous_values),
                baseline_mean=None,
                baseline_standard_deviation=None,
                difference_from_baseline=None,
                is_unusual_for_this_astronaut=False,
                trend=trend,
            )
        return PersonalBaselineAssessment(
            has_enough_history=True,
            sample_count=baseline.sample_count,
            baseline_mean=baseline.mean,
            baseline_standard_deviation=baseline.standard_deviation,
            difference_from_baseline=value - baseline.mean,
            is_unusual_for_this_astronaut=is_unusual_for_astronaut(value, baseline, rule.minimum_meaningful_change),
            trend=trend,
        )

    @staticmethod
    def _describe_rule_result(
        display_name: str, unit: str, value: float, rule: HealthStatusRule, direction: ValueDirection
    ) -> str:
        side = "below" if direction is ValueDirection.BELOW_EXPECTED_RANGE else "above"
        return (
            f"{display_name} of {value:g} ({unit}) is {side} the expected range of "
            f"{rule.normal_minimum:g} to {rule.normal_maximum:g}."
        )

    @staticmethod
    def _compose_headline(display_name: str, final_status: HealthStatus, rule_status: HealthStatus) -> str:
        if final_status is HealthStatus.CRITICAL:
            return f"{display_name} needs urgent attention"
        if final_status is HealthStatus.CAUTION and rule_status is HealthStatus.NORMAL:
            return f"{display_name} is in range but unusual for you"
        if final_status is HealthStatus.CAUTION:
            return f"{display_name} is outside the expected range"
        return f"{display_name} is within the expected range"

    @staticmethod
    def _compose_guidance(
        final_status: HealthStatus, rule_status: HealthStatus, guidance: GuidanceEntry | None, display_name: str
    ) -> tuple[str, tuple[str, ...], str | None]:
        if rule_status is not HealthStatus.NORMAL and guidance is not None:
            return guidance.explanation, guidance.recommended_actions, guidance.warning_signs_requiring_escalation
        if final_status is HealthStatus.CAUTION:
            return (
                f"Your {display_name.lower()} is inside the expected range, "
                "but it differs from your own recent pattern.",
                _UNUSUAL_FOR_YOU_ACTIONS,
                None,
            )
        return (f"Your {display_name.lower()} is inside the expected range.", _ROUTINE_ACTIONS, None)
