"""Builds the machine-learning analytics for one astronaut from stored readings."""

import pandas as pd

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType
from astronaut_health_monitor.domain.exceptions import AstronautNotFoundError
from astronaut_health_monitor.domain.health_analytics import (
    MINIMUM_DAYS_FOR_FORECAST,
    MINIMUM_DAYS_FOR_UNUSUAL_DAY_DETECTION,
    HealthAnalytics,
    IndicatorForecast,
    daily_means,
    find_unusual_days,
    forecast_indicator,
)
from astronaut_health_monitor.domain.health_indicator_reference import get_health_indicator_reference
from astronaut_health_monitor.domain.health_status_rules import get_health_status_rule
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.measurement_repository import MeasurementRepository

HISTORY_LIMIT = 1000


class HealthAnalyticsService:
    def __init__(
        self, measurement_repository: MeasurementRepository, astronaut_repository: AstronautRepository
    ) -> None:
        self._measurement_repository = measurement_repository
        self._astronaut_repository = astronaut_repository

    def analyze_astronaut(self, astronaut_id: int) -> HealthAnalytics:
        if self._astronaut_repository.get_astronaut_by_id(astronaut_id) is None:
            raise AstronautNotFoundError(f"Astronaut {astronaut_id} does not exist.")
        records = self._measurement_repository.list_measurements(astronaut_id, None, HISTORY_LIMIT)
        readings = pd.DataFrame(
            [
                {"indicator": record.indicator_type, "value": record.measured_value, "measured_at": record.measured_at}
                for record in records
            ],
            columns=["indicator", "value", "measured_at"],
        )
        daily = daily_means(readings)
        days = len(daily)
        forecasts: list[IndicatorForecast] = []
        for column in daily.columns:
            indicator_type = HealthIndicatorType(str(column))
            reference = get_health_indicator_reference(indicator_type)
            forecast = forecast_indicator(
                indicator_type.value,
                daily[column],
                get_health_status_rule(indicator_type),
                reference.display_name,
                reference.unit,
            )
            if forecast is not None:
                forecasts.append(forecast)
        order = {"high": 0, "watch": 1, "none": 2}
        forecasts.sort(key=lambda item: order[item.risk.value])
        return HealthAnalytics(
            days_analyzed=days,
            has_enough_data_for_unusual_days=days >= MINIMUM_DAYS_FOR_UNUSUAL_DAY_DETECTION,
            has_enough_data_for_forecast=days >= MINIMUM_DAYS_FOR_FORECAST,
            unusual_days=find_unusual_days(daily),
            forecasts=tuple(forecasts),
        )
