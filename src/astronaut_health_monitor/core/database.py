"""Database engine, session handling and a timezone-safe timestamp column type."""

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, create_engine
from sqlalchemy.engine import Dialect, Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator


class DatabaseBase(DeclarativeBase):
    """Base class for all database table definitions."""


class UtcDateTime(TypeDecorator[datetime]):
    """Stores timestamps as UTC and always returns timezone-aware UTC values (SQLite drops timezones)."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Timestamps must include a timezone.")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


def create_database_engine(database_url: str) -> Engine:
    """Create an engine; in-memory SQLite shares one connection so tests see one database."""
    if database_url.startswith("sqlite"):
        options: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in database_url or database_url == "sqlite://":
            options["poolclass"] = StaticPool
        return create_engine(database_url, **options)
    return create_engine(database_url)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to the engine."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_all_tables(engine: Engine) -> None:
    """Create every table that does not exist yet."""
    DatabaseBase.metadata.create_all(engine)


def get_database_session_generator(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Yield a session and always close it afterwards."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
