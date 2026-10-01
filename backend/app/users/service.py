"""Access-management use cases. These never trust a caller-supplied role for self-service."""

import logging
import re
import uuid
from datetime import UTC, datetime

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.tokens import revoke_all_refresh_tokens
from app.common.exceptions import AppError, ErrorCode
from app.core.logging import log_event
from app.core.password_policy import password_rule_failures
from app.core.security import hash_password
from app.roles.models import Role, UserRole
from app.roles.service import RoleName, get_role_by_name
from app.users.models import User

logger = logging.getLogger("app.users")
_ROLE_NAME = re.compile(r"^[A-Z][A-Z0-9_]{1,49}$")


def list_users(db: Session, *, limit: int, offset: int) -> tuple[list[User], int]:
    total = int(db.scalar(select(func.count()).select_from(User)) or 0)
    stmt = select(User).order_by(User.full_name, User.email).limit(limit).offset(offset)
    return list(db.scalars(stmt).all()), total


def _active_admin_count(db: Session) -> int:
    stmt = (
        select(func.count(User.id))
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.name == RoleName.ADMIN, User.is_active.is_(True))
    )
    return int(db.scalar(stmt) or 0)


def _is_active_admin(user: User) -> bool:
    return user.is_active and any(link.role.name == RoleName.ADMIN for link in user.user_roles)


def _reject_self(actor: User, target: User) -> None:
    if actor.id == target.id:
        raise AppError(
            ErrorCode.CANNOT_MODIFY_OWN_ACCESS,
            "You cannot change your own access.",
            403,
        )


def change_user_role(
    db: Session,
    *,
    actor: User,
    target_id: uuid.UUID,
    role_name: str,
    ip_address: str | None,
) -> User:
    normalized = role_name.strip().upper()
    if _ROLE_NAME.fullmatch(normalized) is None:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "Unknown role.",
            422,
            details=[{"field": "role", "code": "UNKNOWN_ROLE", "message": "Unknown role."}],
        )
    target = db.get(User, target_id)
    if target is None:
        raise AppError(ErrorCode.NOT_FOUND, "User not found.", 404)
    _reject_self(actor, target)
    role = get_role_by_name(db, normalized)
    if role is None:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "Unknown role.",
            422,
            details=[{"field": "role", "code": "UNKNOWN_ROLE", "message": "Unknown role."}],
        )
    actor_is_admin = any(link.role.name == RoleName.ADMIN for link in actor.user_roles)
    if role.name == RoleName.ADMIN and not actor_is_admin:
        raise AppError(
            ErrorCode.FORBIDDEN,
            "You do not have permission to perform this action.",
            403,
        )
    if _is_active_admin(target) and role.name != RoleName.ADMIN and _active_admin_count(db) <= 1:
        raise AppError(
            ErrorCode.LAST_ADMIN,
            "The last active administrator cannot be changed.",
            409,
        )
    previous = sorted(link.role.name for link in target.user_roles)
    now = datetime.now(UTC)
    db.execute(delete(UserRole).where(UserRole.user_id == target.id))
    db.add(UserRole(user_id=target.id, role_id=role.id, created_at=now))
    target.updated_at = now
    record_audit(
        db,
        action="role_changed",
        actor_id=actor.id,
        target_type="user",
        target_id=target.id,
        context={"from": previous, "to": [role.name]},
        ip_address=ip_address,
    )
    db.commit()
    db.expire(target, ["user_roles"])
    log_event(logger, "role_changed", actor_id=str(actor.id), target_id=str(target.id), role=role.name)
    return target


def set_user_active(
    db: Session,
    *,
    actor: User,
    target_id: uuid.UUID,
    is_active: bool,
    ip_address: str | None,
) -> User:
    target = db.get(User, target_id)
    if target is None:
        raise AppError(ErrorCode.NOT_FOUND, "User not found.", 404)
    _reject_self(actor, target)
    if (
        not is_active
        and _is_active_admin(target)
        and _active_admin_count(db) <= 1
    ):
        raise AppError(
            ErrorCode.LAST_ADMIN,
            "The last active administrator cannot be changed.",
            409,
        )
    now = datetime.now(UTC)
    target.is_active = is_active
    target.updated_at = now
    if not is_active:
        target.session_version += 1
        revoke_all_refresh_tokens(db, target.id, now)
    action = "user_activated" if is_active else "user_deactivated"
    record_audit(
        db,
        action=action,
        actor_id=actor.id,
        target_type="user",
        target_id=target.id,
        context={"is_active": is_active},
        ip_address=ip_address,
    )
    db.commit()
    log_event(logger, action, actor_id=str(actor.id), target_id=str(target.id))
    return target


def create_initial_admin(
    db: Session,
    *,
    email: str,
    full_name: str,
    password: str,
    preferred_language: str,
) -> User:
    cleaned_name = " ".join(full_name.split())
    if len(cleaned_name) < 2:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Full name must be at least 2 characters.", 422)
    try:
        normalized_email = validate_email(email, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Enter a valid email address.", 422) from None
    failures = password_rule_failures(password)
    if failures:
        raise AppError(ErrorCode.VALIDATION_ERROR, failures[0].message, 422)
    if _active_admin_count(db) > 0:
        raise AppError(
            ErrorCode.CONFLICT,
            "An administrator already exists. Manage roles from the admin access screen.",
            409,
        )
    admin_role = get_role_by_name(db, RoleName.ADMIN)
    if admin_role is None:
        raise AppError(ErrorCode.INTERNAL_ERROR, "Administrator role is not configured.", 500)
    if db.scalar(select(User).where(User.email == normalized_email)) is not None:
        raise AppError(ErrorCode.EMAIL_ALREADY_EXISTS, "An account with this email already exists.", 409)
    now = datetime.now(UTC)
    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        full_name=cleaned_name,
        preferred_language=preferred_language,
        is_active=True,
        email_verified=True,
        session_version=1,
        created_at=now,
        updated_at=now,
    )
    user.user_roles.append(UserRole(role=admin_role, created_at=now))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(
            ErrorCode.EMAIL_ALREADY_EXISTS,
            "An account with this email already exists.",
            409,
        ) from None
    log_event(logger, "initial_admin_created", user_id=str(user.id))
    return user
