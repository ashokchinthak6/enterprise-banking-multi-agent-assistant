"""Append-only in-memory audit events for the demo."""

from datetime import UTC, datetime
from uuid import uuid4

from .models import AuditEvent


class AuditLog:
    """Records security-relevant actions without storing conversation text."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record(
        self,
        event_type: str,
        actor: str,
        resource_id: str | None = None,
        details: dict | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            id=f"audit-{uuid4().hex[:12]}",
            event_type=event_type,
            actor=actor,
            resource_id=resource_id,
            details=details or {},
            occurred_at=datetime.now(UTC),
        )
        self._events.append(event)
        return event

    def list_events(self) -> list[AuditEvent]:
        return list(reversed(self._events))

