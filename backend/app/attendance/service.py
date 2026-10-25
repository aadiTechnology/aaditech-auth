"""Attendance use cases.

Percentage = present / (present + absent + late) × 100, rounded half up to one decimal.
Excused records are stored and left out of both sides. Late is not counted as present.
Students with no saved row are not counted as absent.

A class attendance save is one transaction. Each student has at most one row per class.
"""

import logging
import uuid
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, cast

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql import Select

from app.attendance.models import AttendanceRecord, AttendanceStatus
from app.attendance.schemas import (
    AttendanceClassItem,
    AttendanceMarkIn,
    AttendanceStatusValue,
    ClassRoster,
    CompletionValue,
    HistoryItem,
    RosterMark,
    RosterStudent,
    SummaryItem,
)
from app.audit.service import record_audit
from app.batches.models import Batch, BatchStudent
from app.common.exceptions import AppError, ErrorCode
from app.common.fields import add_error, clean_multiline, raise_if_errors
from app.common.time import coaching_today
from app.core.logging import log_event
from app.students.models import Student
from app.timetable.models import ClassStatus, ScheduledClass
from app.timetable.service import require_class
from app.users.models import User

logger = logging.getLogger("app.attendance")

MAX_CLASS_RANGE_DAYS = 62
MAX_HISTORY_DAYS = 366


