"""Database access for users and their sign-in sessions."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from astronaut_health_monitor.domain.exceptions import UserAlreadyExistsError
from astronaut_health_monitor.repositories.database_records import SessionRecord, UserRecord


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_user(self, username: str, password_hash: str, role: str, astronaut_id: int | None) -> UserRecord:
        record = UserRecord(username=username, password_hash=password_hash, role=role, astronaut_id=astronaut_id)
        self._session.add(record)
        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            raise UserAlreadyExistsError(f"User {username!r} already exists.") from error
        return record

    def get_user_by_username(self, username: str) -> UserRecord | None:
        return self._session.scalar(select(UserRecord).where(UserRecord.username == username))

    def get_user_by_id(self, user_id: int) -> UserRecord | None:
        return self._session.get(UserRecord, user_id)

    def list_users(self) -> list[UserRecord]:
        return list(self._session.scalars(select(UserRecord).order_by(UserRecord.id)))

    def save_login_state(self, user: UserRecord, failed_attempts: int, locked_until: datetime | None) -> None:
        user.failed_login_attempts = failed_attempts
        user.locked_until = locked_until
        self._session.commit()

    def add_session(self, token_hash: str, user_id: int, created_at: datetime, expires_at: datetime) -> SessionRecord:
        record = SessionRecord(
            token_hash=token_hash,
            user_id=user_id,
            created_at=created_at,
            last_seen_at=created_at,
            expires_at=expires_at,
        )
        self._session.add(record)
        self._session.commit()
        return record

    def get_session_by_token_hash(self, token_hash: str) -> SessionRecord | None:
        return self._session.scalar(select(SessionRecord).where(SessionRecord.token_hash == token_hash))

    def touch_session(self, record: SessionRecord, seen_at: datetime) -> None:
        record.last_seen_at = seen_at
        self._session.commit()

    def revoke_session(self, record: SessionRecord, revoked_at: datetime) -> None:
        record.revoked_at = revoked_at
        self._session.commit()
