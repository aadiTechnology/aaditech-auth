"""Student register use cases."""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.selectable import Select

from app.audit.service import record_audit
from app.common.exceptions import AppError, ErrorCode
from app.common.fields import (
    add_error,
    clean_date_of_birth,
    clean_email,
    clean_enrollment_date,
    clean_grade,
    clean_multiline,
    clean_name,
    clean_phone,
    clean_relationship,
    clean_single_line,
    like_pattern,
    raise_if_errors,
)
from app.core.logging import log_event
from app.parents.models import Parent, ParentStatus
from app.parents.service import build_parent
from app.students.models import Student, StudentParent, StudentStatus
from app.students.schemas import ParentLinkCreate, StudentCreate
from app.users.models import User

logger = logging.getLogger("app.students")


@dataclass
class _LinkPlan:
    parent: Parent | None = None
    relationship: str | None = None
    is_new: bool = False
    missing: bool = False
    archived: bool = False


def _as_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _next_student_code(db: Session) -> str:
    value = db.execute(text("SELECT nextval('student_code_seq')")).scalar_one()
    return f"STU-{int(value):06d}"


def _student_query() -> Select[Any]:
    return select(Student).options(selectinload(Student.links).selectinload(StudentParent.parent))


def get_student(db: Session, student_id: uuid.UUID) -> Student | None:
    return db.scalar(_student_query().where(Student.id == student_id))


def require_student(db: Session, student_id: uuid.UUID) -> Student:
    student = get_student(db, student_id)
    if student is None:
        raise AppError(ErrorCode.NOT_FOUND, "Student not found.", 404)
    return student


def _reload_student(db: Session, student_id: uuid.UUID) -> Student:
    db.expire_all()
    return require_student(db, student_id)


def _apply_student_filters(
    stmt: Select[Any],
    *,
    q: str | None,
    status: str | None,
    grade: str | None,
) -> Select[Any]:
    if status is None:
        stmt = stmt.where(Student.status != StudentStatus.ARCHIVED)
    elif status != "all":
        stmt = stmt.where(Student.status == status)
    if grade:
        stmt = stmt.where(Student.grade == grade)
    if q and q.strip():
        pattern = like_pattern(q.strip())
        stmt = stmt.where(
            or_(
                Student.full_name.ilike(pattern, escape="\\"),
                Student.student_code.ilike(pattern, escape="\\"),
            )
        )
    return stmt


def list_students(
    db: Session,
    *,
    q: str | None,
    status: str | None,
    grade: str | None,
    limit: int,
    offset: int,
    sort: str,
    direction: str,
) -> tuple[list[Student], int]:
    selected_grade = None
    if grade and grade.strip():
        errors: list[dict[str, str]] = []
        selected_grade = clean_grade(grade, errors)
        raise_if_errors(errors)
    total = int(
        db.scalar(
            _apply_student_filters(
                select(func.count()).select_from(Student),
                q=q,
                status=status,
                grade=selected_grade,
            )
        )
        or 0
    )
    columns = {
        "name": Student.full_name,
        "code": Student.student_code,
        "grade": Student.grade,
        "status": Student.status,
        "enrollment": Student.enrollment_date,
    }
    column = columns[sort]
    ordering = column.asc() if direction == "asc" else column.desc()
    stmt = _apply_student_filters(_student_query(), q=q, status=status, grade=selected_grade)
    stmt = stmt.order_by(ordering, Student.id.asc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).unique().all()), total


def active_student_count(db: Session) -> int:
    stmt = select(func.count()).select_from(Student).where(Student.status == StudentStatus.ACTIVE)
    return int(db.scalar(stmt) or 0)


def _plan_parent_link(db: Session, link: ParentLinkCreate | None, errors: list[dict[str, str]]) -> _LinkPlan:
    if link is None:
        return _LinkPlan()
    has_id = link.parent_id is not None
    has_name = bool(link.full_name and link.full_name.strip())
    relationship = clean_relationship(link.relationship, errors, "parent_link.relationship")
    if has_id and has_name:
        add_error(
            errors,
            "parent_link",
            "INVALID",
            "Link an existing parent or enter a new parent, not both.",
        )
        return _LinkPlan(relationship=relationship)
    if not has_id and not has_name:
        add_error(errors, "parent_link", "REQUIRED", "Choose a parent or enter the parent's name.")
        return _LinkPlan(relationship=relationship)
    if has_id and link.parent_id is not None:
        parent = db.get(Parent, link.parent_id)
        if parent is None:
            return _LinkPlan(relationship=relationship, missing=True)
        if parent.status != ParentStatus.ACTIVE:
            return _LinkPlan(relationship=relationship, archived=True)
        return _LinkPlan(parent=parent, relationship=relationship)
    return _LinkPlan(relationship=relationship, is_new=True)


