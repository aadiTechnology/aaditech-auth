"""Parent contact use cases."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.selectable import Select

from app.audit.service import record_audit
from app.common.exceptions import AppError, ErrorCode
from app.common.fields import (
    clean_email,
    clean_multiline,
    clean_name,
    clean_phone,
    like_pattern,
    raise_if_errors,
)
from app.core.logging import log_event
from app.parents.models import Parent, ParentStatus
from app.students.models import StudentParent
from app.users.models import User

logger = logging.getLogger("app.parents")


def build_parent(
    *,
    full_name: str | None,
    phone: str | None,
    email: str | None,
    address: str | None,
    notes: str | None,
) -> Parent:
    errors: list[dict[str, str]] = []
    name = clean_name(full_name, errors)
    phone_value = clean_phone(phone, errors)
    email_value = clean_email(email, errors)
    address_value = clean_multiline(address, errors, "address", 500)
    notes_value = clean_multiline(notes, errors, "notes", 2000)
    raise_if_errors(errors)
    if name is None:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Validation failed.", 422)
    now = datetime.now(UTC)
    return Parent(
        full_name=name,
        phone=phone_value,
        email=email_value,
        address=address_value,
        notes=notes_value,
        status=ParentStatus.ACTIVE,
        version=1,
        created_at=now,
        updated_at=now,
    )


def _parent_query() -> Select[Any]:
    return select(Parent).options(selectinload(Parent.links).selectinload(StudentParent.student))


def get_parent(db: Session, parent_id: uuid.UUID) -> Parent | None:
    return db.scalar(_parent_query().where(Parent.id == parent_id))


def require_parent(db: Session, parent_id: uuid.UUID) -> Parent:
    parent = get_parent(db, parent_id)
    if parent is None:
        raise AppError(ErrorCode.NOT_FOUND, "Parent not found.", 404)
    return parent


def _reload_parent(db: Session, parent_id: uuid.UUID) -> Parent:
    db.expire_all()
    return require_parent(db, parent_id)


def _apply_parent_filters(stmt: Select[Any], *, q: str | None, status: str | None) -> Select[Any]:
    if status is None:
        stmt = stmt.where(Parent.status != ParentStatus.ARCHIVED)
    elif status != "all":
        stmt = stmt.where(Parent.status == status)
    if q and q.strip():
        pattern = like_pattern(q.strip())
        stmt = stmt.where(
            or_(
                Parent.full_name.ilike(pattern, escape="\\"),
                Parent.phone.ilike(pattern, escape="\\"),
                Parent.email.ilike(pattern, escape="\\"),
            )
        )
    return stmt


def list_parents(
    db: Session,
    *,
    q: str | None,
    status: str | None,
    limit: int,
    offset: int,
    sort: str,
    direction: str,
) -> tuple[list[Parent], int]:
    total = int(
        db.scalar(_apply_parent_filters(select(func.count()).select_from(Parent), q=q, status=status)) or 0
    )
    columns = {"name": Parent.full_name, "phone": Parent.phone, "status": Parent.status}
    column = columns[sort]
    ordering = column.asc() if direction == "asc" else column.desc()
    stmt = _apply_parent_filters(_parent_query(), q=q, status=status)
    stmt = stmt.order_by(ordering, Parent.id.asc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).unique().all()), total


def create_parent(
    db: Session,
    *,
    actor: User,
    full_name: str,
    phone: str | None,
    email: str | None,
    address: str | None,
    notes: str | None,
    ip_address: str | None,
) -> Parent:
    parent = build_parent(full_name=full_name, phone=phone, email=email, address=address, notes=notes)
    db.add(parent)
    record_audit(
        db,
        action="parent_created",
        actor_id=actor.id,
        target_type="parent",
        target_id=parent.id,
        context={"status": parent.status},
        ip_address=ip_address,
    )
    db.commit()
    log_event(logger, "parent_created", actor_id=str(actor.id), parent_id=str(parent.id))
    return _reload_parent(db, parent.id)


def update_parent(
    db: Session,
    *,
    actor: User,
    parent_id: uuid.UUID,
    changes: dict[str, object],
    ip_address: str | None,
) -> Parent:
    parent = require_parent(db, parent_id)
    expected = changes.get("version")
    if not isinstance(expected, int) or parent.version != expected:
        raise AppError(
            ErrorCode.STALE_UPDATE,
            "This record was changed by someone else. Reload and try again.",
            409,
        )
    errors: list[dict[str, str]] = []
    cleaned: dict[str, object] = {}
    if "full_name" in changes:
        supplied_name = changes["full_name"]
        cleaned["full_name"] = clean_name(supplied_name if isinstance(supplied_name, str) else None, errors)
    if "phone" in changes:
        phone = changes["phone"]
        cleaned["phone"] = clean_phone(phone if isinstance(phone, str) or phone is None else None, errors)
    if "email" in changes:
        email = changes["email"]
        cleaned["email"] = clean_email(email if isinstance(email, str) or email is None else None, errors)
    if "address" in changes:
        address = changes["address"]
        cleaned["address"] = clean_multiline(
            address if isinstance(address, str) or address is None else None,
            errors,
            "address",
            500,
        )
    if "notes" in changes:
        notes = changes["notes"]
        cleaned["notes"] = clean_multiline(
            notes if isinstance(notes, str) or notes is None else None,
            errors,
            "notes",
            2000,
        )
    if "status" in changes and changes["status"] is not None:
        if changes["status"] != ParentStatus.ACTIVE:
            errors.append(
                {
                    "field": "status",
                    "code": "INVALID_STATUS",
                    "message": "Use archive to deactivate a parent.",
                }
            )
        else:
            cleaned["status"] = ParentStatus.ACTIVE
    raise_if_errors(errors)
    if "full_name" in cleaned and cleaned["full_name"] is None:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Validation failed.", 422)
    if not cleaned:
        return parent
    for key, value in cleaned.items():
        setattr(parent, key, value)
    if cleaned.get("status") == ParentStatus.ACTIVE:
        parent.archived_at = None
    parent.version += 1
    parent.updated_at = datetime.now(UTC)
    record_audit(
        db,
        action="parent_updated",
        actor_id=actor.id,
        target_type="parent",
        target_id=parent.id,
        context={"fields": sorted(cleaned)},
        ip_address=ip_address,
    )
    db.commit()
    log_event(logger, "parent_updated", actor_id=str(actor.id), parent_id=str(parent.id))
    return _reload_parent(db, parent.id)


def archive_parent(
    db: Session,
    *,
    actor: User,
    parent_id: uuid.UUID,
    ip_address: str | None,
) -> Parent:
    parent = require_parent(db, parent_id)
    if parent.status != ParentStatus.ARCHIVED:
        now = datetime.now(UTC)
        parent.status = ParentStatus.ARCHIVED
        parent.archived_at = now
        parent.updated_at = now
        parent.version += 1
        record_audit(
            db,
            action="parent_archived",
            actor_id=actor.id,
            target_type="parent",
            target_id=parent.id,
            context={"status": ParentStatus.ARCHIVED},
            ip_address=ip_address,
        )
        db.commit()
        log_event(logger, "parent_archived", actor_id=str(actor.id), parent_id=str(parent.id))
        return _reload_parent(db, parent.id)
    return parent
