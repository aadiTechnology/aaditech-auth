"""User access-management schemas."""

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth.schemas import RegisteredUser, UserProfile
from app.permissions.service import get_permission_keys
from app.users.models import User


class AccessUser(BaseModel):
    id: str
    full_name: str
    email: str
    roles: list[str]
    is_active: bool


class UserListData(BaseModel):
    items: list[AccessUser]
    total: int


class AssignRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(min_length=1, max_length=50, description="Role name to assign. Replaces existing roles.")


class UpdateStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool


def role_names(user: User) -> list[str]:
    return sorted(link.role.name for link in user.user_roles)


def to_registered_user(user: User) -> RegisteredUser:
    return RegisteredUser(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        preferred_language=user.preferred_language,
        roles=role_names(user),
    )


def to_user_profile(db: Session, user: User) -> UserProfile:
    return UserProfile(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        preferred_language=user.preferred_language,
        is_active=user.is_active,
        email_verified=user.email_verified,
        roles=role_names(user),
        permissions=sorted(get_permission_keys(db, user.id)),
    )


def to_access_user(user: User) -> AccessUser:
    return AccessUser(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        roles=role_names(user),
        is_active=user.is_active,
    )
