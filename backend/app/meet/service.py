"""Save a Meet link on an existing scheduled class."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.common.exceptions import AppError, ErrorCode
from app.core.logging import log_event
from app.meet.urls import MeetUrlError, normalize_meet_url
from app.timetable.models import ClassStatus, ScheduledClass
from app.timetable.service import require_class
from app.users.models import User

logger = logging.getLogger("app.meet")


def clean_meet_url(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return normalize_meet_url(value)
    except MeetUrlError as exc:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "Validation failed.",
            422,
            details=[{"field": "meet_url", "code": "INVALID_URL", "message": str(exc)}],
        ) from None


def set_meet_link(
    db: Session,
    *,
    actor: User,
    class_id: uuid.UUID,
    version: int,
    meet_url: str | None,
    ip_address: str | None,
) -> ScheduledClass:
    item = require_class(db, class_id)
    if item.version != version:
        raise AppError(
            ErrorCode.STALE_UPDATE,
            "This class was changed somewhere else. Reload it and try again.",
            409,
        )
    if item.status != ClassStatus.SCHEDULED:
        raise AppError(
            ErrorCode.CLASS_CANCELLED,
            "A cancelled class keeps its current meeting link.",
            409,
        )
    cleaned = clean_meet_url(meet_url)
    item.meet_url = cleaned
    item.version += 1
    item.updated_at = datetime.now(UTC)
    record_audit(
        db,
        action="meet_link_updated",
        actor_id=actor.id,
        target_type="scheduled_class",
        target_id=item.id,
        context={"batch_id": str(item.batch_id), "link_present": cleaned is not None},
        ip_address=ip_address,
    )
    db.commit()
    log_event(
        logger,
        "meet_link_updated",
        actor_id=str(actor.id),
        class_id=str(item.id),
        link_present=cleaned is not None,
    )
    return require_class(db, item.id)
