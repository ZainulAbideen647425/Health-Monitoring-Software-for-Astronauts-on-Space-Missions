import pytest

from astronaut_health_monitor.domain.authenticated_user import AuthenticatedUser
from astronaut_health_monitor.domain.enumerations import UserRole
from astronaut_health_monitor.domain.permissions import (
    Permission,
    can_read_health_data_of,
    can_write_health_data_of,
    has_permission,
)

ASTRONAUT = AuthenticatedUser(1, "ada", UserRole.ASTRONAUT, astronaut_id=10)
CLINICIAN = AuthenticatedUser(2, "doc", UserRole.CLINICIAN, astronaut_id=None)
CONTROL = AuthenticatedUser(3, "ctrl", UserRole.MISSION_CONTROL, astronaut_id=None)


@pytest.mark.parametrize(
    ("user", "target_astronaut_id", "can_read", "can_write"),
    [
        (ASTRONAUT, 10, True, True),
        (ASTRONAUT, 11, False, False),
        (CLINICIAN, 10, True, True),
        (CLINICIAN, 11, True, True),
        (CONTROL, 10, True, True),
        (CONTROL, 999, True, True),
    ],
)
def test_health_data_access_matrix(
    user: AuthenticatedUser, target_astronaut_id: int, can_read: bool, can_write: bool
) -> None:
    assert can_read_health_data_of(user, target_astronaut_id) is can_read
    assert can_write_health_data_of(user, target_astronaut_id) is can_write


@pytest.mark.parametrize(
    ("user", "permission", "allowed"),
    [
        (ASTRONAUT, Permission.MANAGE_USERS, False),
        (ASTRONAUT, Permission.VIEW_AUDIT_LOG, False),
        (ASTRONAUT, Permission.MANAGE_MISSIONS_AND_CREW, False),
        (CLINICIAN, Permission.MANAGE_USERS, False),
        (CLINICIAN, Permission.VIEW_AUDIT_LOG, False),
        (CLINICIAN, Permission.MANAGE_MISSIONS_AND_CREW, False),
        (CONTROL, Permission.MANAGE_USERS, True),
        (CONTROL, Permission.VIEW_AUDIT_LOG, True),
        (CONTROL, Permission.MANAGE_MISSIONS_AND_CREW, True),
    ],
)
def test_administrative_permissions(user: AuthenticatedUser, permission: Permission, allowed: bool) -> None:
    assert has_permission(user, permission) is allowed


def test_an_astronaut_account_without_a_linked_astronaut_can_see_nothing() -> None:
    unlinked = AuthenticatedUser(4, "orphan", UserRole.ASTRONAUT, astronaut_id=None)
    assert not can_read_health_data_of(unlinked, 10)
    assert not can_write_health_data_of(unlinked, 10)
