"""Authentication use cases."""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.models import PasswordResetToken
from app.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.auth.tokens import find_refresh_token, issue_refresh_token, revoke_all_refresh_tokens
from app.common.exceptions import AppError, ErrorCode
from app.core.config import get_settings
from app.core.logging import log_event
from app.core.password_policy import password_rule_failures
from app.core.security import (
    create_access_token,
    dummy_password_hash,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.email.sender import EmailMessage, EmailSender
from app.roles.models import UserRole
from app.roles.service import RoleName, get_role_by_name
from app.users.models import User

logger = logging.getLogger("app.auth")

GENERIC_RESET_MESSAGE = (
    "If an account exists for this email, password reset instructions have been sent."
)
INVALID_CREDENTIALS_MESSAGE = "Invalid email or password."
INVALID_RESET_MESSAGE = "The password reset link is invalid or has expired."


@dataclass
class IssuedSession:
    user: User
    access_token: str
    refresh_token: str
    refresh_max_age: int


def mfa_challenge_required(user: User) -> bool:
    """Hook for a future second factor. No user has MFA enabled yet."""

    return getattr(user, "mfa_enabled", False) is True


def _password_error(password: str, field: str) -> None:
    failures = password_rule_failures(password)
    if not failures:
        return
    raise AppError(
        ErrorCode.VALIDATION_ERROR,
        "Password does not meet the password policy.",
        422,
        details=[
            {"field": field, "code": failure.code, "message": failure.message} for failure in failures
        ],
    )


def _mismatch(field: str) -> AppError:
    return AppError(
        ErrorCode.VALIDATION_ERROR,
        "Passwords do not match.",
        422,
        details=[
            {
                "field": field,
                "code": "PASSWORD_MISMATCH",
                "message": "Passwords do not match.",
            }
        ],
    )


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def register_user(db: Session, payload: RegisterRequest) -> User:
    if payload.password != payload.confirm_password:
        raise _mismatch("confirm_password")
    _password_error(payload.password, "password")
    if get_user_by_email(db, payload.email) is not None:
        raise AppError(
            ErrorCode.EMAIL_ALREADY_EXISTS,
            "An account with this email already exists.",
            409,
        )
    student = get_role_by_name(db, RoleName.STUDENT)
    if student is None:
        raise AppError(ErrorCode.INTERNAL_ERROR, "An unexpected error occurred.", 500)
    now = datetime.now(UTC)
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        preferred_language=payload.preferred_language,
        is_active=True,
        email_verified=False,
        session_version=1,
        created_at=now,
        updated_at=now,
    )
    user.user_roles.append(UserRole(role=student, created_at=now))
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
    db.refresh(user)
    return user


def _issue_session(
    db: Session,
    user: User,
    *,
    remember_me: bool,
    refresh_expires_at: datetime | None = None,
) -> IssuedSession:
    raw_refresh, max_age = issue_refresh_token(
        db,
        user,
        remember_me=remember_me,
        expires_at=refresh_expires_at,
    )
    access_token = create_access_token(user_id=str(user.id), session_version=user.session_version)
    db.commit()
    return IssuedSession(
        user=user,
        access_token=access_token,
        refresh_token=raw_refresh,
        refresh_max_age=max_age,
    )


def authenticate(db: Session, payload: LoginRequest, ip_address: str | None) -> IssuedSession:
    user = get_user_by_email(db, payload.email)
    if user is None:
        verify_password(payload.password, dummy_password_hash())
        record_audit(
            db,
            action="login_failed",
            actor_id=None,
            context={"reason": "invalid_credentials"},
            ip_address=ip_address,
        )
        db.commit()
        log_event(logger, "authentication_failure", reason="invalid_credentials")
        raise AppError(ErrorCode.INVALID_CREDENTIALS, INVALID_CREDENTIALS_MESSAGE, 401)
    if not verify_password(payload.password, user.password_hash):
        record_audit(
            db,
            action="login_failed",
            actor_id=user.id,
            target_type="user",
            target_id=user.id,
            context={"reason": "invalid_credentials"},
            ip_address=ip_address,
        )
        db.commit()
        log_event(logger, "authentication_failure", reason="invalid_credentials", user_id=str(user.id))
        raise AppError(ErrorCode.INVALID_CREDENTIALS, INVALID_CREDENTIALS_MESSAGE, 401)
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    if not user.is_active:
        record_audit(
            db,
            action="login_failed",
            actor_id=user.id,
            target_type="user",
            target_id=user.id,
            context={"reason": "inactive"},
            ip_address=ip_address,
        )
        db.commit()
        log_event(logger, "authentication_failure", reason="inactive", user_id=str(user.id))
        raise AppError(ErrorCode.ACCOUNT_INACTIVE, "This account is inactive.", 403)
    if mfa_challenge_required(user):
        raise AppError(ErrorCode.FORBIDDEN, "Additional verification is required.", 403)
    session = _issue_session(db, user, remember_me=payload.remember_me)
    record_audit(
        db,
        action="login",
        actor_id=user.id,
        target_type="user",
        target_id=user.id,
        context={"remember_me": payload.remember_me},
        ip_address=ip_address,
    )
    db.commit()
    log_event(logger, "authentication_success", user_id=str(user.id))
    return session


