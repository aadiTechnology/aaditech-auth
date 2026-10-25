"""Timetable use cases.

Overlap for the same batch is new_start < existing_end and new_end > existing_start.
A class that starts when another ends is allowed. Cancelled classes do not block a slot.
Writes lock the batch row so two creates for that batch cannot both pass the check.
Teacher and room conflicts are not checked: those records do not exist.
"""

import logging
import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.selectable import Select

from app.audit.service import record_audit
from app.batches.models import Batch, BatchStatus
from app.common.exceptions import AppError, ErrorCode
from app.common.fields import add_error, clean_multiline, clean_single_line, raise_if_errors
from app.common.time import coaching_today
from app.core.logging import log_event
from app.timetable.models import ClassStatus, ScheduledClass
from app.timetable.schemas import ClassCreate, RecurringCreate
from app.users.models import User

logger = logging.getLogger("app.timetable")

MAX_OCCURRENCES = 60
MAX_RANGE_DAYS = 62
UPCOMING_LIMIT = 5


def times_overlap(start: time, end: time, other_start: time, other_end: time) -> bool:
    return start < other_end and end > other_start


def _class_query() -> Select[Any]:
    return select(ScheduledClass).options(selectinload(ScheduledClass.batch))


def require_class(db: Session, class_id: uuid.UUID) -> ScheduledClass:
    item = db.scalar(_class_query().where(ScheduledClass.id == class_id))
    if item is None:
        raise AppError(ErrorCode.NOT_FOUND, "Class not found.", 404)
    return item


def _reload_class(db: Session, class_id: uuid.UUID) -> ScheduledClass:
    db.expire_all()
    return require_class(db, class_id)


def _reload_classes(db: Session, class_ids: list[uuid.UUID]) -> list[ScheduledClass]:
    db.expire_all()
    stmt = _class_query().where(ScheduledClass.id.in_(class_ids))
    stmt = stmt.order_by(ScheduledClass.class_date, ScheduledClass.start_time)
    return list(db.scalars(stmt).all())


def _clean_clock(start: time | None, end: time | None, errors: list[dict[str, str]]) -> None:
    if start is None:
        add_error(errors, "start_time", "REQUIRED", "Start time is required.")
    if end is None:
        add_error(errors, "end_time", "REQUIRED", "End time is required.")
    if start is not None and end is not None and end <= start:
        add_error(errors, "end_time", "END_BEFORE_START", "End time must be later than the start time.")


def _clean_class_date(value: date | None, errors: list[dict[str, str]], field: str) -> date | None:
    if value is None:
        add_error(errors, field, "REQUIRED", "This field is required.")
        return None
    earliest = date(2020, 1, 1)
    latest = coaching_today() + timedelta(days=732)
    if value < earliest or value > latest:
        add_error(errors, field, "INVALID_DATE", "Enter a valid class date.")
        return None
    return value


def _lock_batches(db: Session, batch_ids: list[uuid.UUID]) -> dict[uuid.UUID, Batch]:
    locked: dict[uuid.UUID, Batch] = {}
    for batch_id in sorted(set(batch_ids)):
        batch = db.scalar(select(Batch).where(Batch.id == batch_id).with_for_update())
        if batch is None:
            raise AppError(ErrorCode.NOT_FOUND, "Batch not found.", 404)
        locked[batch_id] = batch
    return locked


def _require_active(batch: Batch) -> None:
    if batch.status != BatchStatus.ACTIVE:
        raise AppError(
            ErrorCode.NOT_ACTIVE,
            "Classes can only be scheduled for an active batch.",
            409,
        )


def _scheduled_on_dates(db: Session, batch_id: uuid.UUID, class_dates: list[date]) -> list[ScheduledClass]:
    if not class_dates:
        return []
    return list(
        db.scalars(
            select(ScheduledClass).where(
                ScheduledClass.batch_id == batch_id,
                ScheduledClass.status == ClassStatus.SCHEDULED,
                ScheduledClass.class_date.in_(class_dates),
            )
        ).all()
    )


def _conflict_details(dates: list[date]) -> list[dict[str, str]]:
    return [
        {
            "field": "class_date",
            "code": "SCHEDULE_CONFLICT",
            "message": f"Overlaps an existing class on {day.isoformat()}.",
        }
        for day in dates[:8]
    ]


def _raise_conflicts(dates: list[date]) -> None:
    if dates:
        raise AppError(
            ErrorCode.SCHEDULE_CONFLICT,
            "This class overlaps another class for the same batch.",
            409,
            details=_conflict_details(dates),
        )


