"""Database access for measuring devices."""

from sqlalchemy.orm import Session

from astronaut_health_monitor.repositories.database_records import DeviceRecord


class DeviceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_device(self, device_name: str, device_kind: str) -> DeviceRecord:
        record = DeviceRecord(device_name=device_name, device_kind=device_kind)
        self._session.add(record)
        self._session.commit()
        return record

    def get_device_by_id(self, device_id: int) -> DeviceRecord | None:
        return self._session.get(DeviceRecord, device_id)
