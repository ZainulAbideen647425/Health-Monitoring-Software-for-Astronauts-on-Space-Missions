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
