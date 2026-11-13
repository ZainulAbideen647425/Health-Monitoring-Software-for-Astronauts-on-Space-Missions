import pytest

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType, HealthStatus, ValueDirection
from astronaut_health_monitor.domain.guidance import get_guidance
from astronaut_health_monitor.domain.health_status_rules import get_health_status_rule

WELLBEING = (
    HealthIndicatorType.FATIGUE_LEVEL,
    HealthIndicatorType.STRESS_LEVEL,
    HealthIndicatorType.PHYSICAL_ACTIVITY,
)


@pytest.mark.parametrize(
    ("indicator", "value", "expected"),
    [
        (HealthIndicatorType.FATIGUE_LEVEL, 3, HealthStatus.NORMAL),
        (HealthIndicatorType.FATIGUE_LEVEL, 7, HealthStatus.CAUTION),
        (HealthIndicatorType.FATIGUE_LEVEL, 9, HealthStatus.CRITICAL),
        (HealthIndicatorType.STRESS_LEVEL, 2, HealthStatus.NORMAL),
        (HealthIndicatorType.STRESS_LEVEL, 6, HealthStatus.CAUTION),
        (HealthIndicatorType.STRESS_LEVEL, 10, HealthStatus.CRITICAL),
        (HealthIndicatorType.PHYSICAL_ACTIVITY, 90, HealthStatus.NORMAL),
        (HealthIndicatorType.PHYSICAL_ACTIVITY, 10, HealthStatus.CAUTION),
        (HealthIndicatorType.PHYSICAL_ACTIVITY, 300, HealthStatus.CAUTION),
    ],
)
def test_wellbeing_rules_judge_values(indicator: HealthIndicatorType, value: float, expected: HealthStatus) -> None:
    assert get_health_status_rule(indicator).evaluate(value).status is expected


def test_every_out_of_range_wellbeing_direction_has_guidance() -> None:
    for indicator in WELLBEING:
        rule = get_health_status_rule(indicator)
        for value in (rule.normal_minimum - 1, rule.normal_maximum + 1):
            direction = rule.evaluate(value).direction
            if direction is not ValueDirection.WITHIN_EXPECTED_RANGE and value >= 0:
                if (indicator, direction) in {
                    (HealthIndicatorType.FATIGUE_LEVEL, ValueDirection.BELOW_EXPECTED_RANGE),
                    (HealthIndicatorType.STRESS_LEVEL, ValueDirection.BELOW_EXPECTED_RANGE),
                }:
                    continue
                assert get_guidance(indicator, direction) is not None