def attendance_percentage(present: int, eligible: int) -> float | None:
    if eligible <= 0:
        return None
    value = (Decimal(present) * Decimal(100) / Decimal(eligible)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return float(value)


def completion_for(enrolled: int, recorded: int) -> CompletionValue:
    if enrolled <= 0:
        return "no_students"
    if recorded <= 0:
        return "not_recorded"
    if recorded < enrolled:
        return "partial"
    return "complete"


def _require_batch(db: Session, batch_id: uuid.UUID) -> Batch:
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise AppError(ErrorCode.NOT_FOUND, "Batch not found.", 404)
    return batch


def _check_range(from_date: date, to_date: date, limit: int) -> None:
    errors: list[dict[str, str]] = []
    if to_date < from_date:
        add_error(errors, "to", "INVALID_DATE", "The end date must be on or after the start date.")
    elif (to_date - from_date).days > limit:
        add_error(errors, "to", "TOO_LONG", "Choose a shorter date range.")
    raise_if_errors(errors)


def _completion_counts(
    db: Session, classes: list[ScheduledClass]
) -> dict[uuid.UUID, tuple[int, int]]:
    if not classes:
        return {}
    class_ids = [item.id for item in classes]
    batch_ids = list({item.batch_id for item in classes})
    enrolled = {
        batch_id: int(count)
        for batch_id, count in db.execute(
            select(BatchStudent.batch_id, func.count())
            .where(BatchStudent.batch_id.in_(batch_ids))
            .group_by(BatchStudent.batch_id)
        ).all()
    }
    recorded = {
        class_id: int(count)
        for class_id, count in db.execute(
            select(AttendanceRecord.scheduled_class_id, func.count())
            .join(ScheduledClass, ScheduledClass.id == AttendanceRecord.scheduled_class_id)
            .join(
                BatchStudent,
                and_(
                    BatchStudent.batch_id == ScheduledClass.batch_id,
                    BatchStudent.student_id == AttendanceRecord.student_id,
                ),
            )
            .where(AttendanceRecord.scheduled_class_id.in_(class_ids))
            .group_by(AttendanceRecord.scheduled_class_id)
        ).all()
    }
    return {
        item.id: (enrolled.get(item.batch_id, 0), recorded.get(item.id, 0))
        for item in classes
    }


def _class_item(item: ScheduledClass, enrolled: int, recorded: int) -> AttendanceClassItem:
    return AttendanceClassItem(
        id=str(item.id),
        batch_id=str(item.batch_id),
        batch_name=item.batch.name,
        batch_code=item.batch.batch_code,
        class_date=item.class_date,
        start_time=item.start_time,
        end_time=item.end_time,
        topic=item.topic,
        class_status=item.status,
        completion=completion_for(enrolled, recorded),
        enrolled_count=enrolled,
        recorded_count=recorded,
    )


def list_attendance_classes(
    db: Session,
    *,
    batch_id: uuid.UUID,
    from_date: date,
    to_date: date,
    include_cancelled: bool,
) -> tuple[list[AttendanceClassItem], int]:
    _require_batch(db, batch_id)
    _check_range(from_date, to_date, MAX_CLASS_RANGE_DAYS)
    filters = [
        ScheduledClass.batch_id == batch_id,
        ScheduledClass.class_date >= from_date,
        ScheduledClass.class_date <= to_date,
    ]
    if not include_cancelled:
        filters.append(ScheduledClass.status == ClassStatus.SCHEDULED)
    total = int(db.scalar(select(func.count()).select_from(ScheduledClass).where(*filters)) or 0)
    classes = list(
        db.scalars(
            select(ScheduledClass)
            .options(selectinload(ScheduledClass.batch))
            .where(*filters)
            .order_by(ScheduledClass.class_date.asc(), ScheduledClass.start_time.asc(), ScheduledClass.id.asc())
            .limit(500)
        ).all()
    )
    counts = _completion_counts(db, classes)
    items = [_class_item(item, *counts[item.id]) for item in classes]
    return items, total


def today_classes(db: Session) -> list[AttendanceClassItem]:
    today = coaching_today()
    classes = list(
        db.scalars(
            select(ScheduledClass)
            .options(selectinload(ScheduledClass.batch))
            .where(ScheduledClass.status == ClassStatus.SCHEDULED, ScheduledClass.class_date == today)
            .order_by(ScheduledClass.start_time.asc(), ScheduledClass.id.asc())
            .limit(20)
        ).all()
    )
    counts = _completion_counts(db, classes)
    return [_class_item(item, *counts[item.id]) for item in classes]


def _enrolled_students(db: Session, batch_id: uuid.UUID) -> list[BatchStudent]:
    rows = list(
        db.scalars(
            select(BatchStudent)
            .options(selectinload(BatchStudent.student))
            .where(BatchStudent.batch_id == batch_id)
        ).all()
    )
    rows.sort(key=lambda row: (row.student.full_name.casefold(), row.student.student_code))
    return rows


def _records_for_class(db: Session, class_id: uuid.UUID) -> dict[uuid.UUID, AttendanceRecord]:
    rows = db.scalars(select(AttendanceRecord).where(AttendanceRecord.scheduled_class_id == class_id)).all()
    return {row.student_id: row for row in rows}


def _roster_student(enrollment: BatchStudent, record: AttendanceRecord | None) -> RosterStudent:
    attendance = None
    if record is not None:
        attendance = RosterMark(
            id=str(record.id),
            status=cast(AttendanceStatusValue, record.status),
            notes=record.notes,
            version=record.version,
            updated_at=record.updated_at,
        )
    return RosterStudent(
        student_id=str(enrollment.student_id),
        student_code=enrollment.student.student_code,
        full_name=enrollment.student.full_name,
        student_status=enrollment.student.status,
        attendance=attendance,
    )


def build_roster(
    item: ScheduledClass,
    enrollments: list[BatchStudent],
    records: dict[uuid.UUID, AttendanceRecord],
) -> ClassRoster:
    students = [_roster_student(enrollment, records.get(enrollment.student_id)) for enrollment in enrollments]
    recorded = sum(1 for student in students if student.attendance is not None)
    enrolled = len(students)
    return ClassRoster(
        id=str(item.id),
        batch_id=str(item.batch_id),
        batch_name=item.batch.name,
        batch_code=item.batch.batch_code,
        class_date=item.class_date,
        start_time=item.start_time,
        end_time=item.end_time,
        topic=item.topic,
        class_status=item.status,
        completion=completion_for(enrolled, recorded),
        enrolled_count=enrolled,
        recorded_count=recorded,
        students=students,
    )


def get_roster(db: Session, class_id: uuid.UUID) -> ClassRoster:
    item = require_class(db, class_id)
    enrollments = _enrolled_students(db, item.batch_id)
    records = _records_for_class(db, item.id)
    return build_roster(item, enrollments, records)


def save_attendance(
    db: Session,
    *,
    actor: User,
    class_id: uuid.UUID,
    marks: list[AttendanceMarkIn],
    ip_address: str | None,
) -> ClassRoster:
    item = db.scalar(select(ScheduledClass).where(ScheduledClass.id == class_id).with_for_update())
    if item is None:
        raise AppError(ErrorCode.NOT_FOUND, "Class not found.", 404)
    batch = db.get(Batch, item.batch_id)
    if batch is None:
        raise AppError(ErrorCode.NOT_FOUND, "Batch not found.", 404)
    item.batch = batch
    enrollments = _enrolled_students(db, item.batch_id)
    enrolled_ids = {row.student_id for row in enrollments}
    existing = {
        row.student_id: row
        for row in db.scalars(
            select(AttendanceRecord)
            .where(AttendanceRecord.scheduled_class_id == item.id)
            .with_for_update()
        ).all()
    }
    errors: list[dict[str, str]] = []
    seen: set[uuid.UUID] = set()
    for index, mark in enumerate(marks):
        if mark.student_id in seen:
            add_error(
                errors,
                f"marks.{index}.student_id",
                "DUPLICATE",
                "Each student can be included once.",
            )
        seen.add(mark.student_id)
        if mark.student_id not in enrolled_ids:
            add_error(
                errors,
                f"marks.{index}.student_id",
                "STUDENT_NOT_IN_BATCH",
                "This student is not enrolled in the class batch.",
            )
        clean_multiline(mark.notes, errors, f"marks.{index}.notes", 500)
    raise_if_errors(errors)

    if item.status != ClassStatus.SCHEDULED and any(mark.student_id not in existing for mark in marks):
        raise AppError(
            ErrorCode.CLASS_CANCELLED,
            "Attendance cannot be added for a cancelled class. Existing records can still be corrected.",
            409,
        )
    for mark in marks:
        current = existing.get(mark.student_id)
        if (current is None and mark.version is not None) or (
            current is not None and mark.version != current.version
        ):
            raise AppError(
                ErrorCode.STALE_UPDATE,
                "Attendance was changed somewhere else. Reload it and try again.",
                409,
            )

    now = datetime.now(UTC)
    prepared: list[tuple[AttendanceMarkIn, str | None]] = []
    for index, mark in enumerate(marks):
        prepared.append((mark, clean_multiline(mark.notes, [], f"marks.{index}.notes", 500)))
    for mark, notes in prepared:
        current = existing.get(mark.student_id)
        if current is None:
            created = AttendanceRecord(
                scheduled_class_id=item.id,
                student_id=mark.student_id,
                status=mark.status,
                notes=notes,
                version=1,
                recorded_by=actor.id,
                created_at=now,
                updated_at=now,
            )
            db.add(created)
            existing[mark.student_id] = created
        else:
            current.status = mark.status
            current.notes = notes
            current.version += 1
            current.updated_at = now
            current.recorded_by = actor.id
    record_audit(
        db,
        action="attendance_saved",
        actor_id=actor.id,
        target_type="scheduled_class",
        target_id=item.id,
        context={"batch_id": str(item.batch_id), "count": len(marks)},
        ip_address=ip_address,
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(
            ErrorCode.CONFLICT,
            "Attendance for this class was saved somewhere else. Reload it and try again.",
            409,
        ) from None
    log_event(logger, "attendance_saved", actor_id=str(actor.id), class_id=str(item.id), count=len(marks))
    return build_roster(item, enrollments, existing)


def _require_scope(
    db: Session,
    *,
    batch_id: uuid.UUID | None,
    student_id: uuid.UUID | None,
    class_id: uuid.UUID | None,
) -> None:
    if batch_id is None and student_id is None and class_id is None:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "Validation failed.",
            422,
            details=[
                {
                    "field": "batch_id",
                    "code": "REQUIRED",
                    "message": "Choose a batch, student, or class.",
                }
            ],
        )
    if batch_id is not None:
        _require_batch(db, batch_id)
    if class_id is not None:
        require_class(db, class_id)
    if student_id is not None and db.get(Student, student_id) is None:
        raise AppError(ErrorCode.NOT_FOUND, "Student not found.", 404)


def _history_statement(
    *,
    batch_id: uuid.UUID | None,
    student_id: uuid.UUID | None,
    class_id: uuid.UUID | None,
    from_date: date | None,
    to_date: date | None,
) -> Select[Any]:
    filters = []
    if batch_id is not None:
        filters.append(ScheduledClass.batch_id == batch_id)
    if student_id is not None:
        filters.append(AttendanceRecord.student_id == student_id)
    if class_id is not None:
        filters.append(AttendanceRecord.scheduled_class_id == class_id)
    if from_date is not None:
        filters.append(ScheduledClass.class_date >= from_date)
    if to_date is not None:
        filters.append(ScheduledClass.class_date <= to_date)
    joined = cast(
        Select[Any],
        select(AttendanceRecord, ScheduledClass, Student, Batch)
        .join(ScheduledClass, ScheduledClass.id == AttendanceRecord.scheduled_class_id)
        .join(Student, Student.id == AttendanceRecord.student_id)
        .join(Batch, Batch.id == ScheduledClass.batch_id)
        .where(*filters),
    )
    return joined


def history(
    db: Session,
    *,
    batch_id: uuid.UUID | None,
    student_id: uuid.UUID | None,
    class_id: uuid.UUID | None,
    from_date: date | None,
    to_date: date | None,
    limit: int,
    offset: int,
) -> tuple[list[HistoryItem], int]:
    if from_date is not None and to_date is not None:
        _check_range(from_date, to_date, MAX_HISTORY_DAYS)
    _require_scope(db, batch_id=batch_id, student_id=student_id, class_id=class_id)
    joined = _history_statement(
        batch_id=batch_id,
        student_id=student_id,
        class_id=class_id,
        from_date=from_date,
        to_date=to_date,
    )
    total = int(db.scalar(select(func.count()).select_from(joined.subquery())) or 0)
    rows = db.execute(
        joined.order_by(
            ScheduledClass.class_date.desc(),
            ScheduledClass.start_time.desc(),
            Student.full_name.asc(),
            AttendanceRecord.id.asc(),
        )
        .limit(limit)
        .offset(offset)
    ).all()
    items = [
        HistoryItem(
            id=str(record.id),
            scheduled_class_id=str(record.scheduled_class_id),
            student_id=str(student.id),
            student_code=student.student_code,
            full_name=student.full_name,
            batch_id=str(batch.id),
            batch_name=batch.name,
            batch_code=batch.batch_code,
            class_date=scheduled.class_date,
            start_time=scheduled.start_time,
            end_time=scheduled.end_time,
            topic=scheduled.topic,
            class_status=scheduled.status,
            status=cast(AttendanceStatusValue, record.status),
            notes=record.notes,
            version=record.version,
            updated_at=record.updated_at,
        )
        for record, scheduled, student, batch in rows
    ]
    return items, total


def _summary_counts(
    db: Session,
    *,
    batch_id: uuid.UUID | None,
    student_id: uuid.UUID | None,
    class_id: uuid.UUID | None,
    from_date: date | None,
    to_date: date | None,
) -> dict[uuid.UUID, dict[str, int]]:
    filters = []
    if batch_id is not None:
        filters.append(ScheduledClass.batch_id == batch_id)
    if student_id is not None:
        filters.append(AttendanceRecord.student_id == student_id)
    if class_id is not None:
        filters.append(AttendanceRecord.scheduled_class_id == class_id)
    if from_date is not None:
        filters.append(ScheduledClass.class_date >= from_date)
    if to_date is not None:
        filters.append(ScheduledClass.class_date <= to_date)
    rows = db.execute(
        select(AttendanceRecord.student_id, AttendanceRecord.status, func.count())
        .join(ScheduledClass, ScheduledClass.id == AttendanceRecord.scheduled_class_id)
        .where(*filters)
        .group_by(AttendanceRecord.student_id, AttendanceRecord.status)
    ).all()
    grouped: dict[uuid.UUID, dict[str, int]] = {}
    for owner_id, status, count in rows:
        grouped.setdefault(owner_id, {})[str(status)] = int(count)
    return grouped


def _summary_item(student: Student, counts: dict[str, int]) -> SummaryItem:
    present = counts.get(AttendanceStatus.PRESENT, 0)
    absent = counts.get(AttendanceStatus.ABSENT, 0)
    late = counts.get(AttendanceStatus.LATE, 0)
    excused = counts.get(AttendanceStatus.EXCUSED, 0)
    eligible = present + absent + late
    return SummaryItem(
        student_id=str(student.id),
        student_code=student.student_code,
        full_name=student.full_name,
        present=present,
        absent=absent,
        late=late,
        excused=excused,
        recorded=eligible + excused,
        eligible=eligible,
        percentage=attendance_percentage(present, eligible),
    )


def summaries(
    db: Session,
    *,
    batch_id: uuid.UUID | None,
    student_id: uuid.UUID | None,
    class_id: uuid.UUID | None,
    from_date: date | None,
    to_date: date | None,
) -> list[SummaryItem]:
    if from_date is not None and to_date is not None:
        _check_range(from_date, to_date, MAX_HISTORY_DAYS)
    _require_scope(db, batch_id=batch_id, student_id=student_id, class_id=class_id)
    grouped = _summary_counts(
        db,
        batch_id=batch_id,
        student_id=student_id,
        class_id=class_id,
        from_date=from_date,
        to_date=to_date,
    )
    student_ids = set(grouped)
    if batch_id is not None and student_id is None and class_id is None:
        enrolled_ids = set(db.scalars(select(BatchStudent.student_id).where(BatchStudent.batch_id == batch_id)).all())
        student_ids.update(enrolled_ids)
    if student_id is not None:
        student_ids.add(student_id)
    if not student_ids:
        return []
    students = list(db.scalars(select(Student).where(Student.id.in_(student_ids))).all())
    students.sort(key=lambda student: (student.full_name.casefold(), student.student_code))
    return [_summary_item(student, grouped.get(student.id, {})) for student in students]
