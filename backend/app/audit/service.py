"""Record security-sensitive actions. This module does not expose a reporting API."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.audit.models import AuditLog


def record_audit(
    db: Session,
    *,
    action: str,
    actor_id: uuid.UUID | None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    context: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            context=context,
            ip_address=ip_address,
            created_at=datetime.now(UTC),
        )
    )
