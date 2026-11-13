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


def _simulated_value(day_index: int, indicator: HealthIndicatorType) -> float:
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
    return float(values[indicator])


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

    def seed_sample_crew_member(self) -> AstronautRecord:
        """Create one simulated astronaut with 14 days of readings for every indicator."""
        astronaut = self._astronaut_service.register_astronaut("Demo Astronaut", "Commander", None)
        batch_id = uuid.uuid4().hex[:12]
        now = datetime.now(UTC)
        counter = 0
        for days_ago in range(14, 0, -1):
            day_index = 14 - days_ago
            for indicator in HealthIndicatorType:
                self._measurement_service.record_measurement(
                    astronaut_id=astronaut.id,
                    indicator_type=indicator,
                    measured_value=_simulated_value(day_index, indicator),
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
