"""A tamper-evident audit log.

Every entry stores a hash that covers its own content and the hash of the entry before it. Changing or deleting any
past entry breaks every hash after it, which `verify_chain` detects. This shows tampering; it cannot prevent someone
with full database access from rewriting the whole chain, so the log should also be copied somewhere else for real use.
"""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from astronaut_health_monitor.domain.authenticated_user import AuthenticatedUser
from astronaut_health_monitor.domain.enumerations import AuditOutcome
from astronaut_health_monitor.repositories.audit_repository import AuditRepository
from astronaut_health_monitor.repositories.database_records import AuditEventRecord

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class ChainVerification:
    is_valid: bool
    checked_event_count: int
    first_broken_event_id: int | None


def compute_event_hash(
    previous_hash: str,
    occurred_at: datetime,
    username: str | None,
    user_role: str | None,
    action: str,
    target: str | None,
    outcome: str,
    detail: str,
) -> str:
    fields = [
        previous_hash,
        occurred_at.astimezone(UTC).isoformat(),
        username or "",
        user_role or "",
        action,
        target or "",
        outcome,
        detail,
    ]
    return hashlib.sha256("\n".join(fields).encode("utf-8")).hexdigest()


class AuditService:
    def __init__(self, audit_repository: AuditRepository, clock: Callable[[], datetime] | None = None) -> None:
        self._audit_repository = audit_repository
        self._clock = clock or (lambda: datetime.now(UTC))

    def record(
        self,
        action: str,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        user: AuthenticatedUser | None = None,
        username: str | None = None,
        target: str | None = None,
        detail: str = "",
    ) -> AuditEventRecord:
        """Add one entry. Never put passwords, tokens or health values in `detail`."""
        latest = self._audit_repository.get_latest_event()
        previous_hash = latest.event_hash if latest else GENESIS_HASH
        occurred_at = self._clock()
        shown_username = user.username if user else username
        role = user.role.value if user else None
        event_hash = compute_event_hash(
            previous_hash, occurred_at, shown_username, role, action, target, outcome.value, detail
        )
        return self._audit_repository.add_event(
            AuditEventRecord(
                occurred_at=occurred_at,
                username=shown_username,
                user_role=role,
                action=action,
                target=target,
                outcome=outcome.value,
                detail=detail,
                previous_hash=previous_hash,
                event_hash=event_hash,
            )
        )

    def list_recent_events(self, limit: int) -> list[AuditEventRecord]:
        return self._audit_repository.list_events_newest_first(limit)

    def verify_chain(self) -> ChainVerification:
        expected_previous = GENESIS_HASH
        checked = 0
        for event in self._audit_repository.list_all_events_oldest_first():
            recomputed = compute_event_hash(
                event.previous_hash,
                event.occurred_at,
                event.username,
                event.user_role,
                event.action,
                event.target,
                event.outcome,
                event.detail,
            )
            if event.previous_hash != expected_previous or event.event_hash != recomputed:
                return ChainVerification(False, checked, event.id)
            expected_previous = event.event_hash
            checked += 1
        return ChainVerification(True, checked, None)
