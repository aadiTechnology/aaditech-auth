"""Permission response schema."""

from pydantic import BaseModel

from app.permissions.models import Permission


class PermissionPublic(BaseModel):
    id: str
    key: str
    description: str


def to_permission_public(permission: Permission) -> PermissionPublic:
    return PermissionPublic(
        id=str(permission.id),
        key=permission.key,
        description=permission.description,
    )
