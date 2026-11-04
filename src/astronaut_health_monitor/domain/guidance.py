"""Plain-language guidance shown with every out-of-range reading.

The guidance is general self-care and escalation advice for an educational prototype. It never names
medicines or doses. When a reading is critical the astronaut is always told to contact the flight surgeon.
"""

from dataclasses import dataclass

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType, ValueDirection

FLIGHT_SURGEON_INSTRUCTION = "Contact the flight surgeon (or ground medical support) now and share this reading."


@dataclass(frozen=True)
class GuidanceEntry:
    """Explanation and actions for one indicator that is outside its expected range in one direction."""

    explanation: str
    likely_causes: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    warning_signs_requiring_escalation: str


_BELOW = ValueDirection.BELOW_EXPECTED_RANGE
_ABOVE = ValueDirection.ABOVE_EXPECTED_RANGE

GUIDANCE: dict[tuple[HealthIndicatorType, ValueDirection], GuidanceEntry] = {
    (HealthIndicatorType.HEART_RATE, _ABOVE): GuidanceEntry(
        explanation="Your resting heart rate is higher than expected.",
        likely_causes=(
            "Recent exercise or stress",
            "Caffeine",
            "Dehydration",
            "Fever",
            "Poor sleep",
            "Cardiovascular deconditioning",
        ),
        recommended_actions=(
            "Sit and rest for five minutes, then measure again.",
            "Drink water.",
            "Note any symptoms.",
        ),
        warning_signs_requiring_escalation="Chest pain, fainting, shortness of breath, or dizziness.",
    ),
    (HealthIndicatorType.HEART_RATE, _BELOW): GuidanceEntry(
        explanation="Your resting heart rate is lower than expected.",
        likely_causes=(
            "High fitness (can be normal for trained people)",
            "Medication effects",
            "A heart rhythm problem",
        ),
        recommended_actions=("Measure again after resting.", "Stand up slowly.", "Note any symptoms."),
        warning_signs_requiring_escalation="Dizziness, fainting, unusual fatigue, or chest discomfort.",
    ),
    (HealthIndicatorType.SYSTOLIC_BLOOD_PRESSURE, _ABOVE): GuidanceEntry(
        explanation="Your upper blood pressure number is higher than expected.",
        likely_causes=("Stress", "Salty food", "Fluid shifts in microgravity", "Poor sleep", "Recent exertion"),
        recommended_actions=("Rest seated for five minutes and measure again.", "Drink water.", "Reduce salty food."),
        warning_signs_requiring_escalation="Severe headache, chest pain, vision changes, or weakness on one side.",
    ),
    (HealthIndicatorType.SYSTOLIC_BLOOD_PRESSURE, _BELOW): GuidanceEntry(
        explanation="Your upper blood pressure number is lower than expected.",
        likely_causes=("Dehydration", "Standing up quickly", "Fluid shifts after gravity changes", "Illness"),
        recommended_actions=("Sit or lie down.", "Drink fluids.", "Measure again after resting."),
        warning_signs_requiring_escalation="Fainting, confusion, or cold clammy skin.",
    ),
    (HealthIndicatorType.DIASTOLIC_BLOOD_PRESSURE, _ABOVE): GuidanceEntry(
        explanation="Your lower blood pressure number is higher than expected.",
        likely_causes=("Stress", "Salty food", "Poor sleep", "Recent exertion"),
        recommended_actions=("Rest seated for five minutes and measure again.", "Drink water.", "Reduce salty food."),
        warning_signs_requiring_escalation="Severe headache, chest pain, or vision changes.",
    ),
    (HealthIndicatorType.DIASTOLIC_BLOOD_PRESSURE, _BELOW): GuidanceEntry(
        explanation="Your lower blood pressure number is lower than expected.",
        likely_causes=("Dehydration", "Illness", "Standing up quickly"),
        recommended_actions=("Sit or lie down.", "Drink fluids.", "Measure again after resting."),
        warning_signs_requiring_escalation="Fainting or confusion.",
    ),
    (HealthIndicatorType.BLOOD_GLUCOSE, _ABOVE): GuidanceEntry(
        explanation="Your blood glucose is higher than expected for a fasting or pre-meal reading.",
        likely_causes=("A recent meal", "Stress", "Reduced activity", "Illness"),
        recommended_actions=(
            "Confirm you measured before eating.",
            "Measure again at the next scheduled time.",
            "Drink water.",
        ),
        warning_signs_requiring_escalation="Intense thirst, frequent urination, blurred vision, or nausea.",
    ),
    (HealthIndicatorType.BLOOD_GLUCOSE, _BELOW): GuidanceEntry(
        explanation="Your blood glucose is lower than expected.",
        likely_causes=("Skipped or delayed meal", "Intense exercise", "Illness"),
        recommended_actions=(
            "Eat a quick source of carbohydrate from the food supply.",
            "Measure again in fifteen minutes.",
        ),
        warning_signs_requiring_escalation="Shakiness, confusion, sweating, or difficulty speaking.",
    ),
    (HealthIndicatorType.BODY_TEMPERATURE, _ABOVE): GuidanceEntry(
        explanation="Your body temperature is higher than expected, which can mean infection or overheating.",
        likely_causes=("Infection", "Heat load from exercise or equipment", "Dehydration"),
        recommended_actions=(
            "Rest and drink water.",
            "Measure again in thirty minutes.",
            "Limit close contact with crewmates.",
        ),
        warning_signs_requiring_escalation="Chills, severe headache, cough, or difficulty breathing.",
    ),
    (HealthIndicatorType.BODY_TEMPERATURE, _BELOW): GuidanceEntry(
        explanation="Your body temperature is lower than expected.",
        likely_causes=("Cold cabin or clothing", "Measurement error", "Illness"),
        recommended_actions=("Warm up with clothing or a warm drink.", "Measure again in thirty minutes."),
        warning_signs_requiring_escalation="Persistent shivering, confusion, or drowsiness.",
    ),
    (HealthIndicatorType.SLEEP_DURATION, _BELOW): GuidanceEntry(
        explanation="You slept less than the expected amount, which reduces alertness and mood.",
        likely_causes=("Noise", "Light cycle changes", "Workload", "Stress", "Uncomfortable sleeping position"),
        recommended_actions=(
            "Protect your next scheduled sleep period.",
            "Reduce light and noise.",
            "Avoid caffeine late in the day.",
        ),
        warning_signs_requiring_escalation=(
            "Several poor nights in a row, or trouble staying alert during critical tasks."
        ),
    ),
    (HealthIndicatorType.SLEEP_DURATION, _ABOVE): GuidanceEntry(
        explanation="You slept more than expected, which can be a sign of fatigue or low mood.",
        likely_causes=("Earlier sleep debt", "Illness", "Low mood"),
        recommended_actions=("Keep a regular sleep schedule.", "Note how rested you feel."),
        warning_signs_requiring_escalation="Excessive sleepiness that continues for several days.",
    ),
    (HealthIndicatorType.MOOD_SCORE, _BELOW): GuidanceEntry(
        explanation=(
            "Your mood score is lower than expected. Low mood is common on long missions and is worth acting on early."
        ),
        likely_causes=("Isolation and confinement", "Poor sleep", "Workload", "Distance from family"),
        recommended_actions=(
            "Talk with a crewmate or schedule a call home.",
            "Take a short break or exercise.",
            "Protect your sleep.",
        ),
        warning_signs_requiring_escalation=(
            "Feeling hopeless, losing interest in everything, or thoughts of harming yourself."
        ),
    ),
}


def get_guidance(indicator_type: HealthIndicatorType, direction: ValueDirection) -> GuidanceEntry | None:
    """Return guidance for a direction, or None when the direction cannot occur for the indicator."""
    return GUIDANCE.get((indicator_type, direction))
