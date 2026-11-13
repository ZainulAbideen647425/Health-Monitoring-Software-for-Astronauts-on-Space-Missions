"""Who may do what. Pure rules with no database, so they are easy to test exhaustively.

astronaut        reads and writes only their own health data
clinician        reads and writes health data of every crew member
mission_control  everything a clinician can do, plus managing missions, crew, users and reading the audit log
"""

from enum import StrEnum

from astronaut_health_monitor.domain.authenticated_user import AuthenticatedUser
from astronaut_health_monitor.domain.enumerations import UserRole


class Permission(StrEnum):
    READ_OWN_HEALTH_DATA = "read_own_health_data"
    WRITE_OWN_HEALTH_DATA = "write_own_health_data"
    READ_ALL_HEALTH_DATA = "read_all_health_data"
    WRITE_ALL_HEALTH_DATA = "write_all_health_data"
    MANAGE_MISSIONS_AND_CREW = "manage_missions_and_crew"
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOG = "view_audit_log"


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ASTRONAUT: frozenset({Permission.READ_OWN_HEALTH_DATA, Permission.WRITE_OWN_HEALTH_DATA}),
    UserRole.CLINICIAN: frozenset(
        {
            Permission.READ_OWN_HEALTH_DATA,
            Permission.WRITE_OWN_HEALTH_DATA,
            Permission.READ_ALL_HEALTH_DATA,
            Permission.WRITE_ALL_HEALTH_DATA,
        }
    ),
    UserRole.MISSION_CONTROL: frozenset(Permission),
}


def has_permission(user: AuthenticatedUser, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[user.role]


def can_read_health_data_of(user: AuthenticatedUser, astronaut_id: int) -> bool:
    if has_permission(user, Permission.READ_ALL_HEALTH_DATA):
        return True
    return has_permission(user, Permission.READ_OWN_HEALTH_DATA) and user.astronaut_id == astronaut_id


def can_write_health_data_of(user: AuthenticatedUser, astronaut_id: int) -> bool:
    if has_permission(user, Permission.WRITE_ALL_HEALTH_DATA):
        return True
    return has_permission(user, Permission.WRITE_OWN_HEALTH_DATA) and user.astronaut_id == astronaut_id