def _conflicting_dates(
    existing: list[ScheduledClass],
    *,
    class_dates: list[date],
    start: time,
    end: time,
    exclude_id: uuid.UUID | None = None,
) -> list[date]:
    conflicts: list[date] = []
    for class_date in class_dates:
        for item in existing:
            if item.class_date != class_date or item.id == exclude_id:
                continue
            if times_overlap(start, end, item.start_time, item.end_time):
                conflicts.append(class_date)
                break
    return conflicts


def _texts(
    topic: str | None,
    notes: str | None,
    errors: list[dict[str, str]],
) -> tuple[str | None, str | None]:
    return (
        clean_single_line(topic, errors, "topic", 200),
        clean_multiline(notes, errors, "notes", 2000),
    )


def occurrence_dates(start: date, end: date, weekdays: set[int]) -> list[date]:
    found: list[date] = []
    current = start
    while current <= end:
        if current.weekday() in weekdays:
            found.append(current)
            if len(found) > MAX_OCCURRENCES:
                return found
        current += timedelta(days=1)
    return found


def _recurring_plan(payload: RecurringCreate, errors: list[dict[str, str]]) -> tuple[list[date], time, time]:
    start = _clean_class_date(payload.start_date, errors, "start_date")
    if payload.end_date is None:
        end = None if start is None else start + timedelta(weeks=8) - timedelta(days=1)
    else:
        end = _clean_class_date(payload.end_date, errors, "end_date")
    _clean_clock(payload.start_time, payload.end_time, errors)
    dates: list[date] = []
    if start is not None and end is not None:
        if end < start:
            add_error(errors, "end_date", "INVALID_DATE", "End date must be on or after the start date.")
        else:
            dates = occurrence_dates(start, end, set(payload.weekdays))
            if len(dates) > MAX_OCCURRENCES:
                add_error(
                    errors,
                    "end_date",
                    "TOO_MANY",
                    "Choose a shorter range. At most 60 classes can be created at once.",
                )
                dates = []
            elif not dates:
                add_error(
                    errors,
                    "weekdays",
                    "NO_OCCURRENCES",
                    "No classes fall on the selected weekdays in this date range.",
                )
    return dates, payload.start_time, payload.end_time


def list_classes(
    db: Session,
    *,
    from_date: date,
    to_date: date,
    batch_id: uuid.UUID | None,
    include_cancelled: bool,
) -> tuple[list[ScheduledClass], int]:
    errors: list[dict[str, str]] = []
    if to_date < from_date:
        add_error(errors, "to", "INVALID_DATE", "The end date must be on or after the start date.")
    elif (to_date - from_date).days > MAX_RANGE_DAYS:
        add_error(errors, "to", "TOO_LONG", "Choose a range of 62 days or less.")
    raise_if_errors(errors)
    filters = [ScheduledClass.class_date >= from_date, ScheduledClass.class_date <= to_date]
    if batch_id is not None:
        filters.append(ScheduledClass.batch_id == batch_id)
    if not include_cancelled:
        filters.append(ScheduledClass.status == ClassStatus.SCHEDULED)
    total = int(db.scalar(select(func.count()).select_from(ScheduledClass).where(*filters)) or 0)
    stmt = (
        _class_query()
        .where(*filters)
        .order_by(ScheduledClass.class_date.asc(), ScheduledClass.start_time.asc(), ScheduledClass.id.asc())
        .limit(500)
    )
    return list(db.scalars(stmt).all()), total


def summary(db: Session) -> tuple[int, list[ScheduledClass], list[ScheduledClass]]:
    today = coaching_today()
    today_filters = (
        ScheduledClass.status == ClassStatus.SCHEDULED,
        ScheduledClass.class_date == today,
    )
    today_count = int(db.scalar(select(func.count()).select_from(ScheduledClass).where(*today_filters)) or 0)
    today_classes = list(
        db.scalars(
            _class_query()
            .where(*today_filters)
            .order_by(ScheduledClass.start_time.asc(), ScheduledClass.id.asc())
            .limit(20)
        ).all()
    )
    upcoming = list(
        db.scalars(
            _class_query()
            .where(
                ScheduledClass.status == ClassStatus.SCHEDULED,
                ScheduledClass.class_date >= today,
            )
            .order_by(ScheduledClass.class_date.asc(), ScheduledClass.start_time.asc(), ScheduledClass.id.asc())
            .limit(UPCOMING_LIMIT)
        ).all()
    )
    return today_count, today_classes, upcoming


def next_scheduled_by_batch(db: Session, batch_ids: list[uuid.UUID]) -> dict[uuid.UUID, ScheduledClass]:
    if not batch_ids:
        return {}
    today = coaching_today()
    rows = list(
        db.scalars(
            select(ScheduledClass)
            .where(
                ScheduledClass.batch_id.in_(batch_ids),
                ScheduledClass.status == ClassStatus.SCHEDULED,
                ScheduledClass.class_date >= today,
            )
            .ext(distinct_on(ScheduledClass.batch_id))
            .order_by(ScheduledClass.batch_id, ScheduledClass.class_date, ScheduledClass.start_time)
        ).all()
    )
    return {row.batch_id: row for row in rows}


