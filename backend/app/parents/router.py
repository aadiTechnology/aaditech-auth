"""Parent and guardian routes."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import client_ip, require_permission
from app.common.responses import ApiResponse, error_responses
from app.core.database import get_db
from app.parents import service
from app.parents.schemas import (
    LinkStudentRequest,
    ParentCreate,
    ParentDetail,
    ParentListData,
    ParentUpdate,
    to_parent_detail,
    to_parent_list_item,
)
from app.students.router import require_link_access
from app.students.service import link_student_and_parent, unlink_student_and_parent
from app.users.models import User

router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[ParentListData],
    summary="List parents",
    description=(
        "Returns parent and guardian contacts. Archived parents are hidden unless requested. "
        "Requires parents.read."
    ),
    responses=error_responses(401, 403, 422),
)
def get_parents(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("parents.read")),
    q: str | None = Query(default=None, max_length=100),
    status: Literal["active", "archived", "all"] | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: Literal["name", "phone", "status"] = "name",
    direction: Literal["asc", "desc"] = "asc",
) -> ApiResponse[ParentListData]:
    parents, total = service.list_parents(
        db,
        q=q,
        status=status,
        limit=limit,
        offset=offset,
        sort=sort,
        direction=direction,
    )
    return ApiResponse(
        data=ParentListData(
            items=[to_parent_list_item(parent) for parent in parents],
            total=total,
            limit=limit,
            offset=offset,
        ),
        message="Success",
    )


@router.post(
    "",
    response_model=ApiResponse[ParentDetail],
    status_code=201,
    summary="Create a parent",
    description=(
        "Creates a parent or guardian contact. Phone numbers are not required to be unique. "
        "Requires parents.create."
    ),
    responses=error_responses(401, 403, 422),
)
def post_parent(
    payload: ParentCreate,
    request: Request,
    actor: User = Depends(require_permission("parents.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[ParentDetail]:
    parent = service.create_parent(
        db,
        actor=actor,
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        address=payload.address,
        notes=payload.notes,
        ip_address=client_ip(request),
    )
    return ApiResponse(data=to_parent_detail(parent), message="Parent created.")


@router.get(
    "/{parent_id}",
    response_model=ApiResponse[ParentDetail],
    summary="Get a parent",
    description="Returns one parent and the linked students. Requires parents.read.",
    responses=error_responses(401, 403, 404),
)
def get_parent(
    parent_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("parents.read")),
) -> ApiResponse[ParentDetail]:
    return ApiResponse(data=to_parent_detail(service.require_parent(db, parent_id)), message="Success")


@router.patch(
    "/{parent_id}",
    response_model=ApiResponse[ParentDetail],
    summary="Update a parent",
    description="Updates supplied fields and rejects a stale version. Requires parents.update.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def patch_parent(
    parent_id: uuid.UUID,
    payload: ParentUpdate,
    request: Request,
    actor: User = Depends(require_permission("parents.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[ParentDetail]:
    parent = service.update_parent(
        db,
        actor=actor,
        parent_id=parent_id,
        changes=payload.model_dump(exclude_unset=True),
        ip_address=client_ip(request),
    )
    return ApiResponse(data=to_parent_detail(parent), message="Parent updated.")


@router.post(
    "/{parent_id}/archive",
    response_model=ApiResponse[ParentDetail],
    summary="Archive a parent",
    description="Marks a parent archived without deleting linked students. Requires parents.archive.",
    responses=error_responses(401, 403, 404),
)
def archive_parent(
    parent_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_permission("parents.archive")),
    db: Session = Depends(get_db),
) -> ApiResponse[ParentDetail]:
    parent = service.archive_parent(db, actor=actor, parent_id=parent_id, ip_address=client_ip(request))
    return ApiResponse(data=to_parent_detail(parent), message="Parent archived.")


@router.post(
    "/{parent_id}/students",
    response_model=ApiResponse[ParentDetail],
    summary="Link a student to a parent",
    description="Creates one student-parent link. Requires students.update and parents.update.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def link_student(
    parent_id: uuid.UUID,
    payload: LinkStudentRequest,
    request: Request,
    response: Response,
    actor: User = Depends(require_link_access),
    db: Session = Depends(get_db),
) -> ApiResponse[ParentDetail]:
    link_student_and_parent(
        db,
        actor=actor,
        student_id=payload.student_id,
        parent_id=parent_id,
        relationship=payload.relationship,
        ip_address=client_ip(request),
    )
    response.status_code = 201
    return ApiResponse(data=to_parent_detail(service.require_parent(db, parent_id)), message="Student linked.")


@router.delete(
    "/{parent_id}/students/{student_id}",
    response_model=ApiResponse[ParentDetail],
    summary="Unlink a student from a parent",
    description="Removes one link and leaves both records in place. Requires students.update and parents.update.",
    responses=error_responses(401, 403, 404),
)
def unlink_student(
    parent_id: uuid.UUID,
    student_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_link_access),
    db: Session = Depends(get_db),
) -> ApiResponse[ParentDetail]:
    unlink_student_and_parent(
        db,
        actor=actor,
        student_id=student_id,
        parent_id=parent_id,
        ip_address=client_ip(request),
    )
    return ApiResponse(data=to_parent_detail(service.require_parent(db, parent_id)), message="Student unlinked.")
