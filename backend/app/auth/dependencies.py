"""Reusable authentication and authorization dependencies."""

import uuid
from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from app.auth.service import get_user_by_id
from app.common.exceptions import AppError, ErrorCode
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import (
    ACCESS_COOKIE,
    InvalidTokenError,
    decode_access_token,
    hash_opaque_token,
)
from app.permissions.service import get_permission_keys
from app.roles.service import RoleName
from app.users.models import User

access_token_cookie = APIKeyCookie(
    name=ACCESS_COOKIE,
    auto_error=False,
    scheme_name="AccessTokenCookie",
    description="HttpOnly session cookie issued at login. It is not readable by browser scripts.",
)


def client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


def _limit(key: str, limit: int, window_seconds: int) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    limiter.check(key, limit, window_seconds)


def limit_login(request: Request) -> None:
    settings = get_settings()
    _limit(
        f"login:{client_ip(request) or 'unknown'}",
        settings.login_rate_limit,
        settings.login_rate_window_seconds,
    )


def limit_register(request: Request) -> None:
    settings = get_settings()
    _limit(
        f"register:{client_ip(request) or 'unknown'}",
        settings.register_rate_limit,
        settings.register_rate_window_seconds,
    )


def limit_forgot_password(request: Request) -> None:
    settings = get_settings()
    _limit(
        f"forgot:{client_ip(request) or 'unknown'}",
        settings.forgot_password_rate_limit,
        settings.forgot_password_rate_window_seconds,
    )


def limit_forgot_password_email(email: str) -> None:
    settings = get_settings()
    _limit(
        f"forgot-email:{hash_opaque_token(email)}",
        settings.forgot_password_rate_limit,
        settings.forgot_password_rate_window_seconds,
    )


def limit_reset_password(request: Request) -> None:
    settings = get_settings()
    _limit(
        f"reset:{client_ip(request) or 'unknown'}",
        settings.reset_password_rate_limit,
        settings.reset_password_rate_window_seconds,
    )


def get_current_user(
    db: Session = Depends(get_db),
    access_token: str | None = Depends(access_token_cookie),
) -> User:
    """Require a valid access cookie and an active account."""

    if not access_token:
        raise AppError(ErrorCode.UNAUTHENTICATED, "Authentication is required.", 401)
    try:
        payload = decode_access_token(access_token)
        user_id = uuid.UUID(str(payload["sub"]))
    except (InvalidTokenError, ValueError):
        raise AppError(ErrorCode.UNAUTHENTICATED, "Authentication is required.", 401) from None
    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise AppError(ErrorCode.UNAUTHENTICATED, "Authentication is required.", 401)
    if int(payload["sv"]) != user.session_version:
        raise AppError(ErrorCode.UNAUTHENTICATED, "Authentication is required.", 401)
    return user


def require_authenticated_user(user: User = Depends(get_current_user)) -> User:
    return user


def require_permission(permission: str) -> Callable[..., User]:
    """Authorize a single permission key. Role names are not consulted here."""

    def dependency(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if permission not in get_permission_keys(db, user.id):
            raise AppError(
                ErrorCode.FORBIDDEN,
                "You do not have permission to perform this action.",
                403,
            )
        return user

    return dependency


def require_role(role_name: str) -> Callable[..., User]:
    """Authorize a database role. Prefer require_permission for feature checks."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        names = {link.role.name for link in user.user_roles}
        if role_name not in names:
            raise AppError(
                ErrorCode.FORBIDDEN,
                "You do not have permission to perform this action.",
                403,
            )
        return user

    return dependency


def require_admin_permission(permission: str) -> Callable[..., User]:
    """Require the ADMIN role and a specific permission for access-management changes."""

    def dependency(user: User = Depends(require_permission(permission))) -> User:
        names = {link.role.name for link in user.user_roles}
        if RoleName.ADMIN not in names:
            raise AppError(
                ErrorCode.FORBIDDEN,
                "You do not have permission to perform this action.",
                403,
            )
        return user

    return dependency
