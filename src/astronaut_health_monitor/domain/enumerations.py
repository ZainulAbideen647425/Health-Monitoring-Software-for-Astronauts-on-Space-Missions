"""Fixed vocabularies used across the Astronaut Health Monitor."""

from enum import StrEnum


class HealthIndicatorType(StrEnum):
    """Health indicators that an astronaut can measure and record."""

    HEART_RATE = "heart_rate"
    SYSTOLIC_BLOOD_PRESSURE = "systolic_blood_pressure"
    DIASTOLIC_BLOOD_PRESSURE = "diastolic_blood_pressure"
    BLOOD_GLUCOSE = "blood_glucose"
    BODY_TEMPERATURE = "body_temperature"
    SLEEP_DURATION = "sleep_duration"
    MOOD_SCORE = "mood_score"
    FATIGUE_LEVEL = "fatigue_level"
    STRESS_LEVEL = "stress_level"
    PHYSICAL_ACTIVITY = "physical_activity"


class MissionEnvironment(StrEnum):
    """Place where the astronaut lives and works during the mission."""

    SPACECRAFT = "spacecraft"
    SPACE_STATION = "space_station"
    LUNAR_BASE = "lunar_base"
    MARS_BASE = "mars_base"
    ROVER = "rover"


class MeasurementSource(StrEnum):
    """How a measurement value entered the system."""

    MANUAL_ENTRY = "manual_entry"
    WEARABLE_DEVICE = "wearable_device"
    MEDICAL_DEVICE = "medical_device"
    CAMERA_ANALYSIS = "camera_analysis"


class DeviceKind(StrEnum):
    """Category of measuring device."""

    WEARABLE_SENSOR = "wearable_sensor"
    BLOOD_PRESSURE_MONITOR = "blood_pressure_monitor"
    GLUCOSE_METER = "glucose_meter"
    THERMOMETER = "thermometer"
    SLEEP_TRACKER = "sleep_tracker"


class HealthStatus(StrEnum):
    """How a reading compares with the expected range. Ordered from best to worst."""

    NORMAL = "normal"
    CAUTION = "caution"
    CRITICAL = "critical"


class ValueDirection(StrEnum):
    """Where a value lies relative to the expected range."""

    BELOW_EXPECTED_RANGE = "below_expected_range"
    WITHIN_EXPECTED_RANGE = "within_expected_range"
    ABOVE_EXPECTED_RANGE = "above_expected_range"


class TrendDirection(StrEnum):
    """Direction in which recent readings are moving."""

    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"


class BatchItemOutcome(StrEnum):
    """What happened to one measurement in a synchronization batch."""

    CREATED = "created"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


class UserRole(StrEnum):
    """What a signed-in person is allowed to do."""

    ASTRONAUT = "astronaut"
    CLINICIAN = "clinician"
    MISSION_CONTROL = "mission_control"


class AuditOutcome(StrEnum):
    """Result of an action that was written to the audit log."""

    SUCCESS = "success"
    DENIED = "denied"
    FAILED = "failed"