def _insert_classes(
    db: Session,
    *,
    actor: User,
    batch: Batch,
    class_dates: list[date],
    start: time,
    end: time,
    topic: str | None,
    notes: str | None,
    ip_address: str | None,
    action: str,
) -> list[ScheduledClass]:
    existing = _scheduled_on_dates(db, batch.id, class_dates)
    _raise_conflicts(_conflicting_dates(existing, class_dates=class_dates, start=start, end=end))
    now = datetime.now(UTC)
    created: list[ScheduledClass] = []
    for class_date in class_dates:
        item = ScheduledClass(
            batch_id=batch.id,
            class_date=class_date,
            start_time=start,
            end_time=end,
            topic=topic,
            notes=notes,
            status=ClassStatus.SCHEDULED,
            version=1,
            created_at=now,
            updated_at=now,
        )
        db.add(item)
        created.append(item)
    db.flush()
    record_audit(
        db,
        action=action,
        actor_id=actor.id,
        target_type="scheduled_class" if len(created) == 1 else "batch",
        target_id=created[0].id if len(created) == 1 else batch.id,
        context={"count": len(created), "batch_id": str(batch.id)},
        ip_address=ip_address,
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(
            ErrorCode.SCHEDULE_CONFLICT,
            "This class overlaps another class for the same batch.",
            409,
        ) from None
    log_event(logger, action, actor_id=str(actor.id), batch_id=str(batch.id), count=len(created))
    return _reload_classes(db, [item.id for item in created])


def create_class(
    db: Session,
    *,
    actor: User,
    payload: ClassCreate,
    ip_address: str | None,
) -> ScheduledClass:
    errors: list[dict[str, str]] = []
    class_date = _clean_class_date(payload.class_date, errors, "class_date")
    _clean_clock(payload.start_time, payload.end_time, errors)
    topic, notes = _texts(payload.topic, payload.notes, errors)
    raise_if_errors(errors)
    if class_date is None:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Validation failed.", 422)
    locked = _lock_batches(db, [payload.batch_id])
    batch = locked[payload.batch_id]
    _require_active(batch)
    created = _insert_classes(
        db,
        actor=actor,
        batch=batch,
        class_dates=[class_date],
        start=payload.start_time,
        end=payload.end_time,
        topic=topic,
        notes=notes,
        ip_address=ip_address,
        action="class_scheduled",
    )
    return created[0]


def preview_recurring(db: Session, payload: RecurringCreate) -> tuple[list[tuple[date, bool]], int]:
    errors: list[dict[str, str]] = []
    dates, start_time, end_time = _recurring_plan(payload, errors)
    _texts(payload.topic, payload.notes, errors)
    raise_if_errors(errors)
    batch = db.get(Batch, payload.batch_id)
    if batch is None:
        raise AppError(ErrorCode.NOT_FOUND, "Batch not found.", 404)
    _require_active(batch)
    existing = _scheduled_on_dates(db, batch.id, dates)
    conflict_dates = set(_conflicting_dates(existing, class_dates=dates, start=start_time, end=end_time))
    occurrences = [(day, day in conflict_dates) for day in dates]
    return occurrences, len(conflict_dates)


def create_recurring(
    db: Session,
    *,
    actor: User,
    payload: RecurringCreate,
    ip_address: str | None,
) -> list[ScheduledClass]:
    errors: list[dict[str, str]] = []
    dates, start_time, end_time = _recurring_plan(payload, errors)
    topic, notes = _texts(payload.topic, payload.notes, errors)
    raise_if_errors(errors)
    if not dates:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Validation failed.", 422)
    locked = _lock_batches(db, [payload.batch_id])
    batch = locked[payload.batch_id]
    _require_active(batch)
    return _insert_classes(
        db,
        actor=actor,
        batch=batch,
        class_dates=dates,
        start=start_time,
        end=end_time,
        topic=topic,
        notes=notes,
        ip_address=ip_address,
        action="classes_scheduled",
    )


def _as_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _as_time(value: object) -> time | None:
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    return None


def _as_uuid(value: object) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    return None


def update_class(
    db: Session,
    *,
    actor: User,
    class_id: uuid.UUID,
    changes: dict[str, object],
    ip_address: str | None,
) -> ScheduledClass:
    item = db.get(ScheduledClass, class_id)
    if item is None:
        raise AppError(ErrorCode.NOT_FOUND, "Class not found.", 404)
    expected = changes.get("version")
    if not isinstance(expected, int) or item.version != expected:
        raise AppError(
            ErrorCode.STALE_UPDATE,
            "This record was changed by someone else. Reload and try again.",
            409,
        )
    if item.status == ClassStatus.CANCELLED:
        raise AppError(ErrorCode.CONFLICT, "Cancelled classes cannot be edited.", 409)
    errors: list[dict[str, str]] = []
    cleaned: dict[str, object] = {}
    if "class_date" in changes:
        cleaned["class_date"] = _clean_class_date(_as_date(changes["class_date"]), errors, "class_date")
    if "start_time" in changes:
        start_time = _as_time(changes["start_time"])
        if start_time is None:
            add_error(errors, "start_time", "INVALID_TIME", "Enter a valid time.")
        else:
            cleaned["start_time"] = start_time
    if "end_time" in changes:
        end_time = _as_time(changes["end_time"])
        if end_time is None:
            add_error(errors, "end_time", "INVALID_TIME", "Enter a valid time.")
        else:
            cleaned["end_time"] = end_time
    if "topic" in changes:
        value = changes["topic"]
        cleaned["topic"] = clean_single_line(
            value if isinstance(value, str) or value is None else None,
            errors,
            "topic",
            200,
        )
    if "notes" in changes:
        value = changes["notes"]
        cleaned["notes"] = clean_multiline(
            value if isinstance(value, str) or value is None else None,
            errors,
            "notes",
            2000,
        )
    if "batch_id" in changes:
        batch_id = _as_uuid(changes["batch_id"])
        if batch_id is None:
            add_error(errors, "batch_id", "INVALID", "Choose a batch.")
        else:
            cleaned["batch_id"] = batch_id
    target_start = cleaned.get("start_time", item.start_time)
    target_end = cleaned.get("end_time", item.end_time)
    if isinstance(target_start, time) and isinstance(target_end, time):
        _clean_clock(target_start, target_end, errors)
    raise_if_errors(errors)
    if not cleaned:
        return require_class(db, class_id)
    target_batch_id = cleaned.get("batch_id", item.batch_id)
    target_date = cleaned.get("class_date", item.class_date)
    if not isinstance(target_batch_id, uuid.UUID) or not isinstance(target_date, date):
        raise AppError(ErrorCode.VALIDATION_ERROR, "Validation failed.", 422)
    if not isinstance(target_start, time) or not isinstance(target_end, time):
        raise AppError(ErrorCode.VALIDATION_ERROR, "Validation failed.", 422)
    locked = _lock_batches(db, [item.batch_id, target_batch_id])
    db.refresh(item)
    if item.version != expected or item.status == ClassStatus.CANCELLED:
        raise AppError(
            ErrorCode.STALE_UPDATE,
            "This record was changed by someone else. Reload and try again.",
            409,
        )
    target_batch = locked[target_batch_id]
    if target_batch.status == BatchStatus.ARCHIVED or target_batch_id != item.batch_id:
        _require_active(target_batch)
    existing = _scheduled_on_dates(db, target_batch_id, [target_date])
    _raise_conflicts(
        _conflicting_dates(
            existing,
            class_dates=[target_date],
            start=target_start,
            end=target_end,
            exclude_id=item.id,
        )
    )
    for key, value in cleaned.items():
        setattr(item, key, value)
    item.version += 1
    item.updated_at = datetime.now(UTC)
    record_audit(
        db,
        action="class_updated",
        actor_id=actor.id,
        target_type="scheduled_class",
        target_id=item.id,
        context={"fields": sorted(str(key) for key in cleaned)},
        ip_address=ip_address,
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(
            ErrorCode.SCHEDULE_CONFLICT,
            "This class overlaps another class for the same batch.",
            409,
        ) from None
    log_event(logger, "class_updated", actor_id=str(actor.id), class_id=str(item.id))
    return _reload_class(db, item.id)


def cancel_class(
    db: Session,
    *,
    actor: User,
    class_id: uuid.UUID,
    ip_address: str | None,
) -> ScheduledClass:
    item = require_class(db, class_id)
    if item.status != ClassStatus.CANCELLED:
        now = datetime.now(UTC)
        item.status = ClassStatus.CANCELLED
        item.cancelled_at = now
        item.updated_at = now
        item.version += 1
        record_audit(
            db,
            action="class_cancelled",
            actor_id=actor.id,
            target_type="scheduled_class",
            target_id=item.id,
            context={"status": ClassStatus.CANCELLED},
            ip_address=ip_address,
        )
        db.commit()
        log_event(logger, "class_cancelled", actor_id=str(actor.id), class_id=str(item.id))
        return _reload_class(db, item.id)
    return item
