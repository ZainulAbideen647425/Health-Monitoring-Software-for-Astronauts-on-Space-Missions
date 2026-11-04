"""Rules that judge a reading as normal, caution or critical.

IMPORTANT: this is an educational prototype, not a medical device. The ranges below summarise widely
used adult reference values and were chosen conservatively for a closed spacecraft environment.
Verify them against the primary sources before any real-world use.

How a reading is judged (the same logic for every indicator):
    1. value below `critical_below`, or above `critical_above`  -> CRITICAL
    2. value between `normal_minimum` and `normal_maximum`      -> NORMAL
    3. anything else                                           -> CAUTION
"""

from dataclasses import dataclass

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType, HealthStatus, ValueDirection


@dataclass(frozen=True)
class RuleEvaluation:
    """Result of applying a rule to one value."""

    status: HealthStatus
    direction: ValueDirection


@dataclass(frozen=True)
class HealthStatusRule:
    """Expected range, critical limits and sources for one health indicator."""

    indicator_type: HealthIndicatorType
    normal_minimum: float
    normal_maximum: float
    critical_below: float | None
    critical_above: float | None
    minimum_meaningful_change: float
    measurement_conditions: str
    source_notes: str
    source_urls: tuple[str, ...]

    def evaluate(self, value: float) -> RuleEvaluation:
        """Judge one value. Boundaries: critical_below is exclusive, critical_above is exclusive."""
        if self.critical_below is not None and value < self.critical_below:
            return RuleEvaluation(HealthStatus.CRITICAL, ValueDirection.BELOW_EXPECTED_RANGE)
        if self.critical_above is not None and value > self.critical_above:
            return RuleEvaluation(HealthStatus.CRITICAL, ValueDirection.ABOVE_EXPECTED_RANGE)
        if self.normal_minimum <= value <= self.normal_maximum:
            return RuleEvaluation(HealthStatus.NORMAL, ValueDirection.WITHIN_EXPECTED_RANGE)
        direction = (
            ValueDirection.BELOW_EXPECTED_RANGE if value < self.normal_minimum else ValueDirection.ABOVE_EXPECTED_RANGE
        )
        return RuleEvaluation(HealthStatus.CAUTION, direction)


