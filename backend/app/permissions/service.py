"""Permission lookups."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.permissions.models import Permission, RolePermission
from app.roles.models import UserRole


def get_permission_keys(db: Session, user_id: uuid.UUID) -> set[str]:
    stmt = (
        select(Permission.key)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
    )
    return set(db.scalars(stmt).all())


def list_permissions(db: Session) -> list[Permission]:
    return list(db.scalars(select(Permission).order_by(Permission.key)).all())
