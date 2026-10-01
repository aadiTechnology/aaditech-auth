"""Role queries."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.permissions.models import RolePermission
from app.roles.models import Role


class RoleName:
    ADMIN = "ADMIN"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"


def get_role_by_name(db: Session, name: str) -> Role | None:
    stmt = (
        select(Role)
        .where(Role.name == name)
        .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
    )
    return db.scalar(stmt)


def list_roles(db: Session) -> list[Role]:
    stmt = select(Role).options(
        selectinload(Role.role_permissions).selectinload(RolePermission.permission)
    ).order_by(Role.name)
    return list(db.scalars(stmt).all())
