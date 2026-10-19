"""Batch register use cases."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.selectable import Select

from app.audit.service import record_audit
from app.batches.models import Batch, BatchStatus, BatchStudent
from app.batches.schemas import BatchCreate
from app.common.exceptions import AppError, ErrorCode
from app.common.fields import add_error, clean_grade, clean_multiline, clean_single_line, like_pattern, raise_if_errors
from app.core.logging import log_event
from app.students.models import Student, StudentStatus
from app.timetable.service import next_scheduled_by_batch
from app.users.models import User

logger = logging.getLogger("app.batches")


def _clean_batch_name(value: object, errors: list[dict[str, str]]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        add_error(errors, "name", "REQUIRED", "Batch name is required.")
        return None
    cleaned = " ".join(value.split())
    if len(cleaned) < 2:
        add_error(errors, "name", "MIN_LENGTH", "Enter at least 2 characters.")
        return None
    if len(cleaned) > 200:
        add_error(errors, "name", "TOO_LONG", "This value is too long.")
        return None
    return cleaned


def _clean_status(value: object, errors: list[dict[str, str]]) -> str | None:
    if value not in {BatchStatus.ACTIVE, BatchStatus.INACTIVE}:
        add_error(errors, "status", "INVALID_STATUS", "Choose active or inactive.")
        return None
    return str(value)


def _next_batch_code(db: Session) -> str:
    value = db.execute(text("SELECT nextval('batch_code_seq')")).scalar_one()
    return f"BAT-{int(value):06d}"


def _batch_query() -> Select[Any]:
    return select(Batch).options(selectinload(Batch.enrollments).selectinload(BatchStudent.student))


def get_batch(db: Session, batch_id: uuid.UUID) -> Batch | None:
    return db.scalar(_batch_query().where(Batch.id == batch_id))


def require_batch(db: Session, batch_id: uuid.UUID) -> Batch:
    batch = get_batch(db, batch_id)
    if batch is None:
        raise AppError(ErrorCode.NOT_FOUND, "Batch not found.", 404)
    return batch


def _reload_batch(db: Session, batch_id: uuid.UUID) -> Batch:
    db.expire_all()
    return require_batch(db, batch_id)


def _apply_filters(
    stmt: Select[Any],
    *,
    q: str | None,
    status: str | None,
    subject: str | None,
    grade: str | None,
    student_id: uuid.UUID | None,
) -> Select[Any]:
    if status is None:
        stmt = stmt.where(Batch.status != BatchStatus.ARCHIVED)
    elif status != "all":
        stmt = stmt.where(Batch.status == status)
    if grade:
        stmt = stmt.where(Batch.grade == grade)
    if subject and subject.strip():
        stmt = stmt.where(func.lower(Batch.subject) == subject.strip().lower())
    if student_id is not None:
        stmt = stmt.where(
            Batch.id.in_(select(BatchStudent.batch_id).where(BatchStudent.student_id == student_id))
        )
    if q and q.strip():
        pattern = like_pattern(q.strip())
        stmt = stmt.where(
            or_(
                Batch.name.ilike(pattern, escape="\\"),
                Batch.batch_code.ilike(pattern, escape="\\"),
            )
        )
    return stmt


def _student_count_expr() -> Any:
    return (
        select(func.count(BatchStudent.student_id))
        .where(BatchStudent.batch_id == Batch.id)
        .correlate(Batch)
        .scalar_subquery()
    )


def list_batches(
    db: Session,
    *,
    q: str | None,
    status: str | None,
    subject: str | None,
    grade: str | None,
    student_id: uuid.UUID | None,
    limit: int,
    offset: int,
    sort: str,
    direction: str,
) -> tuple[list[Batch], int, dict[uuid.UUID, int]]:
    errors: list[dict[str, str]] = []
    selected_grade = clean_grade(grade, errors) if grade and grade.strip() else None
    raise_if_errors(errors)
    total = int(
        db.scalar(
            _apply_filters(
                select(func.count()).select_from(Batch),
                q=q,
                status=status,
                subject=subject,
                grade=selected_grade,
                student_id=student_id,
            )
        )
        or 0
    )
    columns: dict[str, Any] = {
        "name": Batch.name,
        "code": Batch.batch_code,
        "subject": Batch.subject,
        "grade": Batch.grade,
        "status": Batch.status,
        "students": _student_count_expr(),
    }
    column = columns[sort]
    ordering = column.asc() if direction == "asc" else column.desc()
    stmt = _apply_filters(
        select(Batch),
        q=q,
        status=status,
        subject=subject,
        grade=selected_grade,
        student_id=student_id,
    )
    stmt = stmt.order_by(ordering, Batch.id.asc()).limit(limit).offset(offset)
    batches = list(db.scalars(stmt).all())
    counts = _counts_for(db, [batch.id for batch in batches])
    return batches, total, counts


def _counts_for(db: Session, batch_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not batch_ids:
        return {}
    rows = db.execute(
        select(BatchStudent.batch_id, func.count(BatchStudent.student_id))
        .where(BatchStudent.batch_id.in_(batch_ids))
        .group_by(BatchStudent.batch_id)
    ).all()
    return {batch_id: int(count) for batch_id, count in rows}


def active_batch_count(db: Session) -> int:
    stmt = select(func.count()).select_from(Batch).where(Batch.status == BatchStatus.ACTIVE)
    return int(db.scalar(stmt) or 0)


def _students_for_assignment(db: Session, student_ids: list[uuid.UUID]) -> list[Student]:
    if len(set(student_ids)) != len(student_ids):
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "Validation failed.",
            422,
            details=[{"field": "student_ids", "code": "DUPLICATE", "message": "Each student can be selected once."}],
        )
    rows = list(db.scalars(select(Student).where(Student.id.in_(student_ids))).all())
    found = {row.id for row in rows}
    if any(student_id not in found for student_id in student_ids):
        raise AppError(ErrorCode.NOT_FOUND, "Student not found.", 404)
    if any(row.status == StudentStatus.ARCHIVED for row in rows):
        raise AppError(ErrorCode.CONFLICT, "Archived students cannot be added to a batch.", 409)
    return rows


def _reject_archived_batch(batch: Batch) -> None:
    if batch.status == BatchStatus.ARCHIVED:
        raise AppError(ErrorCode.CONFLICT, "Archived batches cannot be changed.", 409)


def create_batch(
    db: Session,
    *,
    actor: User,
    payload: BatchCreate,
    ip_address: str | None,
) -> Batch:
    errors: list[dict[str, str]] = []
    name = _clean_batch_name(payload.name, errors)
    subject = clean_single_line(payload.subject, errors, "subject", 100)
    grade = clean_grade(payload.grade, errors)
    description = clean_multiline(payload.description, errors, "description", 2000)
    status = _clean_status(payload.status, errors)
    raise_if_errors(errors)
    students = _students_for_assignment(db, payload.student_ids) if payload.student_ids else []
    if name is None or status is None:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Validation failed.", 422)
    now = datetime.now(UTC)
    batch = Batch(
        batch_code=_next_batch_code(db),
        name=name,
        subject=subject,
        grade=grade,
        description=description,
        status=status,
        version=1,
        created_at=now,
        updated_at=now,
    )
    db.add(batch)
    db.flush()
    for student in students:
        db.add(BatchStudent(batch_id=batch.id, student_id=student.id, created_at=now))
    record_audit(
        db,
        action="batch_created",
        actor_id=actor.id,
        target_type="batch",
        target_id=batch.id,
        context={"status": batch.status, "students": len(students)},
        ip_address=ip_address,
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(ErrorCode.DUPLICATE_ASSIGNMENT, "This student is already assigned to this batch.", 409) from None
    log_event(logger, "batch_created", actor_id=str(actor.id), batch_id=str(batch.id))
    return _reload_batch(db, batch.id)


def update_batch(
    db: Session,
    *,
    actor: User,
    batch_id: uuid.UUID,
    changes: dict[str, object],
    ip_address: str | None,
) -> Batch:
    batch = require_batch(db, batch_id)
    expected = changes.get("version")
    if not isinstance(expected, int) or batch.version != expected:
        raise AppError(
            ErrorCode.STALE_UPDATE,
            "This record was changed by someone else. Reload and try again.",
            409,
        )
    _reject_archived_batch(batch)
    errors: list[dict[str, str]] = []
    cleaned: dict[str, object] = {}
    if "name" in changes:
        cleaned["name"] = _clean_batch_name(changes["name"], errors)
    if "status" in changes and changes["status"] is not None:
        cleaned["status"] = _clean_status(changes["status"], errors)
    if "subject" in changes:
        value = changes["subject"]
        cleaned["subject"] = clean_single_line(
            value if isinstance(value, str) or value is None else None,
            errors,
            "subject",
            100,
        )
    if "grade" in changes:
        value = changes["grade"]
        cleaned["grade"] = clean_grade(value if isinstance(value, str) or value is None else None, errors)
    if "description" in changes:
        value = changes["description"]
        cleaned["description"] = clean_multiline(
            value if isinstance(value, str) or value is None else None,
            errors,
            "description",
            2000,
        )
    raise_if_errors(errors)
    if "name" in cleaned and cleaned["name"] is None:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Validation failed.", 422)
    if not cleaned:
        return batch
    for key, value in cleaned.items():
        setattr(batch, key, value)
    batch.version += 1
    batch.updated_at = datetime.now(UTC)
    record_audit(
        db,
        action="batch_updated",
        actor_id=actor.id,
        target_type="batch",
        target_id=batch.id,
        context={"fields": sorted(str(key) for key in cleaned)},
        ip_address=ip_address,
    )
    db.commit()
    log_event(logger, "batch_updated", actor_id=str(actor.id), batch_id=str(batch.id))
    return _reload_batch(db, batch.id)


def archive_batch(
    db: Session,
    *,
    actor: User,
    batch_id: uuid.UUID,
    ip_address: str | None,
) -> Batch:
    batch = require_batch(db, batch_id)
    if batch.status != BatchStatus.ARCHIVED:
        now = datetime.now(UTC)
        batch.status = BatchStatus.ARCHIVED
        batch.archived_at = now
        batch.updated_at = now
        batch.version += 1
        record_audit(
            db,
            action="batch_archived",
            actor_id=actor.id,
            target_type="batch",
            target_id=batch.id,
            context={"status": BatchStatus.ARCHIVED},
            ip_address=ip_address,
        )
        db.commit()
        log_event(logger, "batch_archived", actor_id=str(actor.id), batch_id=str(batch.id))
        return _reload_batch(db, batch.id)
    return batch


def assign_students(
    db: Session,
    *,
    actor: User,
    batch_id: uuid.UUID,
    student_ids: list[uuid.UUID],
    ip_address: str | None,
) -> Batch:
    batch = db.scalar(select(Batch).where(Batch.id == batch_id).with_for_update())
    if batch is None:
        raise AppError(ErrorCode.NOT_FOUND, "Batch not found.", 404)
    _reject_archived_batch(batch)
    students = _students_for_assignment(db, student_ids)
    existing = set(
        db.scalars(
            select(BatchStudent.student_id).where(
                BatchStudent.batch_id == batch.id,
                BatchStudent.student_id.in_(student_ids),
            )
        ).all()
    )
    if existing:
        raise AppError(
            ErrorCode.DUPLICATE_ASSIGNMENT,
            "This student is already assigned to this batch.",
            409,
        )
    now = datetime.now(UTC)
    for student in students:
        db.add(BatchStudent(batch_id=batch.id, student_id=student.id, created_at=now))
    record_audit(
        db,
        action="batch_students_assigned",
        actor_id=actor.id,
        target_type="batch",
        target_id=batch.id,
        context={"student_ids": [str(student.id) for student in students]},
        ip_address=ip_address,
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(
            ErrorCode.DUPLICATE_ASSIGNMENT,
            "This student is already assigned to this batch.",
            409,
        ) from None
    log_event(logger, "batch_students_assigned", actor_id=str(actor.id), batch_id=str(batch.id))
    return _reload_batch(db, batch.id)


def remove_student(
    db: Session,
    *,
    actor: User,
    batch_id: uuid.UUID,
    student_id: uuid.UUID,
    ip_address: str | None,
) -> Batch:
    if db.get(Batch, batch_id) is None:
        raise AppError(ErrorCode.NOT_FOUND, "Batch not found.", 404)
    if db.get(Student, student_id) is None:
        raise AppError(ErrorCode.NOT_FOUND, "Student not found.", 404)
    link = db.get(BatchStudent, (batch_id, student_id))
    if link is None:
        raise AppError(ErrorCode.NOT_FOUND, "This student is not assigned to this batch.", 404)
    db.delete(link)
    record_audit(
        db,
        action="batch_student_removed",
        actor_id=actor.id,
        target_type="batch",
        target_id=batch_id,
        context={"student_id": str(student_id)},
        ip_address=ip_address,
    )
    db.commit()
    log_event(
        logger,
        "batch_student_removed",
        actor_id=str(actor.id),
        batch_id=str(batch_id),
        student_id=str(student_id),
    )
    return _reload_batch(db, batch_id)


def upcoming_for(db: Session, batches: list[Batch]) -> dict[uuid.UUID, Any]:
    return next_scheduled_by_batch(db, [batch.id for batch in batches])
