"""Permission catalogue routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.common.responses import ApiResponse, error_responses
from app.core.database import get_db
from app.permissions.schemas import PermissionPublic, to_permission_public
from app.permissions.service import list_permissions

router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[list[PermissionPublic]],
    summary="List permissions",
    description="Returns the permission catalogue. Requires roles.read.",
    responses=error_responses(401, 403),
    dependencies=[Depends(require_permission("roles.read"))],
)
def get_permissions(db: Session = Depends(get_db)) -> ApiResponse[list[PermissionPublic]]:
    return ApiResponse(
        data=[to_permission_public(permission) for permission in list_permissions(db)],
        message="Success",
    )
