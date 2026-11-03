"""Reference information for each health indicator.

The bounds below are *plausibility limits* used only to reject impossible input
(for example a typing mistake such as a heart rate of 7000). They are NOT clinical
thresholds. Clinical status rules (normal / caution / critical) are added in Phase 2.
"""

from dataclasses import dataclass

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType


@dataclass(frozen=True)
class HealthIndicatorReference:
    """Describes one health indicator in a way an astronaut can understand."""

    indicator_type: HealthIndicatorType
    display_name: str
    unit: str
    minimum_plausible_value: float
    maximum_plausible_value: float
    how_to_measure: str
    why_it_matters_in_spaceflight: str

    def is_plausible(self, value: float) -> bool:
        """Return True when the value lies inside the plausibility limits."""
        return self.minimum_plausible_value <= value <= self.maximum_plausible_value


HEALTH_INDICATOR_REFERENCES: dict[HealthIndicatorType, HealthIndicatorReference] = {
    HealthIndicatorType.HEART_RATE: HealthIndicatorReference(
        indicator_type=HealthIndicatorType.HEART_RATE,
        display_name="Heart rate",
        unit="beats per minute",
        minimum_plausible_value=20,
        maximum_plausible_value=250,
        how_to_measure="Use a wearable sensor, or count pulse beats at the wrist for 30 seconds and double it.",
        why_it_matters_in_spaceflight=(
            "Fluid shifts and altered gravity change cardiovascular load; "
            "a rising resting heart rate can signal stress, dehydration or deconditioning."
        ),
    ),
    HealthIndicatorType.SYSTOLIC_BLOOD_PRESSURE: HealthIndicatorReference(
        indicator_type=HealthIndicatorType.SYSTOLIC_BLOOD_PRESSURE,
        display_name="Systolic blood pressure",
        unit="mmHg",
        minimum_plausible_value=50,
        maximum_plausible_value=260,
        how_to_measure="Use the cuff-based blood pressure monitor while seated and relaxed for five minutes.",
        why_it_matters_in_spaceflight=(
            "Microgravity redistributes body fluids toward the head and alters blood pressure regulation."
        ),
    ),
    HealthIndicatorType.DIASTOLIC_BLOOD_PRESSURE: HealthIndicatorReference(
        indicator_type=HealthIndicatorType.DIASTOLIC_BLOOD_PRESSURE,
        display_name="Diastolic blood pressure",
        unit="mmHg",
        minimum_plausible_value=30,
        maximum_plausible_value=160,
        how_to_measure="Read together with systolic pressure from the same cuff measurement.",
        why_it_matters_in_spaceflight=(
            "Together with systolic pressure it shows how hard the heart works against vessel resistance."
        ),
    ),
    HealthIndicatorType.BLOOD_GLUCOSE: HealthIndicatorReference(
        indicator_type=HealthIndicatorType.BLOOD_GLUCOSE,
        display_name="Blood glucose",
        unit="mg/dL",
        minimum_plausible_value=20,
        maximum_plausible_value=600,
        how_to_measure="Use the glucose meter with a fingertip blood sample, ideally before a meal.",
        why_it_matters_in_spaceflight=(
            "Stress, limited food variety and reduced activity can affect blood sugar regulation."
        ),
    ),
    HealthIndicatorType.BODY_TEMPERATURE: HealthIndicatorReference(
        indicator_type=HealthIndicatorType.BODY_TEMPERATURE,
        display_name="Body temperature",
        unit="degrees Celsius",
        minimum_plausible_value=30,
        maximum_plausible_value=45,
        how_to_measure="Use the contactless or oral thermometer at the same time of day.",
        why_it_matters_in_spaceflight=(
            "Immune changes during long missions make early detection of infection or fever important."
        ),
    ),
    HealthIndicatorType.SLEEP_DURATION: HealthIndicatorReference(
        indicator_type=HealthIndicatorType.SLEEP_DURATION,
        display_name="Sleep duration",
        unit="hours",
        minimum_plausible_value=0,
        maximum_plausible_value=24,
        how_to_measure="Record hours slept from the sleep tracker or note them manually after waking.",
        why_it_matters_in_spaceflight=(
            "Altered light cycles, noise and confinement disturb sleep, which affects performance and mood."
        ),
    ),
    HealthIndicatorType.MOOD_SCORE: HealthIndicatorReference(
        indicator_type=HealthIndicatorType.MOOD_SCORE,
        display_name="Mood score",
        unit="score from 1 (very low) to 10 (very good)",
        minimum_plausible_value=1,
        maximum_plausible_value=10,
        how_to_measure="Rate how you feel right now on the 1 to 10 scale.",
        why_it_matters_in_spaceflight=(
            "Isolation, confinement and distance from Earth are linked to behavioral health risks."
        ),
    ),
}


def get_health_indicator_reference(indicator_type: HealthIndicatorType) -> HealthIndicatorReference:
    """Return the reference entry for an indicator."""
    return HEALTH_INDICATOR_REFERENCES[indicator_type]
