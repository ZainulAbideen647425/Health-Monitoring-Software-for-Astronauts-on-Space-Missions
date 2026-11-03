"""Database table definitions for missions, astronauts, devices and measurements."""

from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from astronaut_health_monitor.core.database import DatabaseBase, UtcDateTime


def _current_utc_time() -> datetime:
    return datetime.now(UTC)


class MissionRecord(DatabaseBase):
    """A space mission and the environment its crew lives in."""

    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_name: Mapped[str] = mapped_column(String(120), unique=True)
    mission_environment: Mapped[str] = mapped_column(String(30))
    mission_start_time: Mapped[datetime] = mapped_column(UtcDateTime)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=_current_utc_time)

    astronauts: Mapped[list["AstronautRecord"]] = relationship(back_populates="mission")


class AstronautRecord(DatabaseBase):
    """A crew member whose health is monitored."""

    __tablename__ = "astronauts"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    mission_role: Mapped[str] = mapped_column(String(80))
    mission_id: Mapped[int | None] = mapped_column(ForeignKey("missions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=_current_utc_time)

    mission: Mapped[MissionRecord | None] = relationship(back_populates="astronauts")
    measurements: Mapped[list["MeasurementRecord"]] = relationship(back_populates="astronaut")


class DeviceRecord(DatabaseBase):
    """A measuring device (wearable sensor, glucose meter, and so on)."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_name: Mapped[str] = mapped_column(String(120), unique=True)
    device_kind: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=_current_utc_time)


class MeasurementRecord(DatabaseBase):
    """One recorded value of one health indicator for one astronaut at one moment."""

    __tablename__ = "measurements"
    __table_args__ = (
        Index("ix_measurements_astronaut_indicator_time", "astronaut_id", "indicator_type", "measured_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey("astronauts.id"))
    indicator_type: Mapped[str] = mapped_column(String(40))
    measured_value: Mapped[float]
    measurement_unit: Mapped[str] = mapped_column(String(60))
    measured_at: Mapped[datetime] = mapped_column(UtcDateTime)
    measurement_source: Mapped[str] = mapped_column(String(30))
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(UtcDateTime, default=_current_utc_time)

    astronaut: Mapped[AstronautRecord] = relationship(back_populates="measurements")
