"""Object-level checks: may this user touch this particular astronaut's health data?"""

from astronaut_health_monitor.domain.authenticated_user import AuthenticatedUser
from astronaut_health_monitor.domain.enumerations import AuditOutcome
from astronaut_health_monitor.domain.exceptions import PermissionDeniedError
from astronaut_health_monitor.domain.permissions import can_read_health_data_of, can_write_health_data_of
from astronaut_health_monitor.services.audit_service import AuditService


def authorize_health_data_read(user: AuthenticatedUser, astronaut_id: int, audit_service: AuditService) -> None:
    """Refuse (and audit) reading another astronaut's data unless the role allows it; audit permitted cross-reads."""
    if not can_read_health_data_of(user, astronaut_id):
        audit_service.record("health_data.read", AuditOutcome.DENIED, user=user, target=f"astronaut:{astronaut_id}")
        raise PermissionDeniedError("You may only view your own health data.")
    if user.astronaut_id != astronaut_id:
        audit_service.record("health_data.viewed", AuditOutcome.SUCCESS, user=user, target=f"astronaut:{astronaut_id}")


def authorize_health_data_write(user: AuthenticatedUser, astronaut_id: int, audit_service: AuditService) -> None:
    if not can_write_health_data_of(user, astronaut_id):
        audit_service.record("health_data.write", AuditOutcome.DENIED, user=user, target=f"astronaut:{astronaut_id}")
        raise PermissionDeniedError("You may only record your own health data.")
