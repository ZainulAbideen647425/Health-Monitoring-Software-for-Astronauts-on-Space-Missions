import pytest

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType
from astronaut_health_monitor.domain.health_indicator_reference import (
    HEALTH_INDICATOR_REFERENCES,
    get_health_indicator_reference,
)


def test_every_health_indicator_type_has_a_reference_entry() -> None:
    assert set(HEALTH_INDICATOR_REFERENCES) == set(HealthIndicatorType)


@pytest.mark.parametrize("indicator_type", list(HealthIndicatorType))
def test_each_reference_is_complete_and_has_sensible_bounds(indicator_type: HealthIndicatorType) -> None:
    reference = get_health_indicator_reference(indicator_type)
    assert reference.minimum_plausible_value < reference.maximum_plausible_value
    assert reference.unit and reference.how_to_measure and reference.why_it_matters_in_spaceflight


def test_plausibility_check_accepts_normal_and_rejects_impossible_heart_rate() -> None:
    reference = get_health_indicator_reference(HealthIndicatorType.HEART_RATE)
    assert reference.is_plausible(72)
    assert not reference.is_plausible(7000)
    assert not reference.is_plausible(-5)
