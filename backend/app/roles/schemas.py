"""Role response schemas."""

from pydantic import BaseModel

from app.roles.models import Role


class PermissionPublic(BaseModel):
    id: str
    key: str
    description: str


class RolePublic(BaseModel):
    id: str
    name: str
    description: str
    permissions: list[PermissionPublic]


def to_role_public(role: Role) -> RolePublic:
    permissions = [
        PermissionPublic(
            id=str(link.permission.id),
            key=link.permission.key,
            description=link.permission.description,
        )
        for link in role.role_permissions
    ]
    permissions.sort(key=lambda item: item.key)
    return RolePublic(
        id=str(role.id),
        name=role.name,
        description=role.description,
        permissions=permissions,
    )
