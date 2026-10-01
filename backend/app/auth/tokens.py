"""Refresh-token persistence. Raw tokens are never stored."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.models import RefreshToken
from app.core.config import get_settings
from app.core.security import generate_opaque_token, hash_opaque_token
from app.users.models import User


def revoke_all_refresh_tokens(db: Session, user_id: uuid.UUID, when: datetime | None = None) -> None:
    moment = when or datetime.now(UTC)
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=moment)
    )


def issue_refresh_token(
    db: Session,
    user: User,
    *,
    remember_me: bool,
    expires_at: datetime | None = None,
) -> tuple[str, int]:
    settings = get_settings()
    raw_token = generate_opaque_token()
    now = datetime.now(UTC)
    if expires_at is None:
        days = settings.remember_me_expire_days if remember_me else settings.refresh_token_expire_days
        expires_at = now + timedelta(days=days)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_opaque_token(raw_token),
            expires_at=expires_at,
            created_at=now,
        )
    )
    return raw_token, max(1, int((expires_at - now).total_seconds()))


def find_refresh_token(db: Session, raw_token: str) -> RefreshToken | None:
    token_hash = hash_opaque_token(raw_token)
    return db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
