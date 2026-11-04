import pytest

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType, HealthStatus, ValueDirection
from astronaut_health_monitor.domain.health_indicator_reference import get_health_indicator_reference
from astronaut_health_monitor.domain.health_status_rules import HEALTH_STATUS_RULES, get_health_status_rule

NORMAL = HealthStatus.NORMAL
CAUTION = HealthStatus.CAUTION
CRITICAL = HealthStatus.CRITICAL


def test_every_indicator_has_a_status_rule() -> None:
    assert set(HEALTH_STATUS_RULES) == set(HealthIndicatorType)


@pytest.mark.parametrize("indicator_type", list(HealthIndicatorType))
def test_rule_limits_are_ordered_sensibly_and_inside_plausible_range(indicator_type: HealthIndicatorType) -> None:
    rule = get_health_status_rule(indicator_type)
    reference = get_health_indicator_reference(indicator_type)
    assert rule.normal_minimum < rule.normal_maximum
    if rule.critical_below is not None:
        assert reference.minimum_plausible_value <= rule.critical_below < rule.normal_minimum
    if rule.critical_above is not None:
        assert rule.normal_maximum < rule.critical_above <= reference.maximum_plausible_value
    assert rule.minimum_meaningful_change > 0
    assert rule.source_notes and rule.measurement_conditions


@pytest.mark.parametrize(
    ("indicator_type", "value", "expected_status"),
    [
        # heart rate: normal 50-100, critical below 40 or above 120
        (HealthIndicatorType.HEART_RATE, 72, NORMAL),
        (HealthIndicatorType.HEART_RATE, 50, NORMAL),
        (HealthIndicatorType.HEART_RATE, 100, NORMAL),
        (HealthIndicatorType.HEART_RATE, 45, CAUTION),
        (HealthIndicatorType.HEART_RATE, 40, CAUTION),
        (HealthIndicatorType.HEART_RATE, 39, CRITICAL),
        (HealthIndicatorType.HEART_RATE, 110, CAUTION),
        (HealthIndicatorType.HEART_RATE, 120, CAUTION),
        (HealthIndicatorType.HEART_RATE, 121, CRITICAL),
        # systolic pressure: normal 90-129, critical below 80 or above 159
        (HealthIndicatorType.SYSTOLIC_BLOOD_PRESSURE, 118, NORMAL),
        (HealthIndicatorType.SYSTOLIC_BLOOD_PRESSURE, 135, CAUTION),
        (HealthIndicatorType.SYSTOLIC_BLOOD_PRESSURE, 85, CAUTION),
        (HealthIndicatorType.SYSTOLIC_BLOOD_PRESSURE, 160, CRITICAL),
        (HealthIndicatorType.SYSTOLIC_BLOOD_PRESSURE, 79, CRITICAL),
        # diastolic pressure: normal 60-79, critical below 50 or above 99
        (HealthIndicatorType.DIASTOLIC_BLOOD_PRESSURE, 75, NORMAL),
        (HealthIndicatorType.DIASTOLIC_BLOOD_PRESSURE, 85, CAUTION),
        (HealthIndicatorType.DIASTOLIC_BLOOD_PRESSURE, 100, CRITICAL),
        (HealthIndicatorType.DIASTOLIC_BLOOD_PRESSURE, 49, CRITICAL),
        # glucose: normal 70-99, critical below 54 or above 249
        (HealthIndicatorType.BLOOD_GLUCOSE, 85, NORMAL),
        (HealthIndicatorType.BLOOD_GLUCOSE, 110, CAUTION),
        (HealthIndicatorType.BLOOD_GLUCOSE, 60, CAUTION),
        (HealthIndicatorType.BLOOD_GLUCOSE, 53, CRITICAL),
        (HealthIndicatorType.BLOOD_GLUCOSE, 250, CRITICAL),
        # temperature: normal 36.1-37.5, any fever (above 37.9) or below 35.0 is critical
        (HealthIndicatorType.BODY_TEMPERATURE, 36.8, NORMAL),
        (HealthIndicatorType.BODY_TEMPERATURE, 37.7, CAUTION),
        (HealthIndicatorType.BODY_TEMPERATURE, 35.5, CAUTION),
        (HealthIndicatorType.BODY_TEMPERATURE, 38.0, CRITICAL),
        (HealthIndicatorType.BODY_TEMPERATURE, 34.9, CRITICAL),
        # sleep: normal 7-9 hours, critical below 4, no critical upper limit
        (HealthIndicatorType.SLEEP_DURATION, 8, NORMAL),
        (HealthIndicatorType.SLEEP_DURATION, 6, CAUTION),
        (HealthIndicatorType.SLEEP_DURATION, 3.9, CRITICAL),
        (HealthIndicatorType.SLEEP_DURATION, 11, CAUTION),
        # mood: normal 6-10, critical below 4
        (HealthIndicatorType.MOOD_SCORE, 8, NORMAL),
        (HealthIndicatorType.MOOD_SCORE, 5, CAUTION),
        (HealthIndicatorType.MOOD_SCORE, 3, CRITICAL),
    ],
)
def test_status_boundaries(indicator_type: HealthIndicatorType, value: float, expected_status: HealthStatus) -> None:
    assert get_health_status_rule(indicator_type).evaluate(value).status is expected_status


def test_direction_is_reported_for_each_side_of_the_range() -> None:
    rule = get_health_status_rule(HealthIndicatorType.HEART_RATE)
    assert rule.evaluate(72).direction is ValueDirection.WITHIN_EXPECTED_RANGE
    assert rule.evaluate(45).direction is ValueDirection.BELOW_EXPECTED_RANGE
    assert rule.evaluate(110).direction is ValueDirection.ABOVE_EXPECTED_RANGE
    assert rule.evaluate(30).direction is ValueDirection.BELOW_EXPECTED_RANGE
    assert rule.evaluate(150).direction is ValueDirection.ABOVE_EXPECTED_RANGE