def _raise_for_link_plan(plan: _LinkPlan) -> None:
    if plan.missing:
        raise AppError(ErrorCode.NOT_FOUND, "Parent not found.", 404)
    if plan.archived:
        raise AppError(ErrorCode.CONFLICT, "Archived records cannot be linked.", 409)


def create_student(
    db: Session,
    *,
    actor: User,
    payload: StudentCreate,
    ip_address: str | None,
) -> Student:
    errors: list[dict[str, str]] = []
    name = clean_name(payload.full_name, errors)
    school = clean_single_line(payload.school_name, errors, "school_name", 200)
    grade = clean_grade(payload.grade, errors)
    address = clean_multiline(payload.address, errors, "address", 500)
    notes = clean_multiline(payload.notes, errors, "notes", 2000)
    dob = clean_date_of_birth(payload.date_of_birth, errors)
    enrollment = clean_enrollment_date(payload.enrollment_date, errors)
    plan = _plan_parent_link(db, payload.parent_link, errors)
    if plan.is_new and payload.parent_link is not None:
        clean_name(payload.parent_link.full_name, errors, "parent_link.full_name")
        clean_phone(payload.parent_link.phone, errors, "parent_link.phone")
        clean_email(payload.parent_link.email, errors, "parent_link.email")
    raise_if_errors(errors)
    _raise_for_link_plan(plan)
    new_parent = None
    if plan.is_new and payload.parent_link is not None:
        new_parent = build_parent(
            full_name=payload.parent_link.full_name,
            phone=payload.parent_link.phone,
            email=payload.parent_link.email,
            address=None,
            notes=None,
        )
    if name is None:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Validation failed.", 422)
    now = datetime.now(UTC)
    student = Student(
        student_code=_next_student_code(db),
        full_name=name,
        date_of_birth=dob,
        school_name=school,
        grade=grade,
        address=address,
        enrollment_date=enrollment,
        status=payload.status,
        notes=notes,
        version=1,
        created_at=now,
        updated_at=now,
    )
    db.add(student)
    parent = new_parent or plan.parent
    if parent is not None:
        if new_parent is not None:
            db.add(new_parent)
            record_audit(
                db,
                action="parent_created",
                actor_id=actor.id,
                target_type="parent",
                target_id=new_parent.id,
                context={"status": new_parent.status},
                ip_address=ip_address,
            )
        db.add(
            StudentParent(
                student=student,
                parent=parent,
                relationship_name=plan.relationship,
                created_at=now,
            )
        )
    record_audit(
        db,
        action="student_created",
        actor_id=actor.id,
        target_type="student",
        target_id=student.id,
        context={"status": student.status},
        ip_address=ip_address,
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(ErrorCode.CONFLICT, "The student could not be saved.", 409) from None
    log_event(logger, "student_created", actor_id=str(actor.id), student_id=str(student.id))
    return _reload_student(db, student.id)


def update_student(
    db: Session,
    *,
    actor: User,
    student_id: uuid.UUID,
    changes: dict[str, object],
    ip_address: str | None,
) -> Student:
    student = require_student(db, student_id)
    expected = changes.get("version")
    if not isinstance(expected, int) or student.version != expected:
        raise AppError(
            ErrorCode.STALE_UPDATE,
            "This record was changed by someone else. Reload and try again.",
            409,
        )
    errors: list[dict[str, str]] = []
    cleaned: dict[str, object] = {}
    if "full_name" in changes:
        cleaned["full_name"] = clean_name(
            changes["full_name"] if isinstance(changes["full_name"], str) else None,
            errors,
        )
    if "status" in changes and changes["status"] is not None:
        status = changes["status"]
        if status not in {StudentStatus.ACTIVE, StudentStatus.INACTIVE}:
            add_error(errors, "status", "INVALID_STATUS", "Choose active or inactive.")
        else:
            cleaned["status"] = status
    if "date_of_birth" in changes:
        cleaned["date_of_birth"] = clean_date_of_birth(_as_date(changes["date_of_birth"]), errors)
    if "school_name" in changes:
        value = changes["school_name"]
        cleaned["school_name"] = clean_single_line(
            value if isinstance(value, str) or value is None else None,
            errors,
            "school_name",
            200,
        )
    if "grade" in changes:
        value = changes["grade"]
        cleaned["grade"] = clean_grade(value if isinstance(value, str) or value is None else None, errors)
    if "address" in changes:
        value = changes["address"]
        cleaned["address"] = clean_multiline(
            value if isinstance(value, str) or value is None else None,
            errors,
            "address",
            500,
        )
    if "enrollment_date" in changes:
        cleaned["enrollment_date"] = clean_enrollment_date(_as_date(changes["enrollment_date"]), errors)
    if "notes" in changes:
        value = changes["notes"]
        cleaned["notes"] = clean_multiline(
            value if isinstance(value, str) or value is None else None,
            errors,
            "notes",
            2000,
        )
    raise_if_errors(errors)
    if "full_name" in cleaned and cleaned["full_name"] is None:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Validation failed.", 422)
    if not cleaned:
        return student
    for key, value in cleaned.items():
        setattr(student, key, value)
    if "status" in cleaned:
        student.archived_at = None
    student.version += 1
    student.updated_at = datetime.now(UTC)
    record_audit(
        db,
        action="student_updated",
        actor_id=actor.id,
        target_type="student",
        target_id=student.id,
        context={"fields": sorted(str(key) for key in cleaned)},
        ip_address=ip_address,
    )
    db.commit()
    log_event(logger, "student_updated", actor_id=str(actor.id), student_id=str(student.id))
    return _reload_student(db, student.id)


def archive_student(
    db: Session,
    *,
    actor: User,
    student_id: uuid.UUID,
    ip_address: str | None,
) -> Student:
    student = require_student(db, student_id)
    if student.status != StudentStatus.ARCHIVED:
        now = datetime.now(UTC)
        student.status = StudentStatus.ARCHIVED
        student.archived_at = now
        student.updated_at = now
        student.version += 1
        record_audit(
            db,
            action="student_archived",
            actor_id=actor.id,
            target_type="student",
            target_id=student.id,
            context={"status": StudentStatus.ARCHIVED},
            ip_address=ip_address,
        )
        db.commit()
        log_event(logger, "student_archived", actor_id=str(actor.id), student_id=str(student.id))
        return _reload_student(db, student.id)
    return student


def _require_active_pair(db: Session, student_id: uuid.UUID, parent_id: uuid.UUID) -> tuple[Student, Parent]:
    student = db.get(Student, student_id)
    if student is None:
        raise AppError(ErrorCode.NOT_FOUND, "Student not found.", 404)
    parent = db.get(Parent, parent_id)
    if parent is None:
        raise AppError(ErrorCode.NOT_FOUND, "Parent not found.", 404)
    if student.status == StudentStatus.ARCHIVED or parent.status == ParentStatus.ARCHIVED:
        raise AppError(ErrorCode.CONFLICT, "Archived records cannot be linked.", 409)
    return student, parent


def link_student_and_parent(
    db: Session,
    *,
    actor: User,
    student_id: uuid.UUID,
    parent_id: uuid.UUID,
    relationship: str | None,
    ip_address: str | None,
) -> None:
    _require_active_pair(db, student_id, parent_id)
    errors: list[dict[str, str]] = []
    relationship_name = clean_relationship(relationship, errors)
    raise_if_errors(errors)
    if db.get(StudentParent, (student_id, parent_id)) is not None:
        raise AppError(
            ErrorCode.DUPLICATE_LINK,
            "This parent is already linked to this student.",
            409,
        )
    now = datetime.now(UTC)
    db.add(
        StudentParent(
            student_id=student_id,
            parent_id=parent_id,
            relationship_name=relationship_name,
            created_at=now,
        )
    )
    record_audit(
        db,
        action="student_parent_linked",
        actor_id=actor.id,
        target_type="student",
        target_id=student_id,
        context={"parent_id": str(parent_id)},
        ip_address=ip_address,
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(
            ErrorCode.DUPLICATE_LINK,
            "This parent is already linked to this student.",
            409,
        ) from None
    log_event(
        logger,
        "student_parent_linked",
        actor_id=str(actor.id),
        student_id=str(student_id),
        parent_id=str(parent_id),
    )


def unlink_student_and_parent(
    db: Session,
    *,
    actor: User,
    student_id: uuid.UUID,
    parent_id: uuid.UUID,
    ip_address: str | None,
) -> None:
    if db.get(Student, student_id) is None:
        raise AppError(ErrorCode.NOT_FOUND, "Student not found.", 404)
    if db.get(Parent, parent_id) is None:
        raise AppError(ErrorCode.NOT_FOUND, "Parent not found.", 404)
    link = db.get(StudentParent, (student_id, parent_id))
    if link is None:
        raise AppError(ErrorCode.NOT_FOUND, "This parent is not linked to this student.", 404)
    db.delete(link)
    record_audit(
        db,
        action="student_parent_unlinked",
        actor_id=actor.id,
        target_type="student",
        target_id=student_id,
        context={"parent_id": str(parent_id)},
        ip_address=ip_address,
    )
    db.commit()
    log_event(
        logger,
        "student_parent_unlinked",
        actor_id=str(actor.id),
        student_id=str(student_id),
        parent_id=str(parent_id),
    )