def logout(db: Session, raw_refresh: str | None, ip_address: str | None) -> None:
    if not raw_refresh:
        return
    stored = find_refresh_token(db, raw_refresh)
    if stored is None:
        return
    if stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
    record_audit(
        db,
        action="logout",
        actor_id=stored.user_id,
        target_type="user",
        target_id=stored.user_id,
        ip_address=ip_address,
    )
    db.commit()
    log_event(logger, "logout", user_id=str(stored.user_id))


def refresh_session(db: Session, raw_refresh: str | None) -> IssuedSession:
    if not raw_refresh:
        raise AppError(ErrorCode.UNAUTHENTICATED, "Authentication is required.", 401)
    stored = find_refresh_token(db, raw_refresh)
    if stored is None:
        raise AppError(ErrorCode.UNAUTHENTICATED, "Authentication is required.", 401)
    now = datetime.now(UTC)
    user = db.get(User, stored.user_id)
    if user is None:
        raise AppError(ErrorCode.UNAUTHENTICATED, "Authentication is required.", 401)
    if stored.revoked_at is not None:
        revoke_all_refresh_tokens(db, user.id, now)
        user.session_version += 1
        user.updated_at = now
        db.commit()
        log_event(logger, "refresh_token_reuse", user_id=str(user.id))
        raise AppError(ErrorCode.UNAUTHENTICATED, "Authentication is required.", 401)
    if stored.expires_at < now or not user.is_active:
        stored.revoked_at = now
        db.commit()
        raise AppError(ErrorCode.UNAUTHENTICATED, "Authentication is required.", 401)
    previous_expiry = stored.expires_at
    stored.revoked_at = now
    return _issue_session(db, user, remember_me=False, refresh_expires_at=previous_expiry)


def request_password_reset(
    db: Session,
    payload: ForgotPasswordRequest,
    email_sender: EmailSender,
    ip_address: str | None,
) -> None:
    settings = get_settings()
    user = get_user_by_email(db, payload.email)
    if user is None or not user.is_active:
        generate_opaque_token()
        log_event(logger, "password_reset_requested", outcome="ignored")
        return
    now = datetime.now(UTC)
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    raw_token = generate_opaque_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_opaque_token(raw_token),
            expires_at=now + timedelta(minutes=settings.password_reset_token_expiry_minutes),
            created_at=now,
        )
    )
    record_audit(
        db,
        action="password_reset_requested",
        actor_id=user.id,
        target_type="user",
        target_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
    link = f"{settings.frontend_base_url}/reset-password?token={raw_token}"
    message = EmailMessage(
        to=user.email,
        subject="Reset your password",
        body=(
            "A password reset was requested for your account.\n\n"
            f"Choose a new password using this link. It expires in "
            f"{settings.password_reset_token_expiry_minutes} minutes.\n\n"
            f"{link}\n\n"
            "If you did not request this, you can ignore this message.\n"
        ),
    )
    try:
        email_sender.send(message)
    except Exception as exc:
        log_event(logger, "email_delivery_failed", error_type=type(exc).__name__)
    log_event(logger, "password_reset_requested", user_id=str(user.id))


def reset_password(db: Session, payload: ResetPasswordRequest, ip_address: str | None) -> None:
    if payload.new_password != payload.confirm_password:
        raise _mismatch("confirm_password")
    _password_error(payload.new_password, "new_password")
    stored = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_opaque_token(payload.token)
        )
    )
    now = datetime.now(UTC)
    if stored is None or stored.used_at is not None or stored.expires_at < now:
        raise AppError(ErrorCode.INVALID_OR_EXPIRED_TOKEN, INVALID_RESET_MESSAGE, 400)
    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise AppError(ErrorCode.INVALID_OR_EXPIRED_TOKEN, INVALID_RESET_MESSAGE, 400)
    user.password_hash = hash_password(payload.new_password)
    user.session_version += 1
    user.updated_at = now
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    revoke_all_refresh_tokens(db, user.id, now)
    record_audit(
        db,
        action="password_reset_completed",
        actor_id=user.id,
        target_type="user",
        target_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
    log_event(logger, "password_reset_completed", user_id=str(user.id))


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)
