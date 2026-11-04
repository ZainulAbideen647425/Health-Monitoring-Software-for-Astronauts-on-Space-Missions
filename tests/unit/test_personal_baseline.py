import pytest

from astronaut_health_monitor.domain.enumerations import TrendDirection
from astronaut_health_monitor.domain.personal_baseline import (
    BASELINE_WINDOW_SIZE,
    PersonalBaseline,
    calculate_personal_baseline,
    detect_trend,
    is_unusual_for_astronaut,
)


def test_no_baseline_with_too_little_history() -> None:
    assert calculate_personal_baseline([60, 61, 62, 63]) is None


def test_baseline_is_mean_and_standard_deviation_of_history() -> None:
    baseline = calculate_personal_baseline([60, 62, 64, 66, 68])
    assert baseline is not None
    assert baseline.sample_count == 5
    assert baseline.mean == pytest.approx(64)
    assert baseline.standard_deviation == pytest.approx(3.1623, rel=1e-3)


def test_baseline_uses_only_the_most_recent_readings() -> None:
    old_readings = [200.0] * 10
    recent_readings = [60.0] * BASELINE_WINDOW_SIZE
    baseline = calculate_personal_baseline(old_readings + recent_readings)
    assert baseline is not None
    assert baseline.sample_count == BASELINE_WINDOW_SIZE
    assert baseline.mean == pytest.approx(60)


def test_steady_astronaut_is_not_flagged_for_a_tiny_change() -> None:
    steady = PersonalBaseline(sample_count=10, mean=60, standard_deviation=0.1)
    assert not is_unusual_for_astronaut(62, steady, minimum_meaningful_change=10)


def test_meaningful_change_from_a_steady_baseline_is_flagged() -> None:
    steady = PersonalBaseline(sample_count=10, mean=60, standard_deviation=0.5)
    assert is_unusual_for_astronaut(75, steady, minimum_meaningful_change=10)
    assert is_unusual_for_astronaut(45, steady, minimum_meaningful_change=10)


def test_naturally_variable_astronaut_is_not_flagged_for_ordinary_swings() -> None:
    variable = PersonalBaseline(sample_count=10, mean=60, standard_deviation=8)
    assert not is_unusual_for_astronaut(72, variable, minimum_meaningful_change=10)


@pytest.mark.parametrize(
    ("values", "expected_trend"),
    [
        ([60, 63, 66, 69, 72], TrendDirection.RISING),
        ([72, 69, 66, 63, 60], TrendDirection.FALLING),
        ([60, 61, 60, 61, 60], TrendDirection.STABLE),
        ([60, 62, 61, 63, 64], TrendDirection.STABLE),  # moving up, but less than the meaningful change
        ([60, 63], TrendDirection.STABLE),  # too few readings to call a trend
        ([100, 100, 60, 63, 66, 69, 72], TrendDirection.RISING),  # only the last five readings count
    ],
)
def test_trend_detection(values: list[float], expected_trend: TrendDirection) -> None:
    assert detect_trend(values, minimum_meaningful_change=10) is expected_trend
