"""Machine-learning analytics on one astronaut's own history (scikit-learn, pandas, NumPy).

Two models, both trained only on that astronaut's readings, so "unusual" always means "unusual for this person":

1. **Unusual-day detection**: an Isolation Forest looks at each day as one row (the daily mean of every indicator)
   and flags days whose combination of values is rare. It can notice that poor sleep, high stress and a raised
   heart rate together are strange even if each value alone is still inside its normal range.
2. **Risk forecast**: a linear regression per indicator projects the next few days. A risk is raised only when the
   fit is reasonable and the projected change is larger than the smallest change that matters.

The models only *flag* things for a human. The rule-based status stays the safety-critical judgement.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression

from astronaut_health_monitor.domain.health_status_rules import HealthStatusRule

MINIMUM_DAYS_FOR_UNUSUAL_DAY_DETECTION = 10
MINIMUM_INDICATORS_FOR_UNUSUAL_DAY_DETECTION = 2
MINIMUM_DAYS_FOR_FORECAST = 7
FORECAST_HORIZON_DAYS = 3
MINIMUM_FIT_QUALITY = 0.3  # R squared; weaker trends are treated as noise
RANDOM_SEED = 0
NUMBER_OF_TREES = 200


class ForecastRisk(StrEnum):
    NONE = "none"
    WATCH = "watch"
    HIGH = "high"


@dataclass(frozen=True)
class UnusualDay:
    day: date
    anomaly_score: float  # higher means stranger; 0 is the decision boundary
    main_contributors: tuple[str, ...]  # indicators that differed most from this astronaut's usual values


@dataclass(frozen=True)
class IndicatorForecast:
    indicator_type: str
    slope_per_day: float
    current_value: float
    projected_value: float
    horizon_days: int
    fit_quality: float
    risk: ForecastRisk
    message: str


@dataclass(frozen=True)
class HealthAnalytics:
    days_analyzed: int
    has_enough_data_for_unusual_days: bool
    has_enough_data_for_forecast: bool
    unusual_days: tuple[UnusualDay, ...]
    forecasts: tuple[IndicatorForecast, ...]


def daily_means(readings: pd.DataFrame) -> pd.DataFrame:
    """Rows are days, columns are indicators, values are the daily mean. Input needs: indicator, value, measured_at."""
    if readings.empty:
        return pd.DataFrame()
    frame = readings.assign(day=pd.to_datetime(readings["measured_at"], utc=True).dt.date)
    return frame.pivot_table(index="day", columns="indicator", values="value", aggfunc="mean").sort_index()


def find_unusual_days(daily: pd.DataFrame) -> tuple[UnusualDay, ...]:
    usable = daily.dropna(axis=1, thresh=MINIMUM_DAYS_FOR_UNUSUAL_DAY_DETECTION)
    if (
        len(usable) < MINIMUM_DAYS_FOR_UNUSUAL_DAY_DETECTION
        or usable.shape[1] < MINIMUM_INDICATORS_FOR_UNUSUAL_DAY_DETECTION
    ):
        return ()
    filled = usable.fillna(usable.median())
    spread = filled.std(ddof=0).replace(0, 1.0)
    standardized = (filled - filled.mean()) / spread
    forest = IsolationForest(n_estimators=NUMBER_OF_TREES, contamination="auto", random_state=RANDOM_SEED)
    forest.fit(standardized.to_numpy())
    scores = -forest.decision_function(standardized.to_numpy())  # positive means more unusual
    flagged: list[UnusualDay] = []
    for position, day in enumerate(standardized.index):
        if scores[position] <= 0:
            continue
        row = standardized.iloc[position].abs().sort_values(ascending=False)
        contributors = tuple(str(name) for name, z in row.items() if z >= 1.0)[:3] or (str(row.index[0]),)
        flagged.append(
            UnusualDay(day=day, anomaly_score=round(float(scores[position]), 4), main_contributors=contributors)
        )
    return tuple(sorted(flagged, key=lambda item: item.anomaly_score, reverse=True))


def forecast_indicator(
    indicator_type: str, daily_values: pd.Series, rule: HealthStatusRule, display_name: str, unit: str
) -> IndicatorForecast | None:
    series = daily_values.dropna()
    if len(series) < MINIMUM_DAYS_FOR_FORECAST:
        return None
    days = np.array([(d - series.index[0]).days for d in series.index], dtype=float).reshape(-1, 1)
    values = series.to_numpy(dtype=float)
    model = LinearRegression().fit(days, values)
    fit_quality = float(model.score(days, values))
    slope = float(model.coef_[0])
    last_day = float(days[-1, 0])
    projected = float(model.predict(np.array([[last_day + FORECAST_HORIZON_DAYS]]))[0])
    current = float(values[-1])
    observed_movement = abs(slope) * float(days[-1, 0] - days[0, 0])  # how far the fitted line moved so far
    risk = ForecastRisk.NONE
    message = f"{display_name} is steady. No risk is projected for the next {FORECAST_HORIZON_DAYS} days."
    meaningful = fit_quality >= MINIMUM_FIT_QUALITY and observed_movement >= rule.minimum_meaningful_change
    if meaningful:
        direction = "rise" if slope > 0 else "fall"
        crosses_normal = projected > rule.normal_maximum or projected < rule.normal_minimum
        crosses_critical = (rule.critical_above is not None and projected >= rule.critical_above) or (
            rule.critical_below is not None and projected <= rule.critical_below
        )
        if crosses_critical:
            risk = ForecastRisk.HIGH
        elif crosses_normal:
            risk = ForecastRisk.WATCH
        if risk is not ForecastRisk.NONE:
            message = (
                f"{display_name} is trending to {direction} to about {projected:.1f} {unit} within "
                f"{FORECAST_HORIZON_DAYS} days, outside the healthy range "
                f"({rule.normal_minimum:g} to {rule.normal_maximum:g}). Review it with the flight surgeon."
            )
        else:
            message = f"{display_name} is trending to {direction} but is projected to stay in the healthy range."
    return IndicatorForecast(
        indicator_type=indicator_type,
        slope_per_day=round(slope, 3),
        current_value=round(current, 2),
        projected_value=round(projected, 2),
        horizon_days=FORECAST_HORIZON_DAYS,
        fit_quality=round(fit_quality, 3),
        risk=risk,
        message=message,
    )
