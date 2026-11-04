import pytest

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType, ValueDirection
from astronaut_health_monitor.domain.guidance import GUIDANCE, get_guidance
from astronaut_health_monitor.domain.health_indicator_reference import get_health_indicator_reference
from astronaut_health_monitor.domain.health_status_rules import get_health_status_rule


@pytest.mark.parametrize("indicator_type", list(HealthIndicatorType))
def test_guidance_exists_for_every_direction_a_reading_can_be_outside_its_range(
    indicator_type: HealthIndicatorType,
) -> None:
    rule = get_health_status_rule(indicator_type)
    reference = get_health_indicator_reference(indicator_type)
    if reference.minimum_plausible_value < rule.normal_minimum:
        assert get_guidance(indicator_type, ValueDirection.BELOW_EXPECTED_RANGE) is not None
    if rule.normal_maximum < reference.maximum_plausible_value:
        assert get_guidance(indicator_type, ValueDirection.ABOVE_EXPECTED_RANGE) is not None


def test_every_guidance_entry_is_complete() -> None:
    for entry in GUIDANCE.values():
        assert entry.explanation
        assert entry.likely_causes
        assert entry.recommended_actions
        assert entry.warning_signs_requiring_escalation


def test_no_guidance_exists_for_impossible_directions() -> None:
    assert get_guidance(HealthIndicatorType.MOOD_SCORE, ValueDirection.ABOVE_EXPECTED_RANGE) is None
    assert get_guidance(HealthIndicatorType.HEART_RATE, ValueDirection.WITHIN_EXPECTED_RANGE) is None
