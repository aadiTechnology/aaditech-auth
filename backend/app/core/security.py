"""Password hashing and access-token primitives."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "x-csrf-token"
JWT_ALGORITHM = "HS256"


class InvalidTokenError(Exception):
    """Raised when an access token cannot be trusted."""


@lru_cache
def get_password_hasher() -> PasswordHasher:
    settings = get_settings()
    if settings.app_env == "test":
        return PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
    return PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)


def hash_password(password: str) -> str:
    return get_password_hasher().hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        valid = get_password_hasher().verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    return bool(valid)


def password_needs_rehash(password_hash: str) -> bool:
    return get_password_hasher().check_needs_rehash(password_hash)


@lru_cache
def dummy_password_hash() -> str:
    return hash_password("dummy-password-not-used-for-accounts")


def hash_opaque_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(*, user_id: str, session_version: int) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "type": "access",
        "sv": session_version,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError from exc
    if payload.get("type") != "access" or "sub" not in payload or "sv" not in payload:
        raise InvalidTokenError
    return payload
