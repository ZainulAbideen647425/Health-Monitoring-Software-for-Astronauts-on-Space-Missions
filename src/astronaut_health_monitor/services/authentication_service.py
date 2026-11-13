"""Sign-in, sign-out, session checking and user creation."""

import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from astronaut_health_monitor.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    validate_password_strength,
    verify_password,
)
from astronaut_health_monitor.domain.authenticated_user import AuthenticatedUser
from astronaut_health_monitor.domain.enumerations import AuditOutcome, UserRole
from astronaut_health_monitor.domain.exceptions import (
    AccountLockedError,
    AuthenticationFailedError,
    AuthenticationRequiredError,
    InvalidUserDetailsError,
)
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.database_records import UserRecord
from astronaut_health_monitor.repositories.user_repository import UserRepository
from astronaut_health_monitor.services.audit_service import AuditService

MAXIMUM_FAILED_LOGINS = 5
LOCKOUT_DURATION = timedelta(minutes=15)
SESSION_ABSOLUTE_LIFETIME = timedelta(hours=8)
SESSION_IDLE_TIMEOUT = timedelta(minutes=30)
USERNAME_PATTERN = re.compile(r"^[a-z0-9._-]{3,64}$")
GENERIC_LOGIN_ERROR = "Invalid username or password."

# Checked when the username does not exist, so a wrong username takes as long as a wrong password.
_DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing-only")


class AuthenticationService:
    def __init__(
        self,
        user_repository: UserRepository,
        astronaut_repository: AstronautRepository,
        audit_service: AuditService,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._user_repository = user_repository
        self._astronaut_repository = astronaut_repository
        self._audit_service = audit_service
        self._clock = clock or (lambda: datetime.now(UTC))

    def create_user(self, username: str, password: str, role: UserRole, astronaut_id: int | None) -> UserRecord:
        username = username.strip().lower()
        if not USERNAME_PATTERN.match(username):
            raise InvalidUserDetailsError(
                "Username must be 3 to 64 characters: letters, digits, dot, dash or underscore."
            )
        validate_password_strength(password)
        if role is UserRole.ASTRONAUT:
            if astronaut_id is None or self._astronaut_repository.get_astronaut_by_id(astronaut_id) is None:
                raise InvalidUserDetailsError("An astronaut account must be linked to an existing astronaut.")
        elif astronaut_id is not None:
            raise InvalidUserDetailsError("Only astronaut accounts can be linked to an astronaut.")
        return self._user_repository.add_user(username, hash_password(password), role.value, astronaut_id)

    def login(self, username: str, password: str) -> tuple[str, AuthenticatedUser]:
        """Check the credentials and start a session. Returns the session token and the user."""
        username = username.strip().lower()
        now = self._clock()
        user = self._user_repository.get_user_by_username(username)
        if user is None:
            verify_password(password, _DUMMY_PASSWORD_HASH)
            self._audit_service.record("login", AuditOutcome.FAILED, username=username, detail="unknown user")
            raise AuthenticationFailedError(GENERIC_LOGIN_ERROR)
        if user.locked_until is not None and user.locked_until > now:
            self._audit_service.record("login", AuditOutcome.DENIED, username=username, detail="account locked")
            raise AccountLockedError("Too many wrong attempts. Try again in a few minutes.")
        if not user.is_active or not verify_password(password, user.password_hash):
            attempts = user.failed_login_attempts + 1
            locked_until = now + LOCKOUT_DURATION if attempts >= MAXIMUM_FAILED_LOGINS else None
            self._user_repository.save_login_state(user, 0 if locked_until else attempts, locked_until)
            detail = "account locked after repeated failures" if locked_until else "wrong password"
            self._audit_service.record("login", AuditOutcome.FAILED, username=username, detail=detail)
            raise AuthenticationFailedError(GENERIC_LOGIN_ERROR)

        self._user_repository.save_login_state(user, 0, None)
        token = generate_session_token()
        self._user_repository.add_session(hash_session_token(token), user.id, now, now + SESSION_ABSOLUTE_LIFETIME)
        authenticated = self._to_authenticated_user(user)
        self._audit_service.record("login", AuditOutcome.SUCCESS, user=authenticated)
        return token, authenticated

    def authenticate(self, token: str | None) -> AuthenticatedUser:
        """Return the user for a session token, or raise AuthenticationRequiredError."""
        if not token:
            raise AuthenticationRequiredError("Sign in to continue.")
        session_record = self._user_repository.get_session_by_token_hash(hash_session_token(token))
        now = self._clock()
        if (
            session_record is None
            or session_record.revoked_at is not None
            or session_record.expires_at <= now
            or session_record.last_seen_at + SESSION_IDLE_TIMEOUT <= now
        ):
            raise AuthenticationRequiredError("Your session has ended. Please sign in again.")
        user = self._user_repository.get_user_by_id(session_record.user_id)
        if user is None or not user.is_active:
            raise AuthenticationRequiredError("Your session has ended. Please sign in again.")
        self._user_repository.touch_session(session_record, now)
        return self._to_authenticated_user(user)

    def logout(self, token: str | None) -> None:
        if not token:
            return
        session_record = self._user_repository.get_session_by_token_hash(hash_session_token(token))
        if session_record is None or session_record.revoked_at is not None:
            return
        user = self._user_repository.get_user_by_id(session_record.user_id)
        self._user_repository.revoke_session(session_record, self._clock())
        if user is not None:
            self._audit_service.record("logout", AuditOutcome.SUCCESS, user=self._to_authenticated_user(user))

    @staticmethod
    def _to_authenticated_user(user: UserRecord) -> AuthenticatedUser:
        return AuthenticatedUser(user.id, user.username, UserRole(user.role), user.astronaut_id)
