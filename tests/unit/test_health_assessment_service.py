from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from astronaut_health_monitor.domain.enumerations import (
    HealthIndicatorType,
    HealthStatus,
    TrendDirection,
    ValueDirection,
)
from astronaut_health_monitor.domain.exceptions import AstronautNotFoundError, MeasurementNotFoundError
from astronaut_health_monitor.domain.guidance import FLIGHT_SURGEON_INSTRUCTION
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.database_records import MeasurementRecord
from astronaut_health_monitor.repositories.measurement_repository import MeasurementRepository
from astronaut_health_monitor.services.health_assessment_service import HealthAssessmentService

START_OF_HISTORY = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)


@pytest.fixture
def astronaut_id(database_session: Session) -> int:
    return AstronautRepository(database_session).add_astronaut("Test Astronaut", "Flight Engineer", None).id


@pytest.fixture
def service(database_session: Session) -> HealthAssessmentService:
    return HealthAssessmentService(MeasurementRepository(database_session), AstronautRepository(database_session))


def add_reading(
    session: Session,
    astronaut_id: int,
    value: float,
    day: int,
    indicator: HealthIndicatorType = HealthIndicatorType.HEART_RATE,
) -> MeasurementRecord:
    return MeasurementRepository(session).add_measurement(
        astronaut_id=astronaut_id,
        indicator_type=indicator.value,
        measured_value=value,
        measurement_unit="unit",
        measured_at=START_OF_HISTORY + timedelta(days=day),
        measurement_source="manual_entry",
        device_id=None,
        notes=None,
    )


def test_normal_reading_without_history(
    database_session: Session, astronaut_id: int, service: HealthAssessmentService
) -> None:
    reading = add_reading(database_session, astronaut_id, 72, day=0)
    assessment = service.assess_measurement(reading.id)
    assert assessment.final_status is HealthStatus.NORMAL
    assert assessment.value_direction is ValueDirection.WITHIN_EXPECTED_RANGE
    assert assessment.contact_flight_surgeon is False
    assert assessment.status_reasons == ()
    assert assessment.recommended_actions == ("Keep measuring on your routine schedule.",)
    assert assessment.personal_baseline.has_enough_history is False
    assert assessment.headline == "Heart rate is within the expected range"


def test_caution_reading_gets_guidance_and_reason(
    database_session: Session, astronaut_id: int, service: HealthAssessmentService
) -> None:
    reading = add_reading(database_session, astronaut_id, 110, day=0)
    assessment = service.assess_measurement(reading.id)
    assert assessment.final_status is HealthStatus.CAUTION
    assert assessment.value_direction is ValueDirection.ABOVE_EXPECTED_RANGE
    assert assessment.contact_flight_surgeon is False
    assert "above the expected range of 50 to 100" in assessment.status_reasons[0]
    assert any("rest" in action.lower() for action in assessment.recommended_actions)
    assert assessment.warning_signs_requiring_escalation


def test_critical_reading_tells_astronaut_to_contact_flight_surgeon_first(
    database_session: Session, astronaut_id: int, service: HealthAssessmentService
) -> None:
    reading = add_reading(database_session, astronaut_id, 130, day=0)
    assessment = service.assess_measurement(reading.id)
    assert assessment.final_status is HealthStatus.CRITICAL
    assert assessment.contact_flight_surgeon is True
    assert assessment.recommended_actions[0] == FLIGHT_SURGEON_INSTRUCTION
    assert assessment.headline == "Heart rate needs urgent attention"


def test_in_range_value_that_is_unusual_for_the_astronaut_becomes_caution(
    database_session: Session, astronaut_id: int, service: HealthAssessmentService
) -> None:
    for day in range(6):
        add_reading(database_session, astronaut_id, 60 + (day % 2), day)
    unusual = add_reading(database_session, astronaut_id, 80, day=6)  # 80 bpm is normal for most people
    assessment = service.assess_measurement(unusual.id)
    assert assessment.rule_status is HealthStatus.NORMAL
    assert assessment.final_status is HealthStatus.CAUTION
    assert assessment.personal_baseline.is_unusual_for_this_astronaut is True
    assert assessment.personal_baseline.has_enough_history is True
    assert assessment.headline == "Heart rate is in range but unusual for you"
    assert any("usual average" in reason for reason in assessment.status_reasons)
    assert len(assessment.recommended_actions) == 3


def test_steady_rise_inside_normal_range_is_flagged_as_trend(
    database_session: Session, astronaut_id: int, service: HealthAssessmentService
) -> None:
    last = None
    for day, value in enumerate([60, 63, 66, 69, 72]):
        last = add_reading(database_session, astronaut_id, value, day)
    assert last is not None
    assessment = service.assess_measurement(last.id)
    assert assessment.rule_status is HealthStatus.NORMAL
    assert assessment.personal_baseline.trend is TrendDirection.RISING
    assert assessment.final_status is HealthStatus.CAUTION
    assert any("rising trend" in reason for reason in assessment.status_reasons)


def test_assessment_ignores_readings_taken_after_the_one_being_assessed(
    database_session: Session, astronaut_id: int, service: HealthAssessmentService
) -> None:
    early = add_reading(database_session, astronaut_id, 62, day=0)
    for day in range(1, 8):
        add_reading(database_session, astronaut_id, 95, day)
    assessment = service.assess_measurement(early.id)
    assert assessment.personal_baseline.sample_count == 0
    assert assessment.personal_baseline.has_enough_history is False


def test_unknown_measurement_is_reported(service: HealthAssessmentService) -> None:
    with pytest.raises(MeasurementNotFoundError):
        service.assess_measurement(12345)


def test_summary_uses_latest_reading_per_indicator_and_worst_status(
    database_session: Session, astronaut_id: int, service: HealthAssessmentService
) -> None:
    add_reading(database_session, astronaut_id, 130, day=0)  # older critical reading
    add_reading(database_session, astronaut_id, 70, day=1)  # latest heart rate is fine
    add_reading(database_session, astronaut_id, 3, day=1, indicator=HealthIndicatorType.MOOD_SCORE)  # critical mood
    summary = service.summarize_astronaut_health(astronaut_id)
    by_indicator = {a.indicator_type: a for a in summary.assessments}
    assert set(by_indicator) == {HealthIndicatorType.HEART_RATE, HealthIndicatorType.MOOD_SCORE}
    assert by_indicator[HealthIndicatorType.HEART_RATE].measured_value == 70
    assert summary.overall_status is HealthStatus.CRITICAL
    assert summary.contact_flight_surgeon is True


def test_summary_without_readings_is_normal_and_empty(astronaut_id: int, service: HealthAssessmentService) -> None:
    summary = service.summarize_astronaut_health(astronaut_id)
    assert summary.overall_status is HealthStatus.NORMAL
    assert summary.assessments == ()
    assert summary.contact_flight_surgeon is False


def test_summary_for_unknown_astronaut_is_reported(service: HealthAssessmentService) -> None:
    with pytest.raises(AstronautNotFoundError):
        service.summarize_astronaut_health(999)