HEALTH_STATUS_RULES: dict[HealthIndicatorType, HealthStatusRule] = {
    HealthIndicatorType.HEART_RATE: HealthStatusRule(
        indicator_type=HealthIndicatorType.HEART_RATE,
        normal_minimum=50,
        normal_maximum=100,
        critical_below=40,
        critical_above=120,
        minimum_meaningful_change=10,
        measurement_conditions="Resting heart rate, taken after at least five minutes of rest.",
        source_notes=(
            "American Heart Association: normal adult resting heart rate is 60 to 100 beats per minute, "
            "and very fit people can be as low as 40. The lower normal limit is set to 50 because astronaut "
            "crews are physically fit; each astronaut's own baseline refines this."
        ),
        source_urls=("https://www.aarp.org/health/healthy-living/what-is-a-healthy-heart-rate/",),
    ),
    HealthIndicatorType.SYSTOLIC_BLOOD_PRESSURE: HealthStatusRule(
        indicator_type=HealthIndicatorType.SYSTOLIC_BLOOD_PRESSURE,
        normal_minimum=90,
        normal_maximum=129,
        critical_below=80,
        critical_above=159,
        minimum_meaningful_change=10,
        measurement_conditions="Seated, relaxed for five minutes, cuff at heart level.",
        source_notes=(
            "American Heart Association categories: normal below 120, elevated 120 to 129, stage 1 hypertension "
            "130 to 139, stage 2 hypertension 140 or higher, crisis above 180. This prototype treats up to 129 as "
            "normal, 130 to 159 as caution, and 160 or higher as critical to be conservative in a closed environment. "
            "Unusually low readings should be evaluated by a clinician, so below 90 is caution "
            "and below 80 is critical."
        ),
        source_urls=("https://heart.org/bplevels",),
    ),
    HealthIndicatorType.DIASTOLIC_BLOOD_PRESSURE: HealthStatusRule(
        indicator_type=HealthIndicatorType.DIASTOLIC_BLOOD_PRESSURE,
        normal_minimum=60,
        normal_maximum=79,
        critical_below=50,
        critical_above=99,
        minimum_meaningful_change=8,
        measurement_conditions="Same cuff reading as systolic pressure.",
        source_notes=(
            "American Heart Association categories: normal below 80, stage 1 hypertension 80 to 89, stage 2 "
            "hypertension 90 or higher, crisis above 120. This prototype uses caution for 80 to 99 and critical "
            "for 100 or higher; below 60 is caution and below 50 is critical."
        ),
        source_urls=("https://heart.org/bplevels",),
    ),
    HealthIndicatorType.BLOOD_GLUCOSE: HealthStatusRule(
        indicator_type=HealthIndicatorType.BLOOD_GLUCOSE,
        normal_minimum=70,
        normal_maximum=99,
        critical_below=54,
        critical_above=249,
        minimum_meaningful_change=20,
        measurement_conditions="Fasting (at least eight hours without food) or before a meal.",
        source_notes=(
            "American Diabetes Association Standards of Care: fasting glucose 70 to 99 mg/dL is normal, 100 to 125 "
            "is prediabetes range, 126 or higher is the diabetes threshold; below 70 is hypoglycemia and below 54 "
            "is severe (level 2) hypoglycemia. Readings of 250 or more are treated as critical here. "
            "These values were confirmed through summaries of the ADA standards, not the ADA document itself."
        ),
        source_urls=("https://www.diabetesselfmanagement.com/blood-sugar-chart.html",),
    ),
    HealthIndicatorType.BODY_TEMPERATURE: HealthStatusRule(
        indicator_type=HealthIndicatorType.BODY_TEMPERATURE,
        normal_minimum=36.1,
        normal_maximum=37.5,
        critical_below=35.0,
        critical_above=37.9,
        minimum_meaningful_change=0.5,
        measurement_conditions="Oral or contactless thermometer, same time of day, not right after exercise.",
        source_notes=(
            "Fever is generally defined as 38.0 C (100.4 F) or higher and hypothermia as below 35 C (95 F) "
            "(CDC definitions as summarised by health references). Any fever is treated as critical here because "
            "infections spread easily in a closed spacecraft and immune function changes in spaceflight."
        ),
        source_urls=("https://www.tuasaude.com/en/how-to-tell-if-you-have-a-fever/",),
    ),
    HealthIndicatorType.SLEEP_DURATION: HealthStatusRule(
        indicator_type=HealthIndicatorType.SLEEP_DURATION,
        normal_minimum=7,
        normal_maximum=9,
        critical_below=4,
        critical_above=None,
        minimum_meaningful_change=1.5,
        measurement_conditions="Hours actually slept in the last 24 hours, not hours in bed.",
        source_notes=(
            "NASA schedules 8.5 hours of sleep per night for crew, yet a ten-year study found crew averaged about "
            "6 hours in flight, and ground studies link sleep under 6 hours to performance problems "
            "(Barger et al., Brigham and Women's Hospital). Seven to nine hours is used as the normal range."
        ),
        source_urls=("https://sciencedaily.com/releases/2014/08/140807215803.htm",),
    ),
    HealthIndicatorType.MOOD_SCORE: HealthStatusRule(
        indicator_type=HealthIndicatorType.MOOD_SCORE,
        normal_minimum=6,
        normal_maximum=10,
        critical_below=4,
        critical_above=None,
        minimum_meaningful_change=2,
        measurement_conditions="Self-rated from 1 (very low) to 10 (very good).",
        source_notes=(
            "This is a self-report scale designed for this prototype, not a diagnostic instrument. "
            "NASA's Human Research Program identifies isolation, confinement and distance from Earth as "
            "behavioral health hazards, so low scores prompt contact with support."
        ),
        source_urls=(),
    ),
}


def get_health_status_rule(indicator_type: HealthIndicatorType) -> HealthStatusRule:
    """Return the status rule for an indicator."""
    return HEALTH_STATUS_RULES[indicator_type]
