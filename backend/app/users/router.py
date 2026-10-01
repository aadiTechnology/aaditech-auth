"""Admin access-management routes."""

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import client_ip, require_admin_permission, require_permission
from app.common.responses import ApiResponse, error_responses
from app.core.database import get_db
from app.users.models import User
from app.users.schemas import (
    AccessUser,
    AssignRoleRequest,
    UpdateStatusRequest,
    UserListData,
    to_access_user,
)
from app.users.service import change_user_role, list_users, set_user_active

router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[UserListData],
    summary="List users",
    description="Returns accounts with their current roles and active status. Requires users.read.",
    responses=error_responses(401, 403),
    dependencies=[Depends(require_permission("users.read"))],
)
def get_users(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[UserListData]:
    users, total = list_users(db, limit=limit, offset=offset)
    return ApiResponse(
        data=UserListData(items=[to_access_user(user) for user in users], total=total),
        message="Success",
    )


@router.patch(
    "/{user_id}/role",
    response_model=ApiResponse[AccessUser],
    summary="Assign a role",
    description=(
        "Replaces another user's roles. Requires an authenticated administrator with roles.assign. "
        "A user cannot change their own role, and the last active administrator cannot be demoted."
    ),
    responses=error_responses(401, 403, 404, 409, 422),
)
def assign_role(
    user_id: uuid.UUID,
    payload: AssignRoleRequest,
    request: Request,
    actor: User = Depends(require_admin_permission("roles.assign")),
    db: Session = Depends(get_db),
) -> ApiResponse[AccessUser]:
    updated = change_user_role(
        db,
        actor=actor,
        target_id=user_id,
        role_name=payload.role,
        ip_address=client_ip(request),
    )
    return ApiResponse(data=to_access_user(updated), message="Role updated.")


@router.patch(
    "/{user_id}/status",
    response_model=ApiResponse[AccessUser],
    summary="Activate or deactivate a user",
    description=(
        "Requires an authenticated administrator with users.update. "
        "Deactivation revokes that user's sessions. Users cannot change their own status."
    ),
    responses=error_responses(401, 403, 404, 409, 422),
)
def update_status(
    user_id: uuid.UUID,
    payload: UpdateStatusRequest,
    request: Request,
    actor: User = Depends(require_admin_permission("users.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[AccessUser]:
    updated = set_user_active(
        db,
        actor=actor,
        target_id=user_id,
        is_active=payload.is_active,
        ip_address=client_ip(request),
    )
    return ApiResponse(data=to_access_user(updated), message="User updated.")
