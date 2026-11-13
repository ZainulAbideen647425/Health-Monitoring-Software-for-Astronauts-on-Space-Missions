"""The signed-in person making a request."""

from dataclasses import dataclass

from astronaut_health_monitor.domain.enumerations import UserRole


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    username: str
    role: UserRole
    astronaut_id: int | None
