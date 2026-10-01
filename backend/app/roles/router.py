"""Role catalogue routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.common.responses import ApiResponse, error_responses
from app.core.database import get_db
from app.roles.schemas import RolePublic, to_role_public
from app.roles.service import list_roles

router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[list[RolePublic]],
    summary="List roles and their permissions",
    description="Returns every role and the permissions explicitly granted to it. Requires roles.read.",
    responses=error_responses(401, 403),
    dependencies=[Depends(require_permission("roles.read"))],
)
def get_roles(db: Session = Depends(get_db)) -> ApiResponse[list[RolePublic]]:
    return ApiResponse(data=[to_role_public(role) for role in list_roles(db)], message="Success")
