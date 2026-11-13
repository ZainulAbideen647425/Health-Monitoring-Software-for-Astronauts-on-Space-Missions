from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType
from astronaut_health_monitor.domain.health_analytics import (
    ForecastRisk,
    daily_means,
    find_unusual_days,
    forecast_indicator,
)
from astronaut_health_monitor.domain.health_status_rules import get_health_status_rule

START = datetime(2026, 10, 1, 8, tzinfo=UTC)


def readings(values_by_indicator: dict[str, list[float]]) -> pd.DataFrame:
    rows = [
        {"indicator": name, "value": value, "measured_at": START + timedelta(days=day)}
        for name, values in values_by_indicator.items()
        for day, value in enumerate(values)
    ]
    return pd.DataFrame(rows, columns=["indicator", "value", "measured_at"])


def test_empty_history_gives_an_empty_table_and_no_flags() -> None:
    daily = daily_means(readings({}))
    assert daily.empty
    assert find_unusual_days(daily) == ()


def test_daily_means_average_several_readings_in_one_day() -> None:
    frame = pd.DataFrame(
        {"indicator": ["heart_rate"] * 2, "value": [60.0, 80.0], "measured_at": [START, START + timedelta(hours=2)]}
    )
    assert daily_means(frame)["heart_rate"].iloc[0] == 70.0


def test_too_little_history_is_never_flagged() -> None:
    daily = daily_means(readings({"heart_rate": [70.0] * 5, "mood_score": [7.0] * 5}))
    assert find_unusual_days(daily) == ()


def test_a_day_with_a_strange_combination_is_flagged_and_explained() -> None:
    rng = np.random.default_rng(1)
    heart = list(70 + rng.normal(0, 1, 20))
    sleep = list(8 + rng.normal(0, 0.2, 20))
    heart[12], sleep[12] = 112.0, 3.0  # one day where everything is wrong at once
    flagged = find_unusual_days(daily_means(readings({"heart_rate": heart, "sleep_duration": sleep})))
    assert flagged, "the strange day should be flagged"
    top = flagged[0]
    assert top.day == (START + timedelta(days=12)).date()
    assert set(top.main_contributors) <= {"heart_rate", "sleep_duration"} and top.anomaly_score > 0


def test_the_flagging_is_repeatable() -> None:
    frame = readings(
        {"heart_rate": [70 + (i % 3) for i in range(15)], "mood_score": [7.0 - (i % 2) for i in range(15)]}
    )
    assert find_unusual_days(daily_means(frame)) == find_unusual_days(daily_means(frame))


def test_forecast_needs_enough_days() -> None:
    series = daily_means(readings({"heart_rate": [70.0] * 4}))["heart_rate"]
    rule = get_health_status_rule(HealthIndicatorType.HEART_RATE)
    assert forecast_indicator("heart_rate", series, rule, "Heart rate", "bpm") is None


def test_a_steady_indicator_has_no_risk() -> None:
    series = daily_means(readings({"heart_rate": [70.0 + (i % 2) for i in range(14)]}))["heart_rate"]
    result = forecast_indicator(
        "heart_rate", series, get_health_status_rule(HealthIndicatorType.HEART_RATE), "Heart rate", "bpm"
    )
    assert result is not None and result.risk is ForecastRisk.NONE


def test_a_rising_trend_heading_out_of_range_raises_a_watch_risk() -> None:
    series = daily_means(readings({"heart_rate": [80.0 + 3 * i for i in range(10)]}))["heart_rate"]  # 80..107
    result = forecast_indicator(
        "heart_rate", series, get_health_status_rule(HealthIndicatorType.HEART_RATE), "Heart rate", "bpm"
    )
    assert result is not None and result.risk is ForecastRisk.WATCH and result.projected_value > 100
    assert "flight surgeon" in result.message


def test_a_trend_heading_to_the_critical_limit_is_high_risk() -> None:
    series = daily_means(readings({"heart_rate": [90.0 + 5 * i for i in range(10)]}))["heart_rate"]  # to 135
    result = forecast_indicator(
        "heart_rate", series, get_health_status_rule(HealthIndicatorType.HEART_RATE), "Heart rate", "bpm"
    )
    assert result is not None and result.risk is ForecastRisk.HIGH


def test_a_noisy_series_is_not_treated_as_a_trend() -> None:
    noisy = [70, 95, 62, 99, 58, 97, 64, 96, 60, 98]
    series = daily_means(readings({"heart_rate": [float(v) for v in noisy]}))["heart_rate"]
    result = forecast_indicator(
        "heart_rate", series, get_health_status_rule(HealthIndicatorType.HEART_RATE), "Heart rate", "bpm"
    )
    assert result is not None and result.risk is ForecastRisk.NONE


def test_a_trend_that_stays_in_range_is_reported_without_alarm() -> None:
    series = daily_means(readings({"heart_rate": [60.0 + 2 * i for i in range(10)]}))["heart_rate"]
    result = forecast_indicator(
        "heart_rate", series, get_health_status_rule(HealthIndicatorType.HEART_RATE), "Heart rate", "bpm"
    )
    assert result is not None and result.risk is ForecastRisk.NONE and "stay in the healthy range" in result.message


def test_a_falling_trend_is_described_as_a_fall() -> None:
    series = daily_means(readings({"heart_rate": [100.0 - 4 * i for i in range(10)]}))["heart_rate"]  # to 64, toward 52
    result = forecast_indicator(
        "heart_rate", series, get_health_status_rule(HealthIndicatorType.HEART_RATE), "Heart rate", "bpm"
    )
    assert result is not None and result.slope_per_day < 0
    assert "trending to fall" in result.message or "stay in the healthy range" in result.message
