import pytest

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType, HealthStatus
from astronaut_health_monitor.domain.guidance import get_guidance
from astronaut_health_monitor.domain.health_status_rules import HEALTH_STATUS_RULES


@pytest.mark.parametrize(
    ("dose", "expected"),
    [
        (0.5, HealthStatus.NORMAL),
        (1.3, HealthStatus.NORMAL),
        (1.84, HealthStatus.CAUTION),
        (5.0, HealthStatus.CAUTION),
        (6.2, HealthStatus.CRITICAL),
    ],
)
def test_daily_radiation_dose_is_judged_against_nasa_figures(dose: float, expected: HealthStatus) -> None:
    rule = HEALTH_STATUS_RULES[HealthIndicatorType.RADIATION_DOSE]
    assert rule.evaluate(dose).status is expected
    assert "600 mSv" in rule.source_notes


def test_high_radiation_dose_has_guidance_that_mentions_shielding() -> None:
    rule = HEALTH_STATUS_RULES[HealthIndicatorType.RADIATION_DOSE]
    guidance = get_guidance(HealthIndicatorType.RADIATION_DOSE, rule.evaluate(2).direction)
    assert guidance is not None
    assert any("shielded" in action for action in guidance.recommended_actions)
