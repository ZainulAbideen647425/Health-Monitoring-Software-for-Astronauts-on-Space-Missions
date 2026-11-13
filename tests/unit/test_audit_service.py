from sqlalchemy import text
from sqlalchemy.orm import Session

from astronaut_health_monitor.domain.authenticated_user import AuthenticatedUser
from astronaut_health_monitor.domain.enumerations import AuditOutcome, UserRole
from astronaut_health_monitor.repositories.audit_repository import AuditRepository
from astronaut_health_monitor.services.audit_service import GENESIS_HASH, AuditService

USER = AuthenticatedUser(1, "doc", UserRole.CLINICIAN, None)


def filled_log(session: Session, count: int = 4) -> AuditService:
    service = AuditService(AuditRepository(session))
    for index in range(count):
        service.record(f"action.{index}", user=USER, target=f"astronaut:{index}", detail="note")
    return service


def test_empty_log_is_valid(database_session: Session) -> None:
    verification = AuditService(AuditRepository(database_session)).verify_chain()
    assert verification.is_valid and verification.checked_event_count == 0


def test_each_entry_is_linked_to_the_previous_one(database_session: Session) -> None:
    service = filled_log(database_session)
    events = AuditRepository(database_session).list_all_events_oldest_first()
    assert events[0].previous_hash == GENESIS_HASH
    for earlier, later in zip(events, events[1:], strict=False):
        assert later.previous_hash == earlier.event_hash
    assert service.verify_chain().is_valid
    assert service.verify_chain().checked_event_count == 4


def test_changing_an_old_entry_is_detected_at_that_entry(database_session: Session) -> None:
    service = filled_log(database_session)
    database_session.execute(text("UPDATE audit_events SET target = 'astronaut:999' WHERE id = 2"))
    database_session.commit()
    verification = service.verify_chain()
    assert verification.is_valid is False
    assert verification.first_broken_event_id == 2


def test_deleting_an_entry_is_detected(database_session: Session) -> None:
    service = filled_log(database_session)
    database_session.execute(text("DELETE FROM audit_events WHERE id = 2"))
    database_session.commit()
    verification = service.verify_chain()
    assert verification.is_valid is False
    assert verification.first_broken_event_id == 3


def test_outcomes_and_anonymous_actors_are_recorded(database_session: Session) -> None:
    service = AuditService(AuditRepository(database_session))
    event = service.record("login", AuditOutcome.FAILED, username="intruder", detail="wrong password")
    assert event.username == "intruder" and event.user_role is None and event.outcome == "failed"
    assert service.list_recent_events(10)[0].id == event.id
