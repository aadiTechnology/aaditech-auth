"""HTTP helpers for authentication tests."""

import re
from datetime import UTC, datetime, timedelta

from app.auth.models import PasswordResetToken
from app.core.database import SessionLocal
from app.email.sender import get_memory_sender
from app.roles.models import UserRole
from app.roles.service import get_role_by_name
from app.users.models import User
from httpx import AsyncClient
from sqlalchemy import delete, select, update

VALID_PASSWORD = "ValidPass1!"


async def csrf_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.get("/api/v1/auth/csrf")
    assert response.status_code == 200, response.text
    token = response.json()["data"]["csrf_token"]
    return {"X-CSRF-Token": token}


async def register_student(
    client: AsyncClient,
    *,
    email: str = "student@example.com",
    password: str = VALID_PASSWORD,
    full_name: str = "Student User",
    extra: dict | None = None,
):
    payload = {
        "full_name": full_name,
        "email": email,
        "password": password,
        "confirm_password": password,
        "preferred_language": "en",
    }
    if extra:
        payload.update(extra)
    return await client.post(
        "/api/v1/auth/register",
        json=payload,
        headers=await csrf_headers(client),
    )


async def login(
    client: AsyncClient,
    *,
    email: str = "student@example.com",
    password: str = VALID_PASSWORD,
    remember_me: bool = False,
):
    return await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "remember_me": remember_me},
        headers=await csrf_headers(client),
    )


def assign_role(email: str, role_name: str) -> None:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        role = get_role_by_name(db, role_name)
        assert role is not None
        db.execute(delete(UserRole).where(UserRole.user_id == user.id))
        db.add(UserRole(user_id=user.id, role_id=role.id, created_at=datetime.now(UTC)))
        db.commit()
    finally:
        db.close()


def set_active(email: str, is_active: bool) -> None:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.is_active = is_active
        db.commit()
    finally:
        db.close()


def expire_reset_tokens(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id)
            .values(expires_at=datetime.now(UTC) - timedelta(minutes=5))
        )
        db.commit()
    finally:
        db.close()


def latest_reset_token() -> str:
    assert get_memory_sender().messages
    body = get_memory_sender().messages[-1].body
    match = re.search(r"token=([A-Za-z0-9_\-]+)", body)
    assert match is not None
    return match.group(1)
