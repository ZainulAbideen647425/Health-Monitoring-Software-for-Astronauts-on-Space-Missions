"""Sample data for demonstrations. Clearly labelled as simulated everywhere it is stored."""

import uuid
from datetime import UTC, datetime, timedelta

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType, MeasurementSource, UserRole
from astronaut_health_monitor.repositories.database_records import AstronautRecord
from astronaut_health_monitor.services.astronaut_service import AstronautService
from astronaut_health_monitor.services.authentication_service import AuthenticationService
from astronaut_health_monitor.services.measurement_service import MeasurementService

SIMULATED_DATA_LABEL = "Simulated sample data"
# Demo accounts exist only when demo mode is switched on. The password is public, so never use demo mode for real data.
DEMO_PASSWORD = "Demo-Passphrase-2026!"
DEMO_ASTRONAUT_USERNAME = "astronaut.demo"
DEMO_CLINICIAN_USERNAME = "clinician.demo"
DEMO_MISSION_CONTROL_USERNAME = "control.demo"


# Qualitative, illustrative shifts so each mission environment loads a different simulated crew member.
# They are not physiological predictions and the data is always labelled as simulated.
ENVIRONMENT_SHORT_NAMES: dict[str, str] = {
    "station": "Space station",
    "transit": "Deep-space transit",
    "rover": "Pressurized rover",
    "moon": "Lunar base",
    "mars": "Mars base",
}
_ENVIRONMENT_SHIFTS: dict[str, dict[HealthIndicatorType, float]] = {
    "station": {},
    "transit": {
        HealthIndicatorType.STRESS_LEVEL: 1.5,
        HealthIndicatorType.FATIGUE_LEVEL: 1.0,
        HealthIndicatorType.SLEEP_DURATION: -0.5,
        HealthIndicatorType.MOOD_SCORE: -0.5,
        HealthIndicatorType.PHYSICAL_ACTIVITY: -20,
        HealthIndicatorType.HEART_RATE: 2,
    },
    "rover": {
        HealthIndicatorType.STRESS_LEVEL: 1.0,
        HealthIndicatorType.FATIGUE_LEVEL: 1.5,
        HealthIndicatorType.SLEEP_DURATION: -0.3,
        HealthIndicatorType.PHYSICAL_ACTIVITY: -10,
        HealthIndicatorType.HEART_RATE: 4,
        HealthIndicatorType.BODY_TEMPERATURE: 0.2,
    },
    "moon": {
        HealthIndicatorType.STRESS_LEVEL: 0.5,
        HealthIndicatorType.FATIGUE_LEVEL: 0.5,
        HealthIndicatorType.SLEEP_DURATION: -0.3,
        HealthIndicatorType.PHYSICAL_ACTIVITY: 15,
        HealthIndicatorType.HEART_RATE: 1,
    },
    "mars": {
        HealthIndicatorType.STRESS_LEVEL: 2.0,
        HealthIndicatorType.FATIGUE_LEVEL: 1.5,
        HealthIndicatorType.SLEEP_DURATION: -0.6,
        HealthIndicatorType.MOOD_SCORE: -1.0,
        HealthIndicatorType.PHYSICAL_ACTIVITY: 5,
        HealthIndicatorType.HEART_RATE: 2,
        HealthIndicatorType.BLOOD_GLUCOSE: 2,
    },
}
_SCORE_INDICATORS = (
    HealthIndicatorType.MOOD_SCORE,
    HealthIndicatorType.FATIGUE_LEVEL,
    HealthIndicatorType.STRESS_LEVEL,
)


def _simulated_value(day_index: int, indicator: HealthIndicatorType, environment: str = "station") -> float:
    """14 days of mostly steady values, with heart rate rising and sleep and mood falling at the end."""
    late = max(day_index - 9, 0)
    values = {
        HealthIndicatorType.HEART_RATE: 60 + (day_index % 2) + late * 3,
        HealthIndicatorType.SYSTOLIC_BLOOD_PRESSURE: 114 + day_index % 3,
        HealthIndicatorType.DIASTOLIC_BLOOD_PRESSURE: 72 + day_index % 2,
        HealthIndicatorType.BLOOD_GLUCOSE: 88 + day_index % 4,
        HealthIndicatorType.BODY_TEMPERATURE: 36.6 + (day_index % 3) / 10,
        HealthIndicatorType.SLEEP_DURATION: 7.5 - late * 0.8 if late else 7.6,
        HealthIndicatorType.MOOD_SCORE: 8 - late,
        HealthIndicatorType.FATIGUE_LEVEL: 3 + late,
        HealthIndicatorType.STRESS_LEVEL: 3 + (day_index % 2) + (late // 2),
        HealthIndicatorType.PHYSICAL_ACTIVITY: 120 - late * 10 + (day_index % 3) * 5,
    }
    value = float(values[indicator]) + _ENVIRONMENT_SHIFTS[environment].get(indicator, 0.0)
    if indicator in _SCORE_INDICATORS:
        value = min(10.0, max(1.0, value))
    if indicator is HealthIndicatorType.SLEEP_DURATION:
        value = max(3.0, value)
    return round(value, 1)


class DemoDataService:
    def __init__(
        self,
        astronaut_service: AstronautService,
        measurement_service: MeasurementService,
        authentication_service: AuthenticationService,
    ) -> None:
        self._astronaut_service = astronaut_service
        self._measurement_service = measurement_service
        self._authentication_service = authentication_service

    def seed_sample_crew_member(self, environment: str = "station") -> AstronautRecord:
        """Create one simulated astronaut with 14 days of readings for every indicator, shaped by the environment."""
        if environment not in ENVIRONMENT_SHORT_NAMES:
            raise ValueError(f"Unknown mission environment: {environment}")
        name = (
            "Demo Astronaut" if environment == "station" else f"Demo Astronaut ({ENVIRONMENT_SHORT_NAMES[environment]})"
        )
        astronaut = self._astronaut_service.register_astronaut(name, "Commander", None)
        batch_id = uuid.uuid4().hex[:12]
        now = datetime.now(UTC)
        counter = 0
        for days_ago in range(14, 0, -1):
            day_index = 14 - days_ago
            for indicator in HealthIndicatorType:
                self._measurement_service.record_measurement(
                    astronaut_id=astronaut.id,
                    indicator_type=indicator,
                    measured_value=_simulated_value(day_index, indicator, environment),
                    measured_at=now - timedelta(days=days_ago, seconds=counter),
                    measurement_source=MeasurementSource.MANUAL_ENTRY,
                    notes=SIMULATED_DATA_LABEL,
                    client_reference=f"demo-{batch_id}-{counter}",
                )
                counter += 1
        return astronaut

    def seed_demo_environment(self) -> None:
        """Sample astronaut plus one demo account for each role."""
        astronaut = self.seed_sample_crew_member()
        self._authentication_service.create_user(
            DEMO_ASTRONAUT_USERNAME, DEMO_PASSWORD, UserRole.ASTRONAUT, astronaut.id
        )
        self._authentication_service.create_user(DEMO_CLINICIAN_USERNAME, DEMO_PASSWORD, UserRole.CLINICIAN, None)
        self._authentication_service.create_user(
            DEMO_MISSION_CONTROL_USERNAME, DEMO_PASSWORD, UserRole.MISSION_CONTROL, None
        )
