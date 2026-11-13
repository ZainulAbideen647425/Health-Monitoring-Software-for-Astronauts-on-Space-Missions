from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from astronaut_health_monitor.domain.enumerations import UserRole
from astronaut_health_monitor.domain.exceptions import (
    AccountLockedError,
    AuthenticationFailedError,
    AuthenticationRequiredError,
    InvalidUserDetailsError,
    UserAlreadyExistsError,
)
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.audit_repository import AuditRepository
from astronaut_health_monitor.repositories.user_repository import UserRepository
from astronaut_health_monitor.services.audit_service import AuditService
from astronaut_health_monitor.services.authentication_service import (
    LOCKOUT_DURATION,
    MAXIMUM_FAILED_LOGINS,
    SESSION_ABSOLUTE_LIFETIME,
    SESSION_IDLE_TIMEOUT,
    AuthenticationService,
)

PASSWORD = "a-long-test-passphrase"


class MutableClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, amount: timedelta) -> None:
        self.now += amount


@pytest.fixture
def clock() -> MutableClock:
    return MutableClock()


@pytest.fixture
def service(database_session: Session, clock: MutableClock) -> AuthenticationService:
    return AuthenticationService(
        UserRepository(database_session),
        AstronautRepository(database_session),
        AuditService(AuditRepository(database_session), clock),
        clock,
    )


@pytest.fixture
def astronaut_id(database_session: Session) -> int:
    return AstronautRepository(database_session).add_astronaut("Ada", "Pilot", None).id


def test_new_users_are_validated(service: AuthenticationService, astronaut_id: int) -> None:
    with pytest.raises(InvalidUserDetailsError, match="Username"):
        service.create_user("a b", PASSWORD, UserRole.CLINICIAN, None)
    with pytest.raises(InvalidUserDetailsError, match="at least"):
        service.create_user("doc", "short", UserRole.CLINICIAN, None)
    with pytest.raises(InvalidUserDetailsError, match="linked"):
        service.create_user("ada", PASSWORD, UserRole.ASTRONAUT, None)
    with pytest.raises(InvalidUserDetailsError, match="linked"):
        service.create_user("ada", PASSWORD, UserRole.ASTRONAUT, 999)
    with pytest.raises(InvalidUserDetailsError, match="Only astronaut"):
        service.create_user("doc", PASSWORD, UserRole.CLINICIAN, astronaut_id)


def test_username_is_case_insensitive_and_unique(service: AuthenticationService) -> None:
    service.create_user("Doc.Who", PASSWORD, UserRole.CLINICIAN, None)
    with pytest.raises(UserAlreadyExistsError):
        service.create_user("doc.who", PASSWORD, UserRole.CLINICIAN, None)
    token, user = service.login("DOC.WHO", PASSWORD)
    assert user.username == "doc.who" and token


def test_wrong_username_and_wrong_password_look_identical(service: AuthenticationService) -> None:
    service.create_user("doc", PASSWORD, UserRole.CLINICIAN, None)
    with pytest.raises(AuthenticationFailedError) as wrong_password:
        service.login("doc", "wrong-passphrase-123")
    with pytest.raises(AuthenticationFailedError) as unknown_user:
        service.login("nobody", PASSWORD)
    assert str(wrong_password.value) == str(unknown_user.value) == "Invalid username or password."


def test_account_locks_after_repeated_failures_and_unlocks_later(
    service: AuthenticationService, clock: MutableClock
) -> None:
    service.create_user("doc", PASSWORD, UserRole.CLINICIAN, None)
    for _ in range(MAXIMUM_FAILED_LOGINS):
        with pytest.raises(AuthenticationFailedError):
            service.login("doc", "wrong-passphrase-123")
    with pytest.raises(AccountLockedError):
        service.login("doc", PASSWORD)  # even the right password is refused while locked
    clock.advance(LOCKOUT_DURATION + timedelta(seconds=1))
    token, _ = service.login("doc", PASSWORD)
    assert token


def test_successful_login_resets_the_failure_counter(service: AuthenticationService) -> None:
    service.create_user("doc", PASSWORD, UserRole.CLINICIAN, None)
    for _ in range(MAXIMUM_FAILED_LOGINS - 1):
        with pytest.raises(AuthenticationFailedError):
            service.login("doc", "wrong-passphrase-123")
    service.login("doc", PASSWORD)
    for _ in range(MAXIMUM_FAILED_LOGINS - 1):
        with pytest.raises(AuthenticationFailedError):
            service.login("doc", "wrong-passphrase-123")
    service.login("doc", PASSWORD)  # still not locked


def test_session_token_authenticates_and_only_its_hash_is_stored(
    service: AuthenticationService, database_session: Session
) -> None:
    service.create_user("doc", PASSWORD, UserRole.CLINICIAN, None)
    token, _ = service.login("doc", PASSWORD)
    assert service.authenticate(token).username == "doc"
    stored: str = database_session.execute(text("SELECT token_hash FROM user_sessions")).scalar_one()
    assert stored != token and token not in stored


@pytest.mark.parametrize("bad_token", [None, "", "not-a-real-token"])
def test_missing_or_unknown_tokens_are_refused(service: AuthenticationService, bad_token: str | None) -> None:
    with pytest.raises(AuthenticationRequiredError):
        service.authenticate(bad_token)


def test_session_ends_after_idle_timeout_but_activity_keeps_it_alive(
    service: AuthenticationService, clock: MutableClock
) -> None:
    service.create_user("doc", PASSWORD, UserRole.CLINICIAN, None)
    token, _ = service.login("doc", PASSWORD)
    for _ in range(3):
        clock.advance(SESSION_IDLE_TIMEOUT - timedelta(minutes=1))
        service.authenticate(token)  # active use extends the idle window
    clock.advance(SESSION_IDLE_TIMEOUT + timedelta(seconds=1))
    with pytest.raises(AuthenticationRequiredError):
        service.authenticate(token)


def test_session_ends_after_its_absolute_lifetime_even_if_active(
    service: AuthenticationService, clock: MutableClock
) -> None:
    service.create_user("doc", PASSWORD, UserRole.CLINICIAN, None)
    token, _ = service.login("doc", PASSWORD)
    elapsed = timedelta()
    while elapsed + timedelta(minutes=20) < SESSION_ABSOLUTE_LIFETIME:
        clock.advance(timedelta(minutes=20))
        elapsed += timedelta(minutes=20)
        service.authenticate(token)
    clock.advance(timedelta(minutes=21))
    with pytest.raises(AuthenticationRequiredError):
        service.authenticate(token)


def test_logout_ends_the_session_for_good(service: AuthenticationService) -> None:
    service.create_user("doc", PASSWORD, UserRole.CLINICIAN, None)
    token, _ = service.login("doc", PASSWORD)
    service.logout(token)
    with pytest.raises(AuthenticationRequiredError):
        service.authenticate(token)
    service.logout(token)  # logging out twice is harmless
    service.logout(None)


def test_deactivated_users_cannot_sign_in_or_keep_a_session(
    service: AuthenticationService, database_session: Session
) -> None:
    service.create_user("doc", PASSWORD, UserRole.CLINICIAN, None)
    token, _ = service.login("doc", PASSWORD)
    database_session.execute(text("UPDATE users SET is_active = 0"))
    database_session.commit()
    with pytest.raises(AuthenticationRequiredError):
        service.authenticate(token)
    with pytest.raises(AuthenticationFailedError):
        service.login("doc", PASSWORD)
