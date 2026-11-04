"""Personal baselines: judging a reading against the astronaut's own recent history."""

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from astronaut_health_monitor.domain.enumerations import TrendDirection

BASELINE_WINDOW_SIZE = 14
MINIMUM_READINGS_FOR_BASELINE = 5
TREND_WINDOW_SIZE = 5
UNUSUAL_DEVIATION_IN_STANDARD_DEVIATIONS = 2.0


@dataclass(frozen=True)
class PersonalBaseline:
    """Average and spread of an astronaut's recent readings for one indicator."""

    sample_count: int
    mean: float
    standard_deviation: float


def calculate_personal_baseline(previous_values: Sequence[float]) -> PersonalBaseline | None:
    """Return the baseline of the most recent readings, or None when there is too little history."""
    recent_values = list(previous_values)[-BASELINE_WINDOW_SIZE:]
    if len(recent_values) < MINIMUM_READINGS_FOR_BASELINE:
        return None
    return PersonalBaseline(
        sample_count=len(recent_values),
        mean=statistics.fmean(recent_values),
        standard_deviation=statistics.stdev(recent_values),
    )


def is_unusual_for_astronaut(value: float, baseline: PersonalBaseline, minimum_meaningful_change: float) -> bool:
    """True when the value differs from the baseline by more than normal variation AND a meaningful amount.

    Both conditions are required: a very steady astronaut should not be flagged for a tiny change,
    and a naturally variable astronaut should not be flagged for ordinary ups and downs.
    """
    allowed_difference = max(
        UNUSUAL_DEVIATION_IN_STANDARD_DEVIATIONS * baseline.standard_deviation, minimum_meaningful_change
    )
    return abs(value - baseline.mean) > allowed_difference


def detect_trend(chronological_values: Sequence[float], minimum_meaningful_change: float) -> TrendDirection:
    """Fit a straight line through the last readings and report a rising or falling trend.

    The trend counts only when the line's total change across the window reaches the meaningful change.
    """
    if len(chronological_values) < TREND_WINDOW_SIZE:
        return TrendDirection.STABLE
    window = list(chronological_values)[-TREND_WINDOW_SIZE:]
    slope = statistics.linear_regression(range(TREND_WINDOW_SIZE), window).slope
    total_change = slope * (TREND_WINDOW_SIZE - 1)
    if total_change >= minimum_meaningful_change:
        return TrendDirection.RISING
    if total_change <= -minimum_meaningful_change:
        return TrendDirection.FALLING
    return TrendDirection.STABLE
