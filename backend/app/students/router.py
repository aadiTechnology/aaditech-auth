"""Student register routes."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import client_ip, require_permission
from app.common.exceptions import AppError, ErrorCode
from app.common.responses import ApiResponse, error_responses
from app.core.database import get_db
from app.permissions.service import get_permission_keys
from app.students import service
from app.students.schemas import (
    LinkParentRequest,
    StudentCreate,
    StudentDetail,
    StudentListData,
    StudentSummary,
    StudentUpdate,
    to_student_detail,
    to_student_list_item,
)
from app.users.models import User

router = APIRouter()


def require_link_access(
    user: User = Depends(require_permission("students.update")),
    db: Session = Depends(get_db),
) -> User:
    """Linking changes both the student and the parent, so both update permissions are required."""

    if "parents.update" not in get_permission_keys(db, user.id):
        raise AppError(ErrorCode.FORBIDDEN, "You do not have permission to perform this action.", 403)
    return user


def _require_parent_permission_for_link(db: Session, actor: User, payload: StudentCreate) -> None:
    link = payload.parent_link
    if link is None:
        return
    keys = get_permission_keys(db, actor.id)
    needs_create = bool(link.full_name and link.full_name.strip())
    needs_update = link.parent_id is not None
    if (needs_create and "parents.create" not in keys) or (needs_update and "parents.update" not in keys):
        raise AppError(ErrorCode.FORBIDDEN, "You do not have permission to perform this action.", 403)


@router.get(
    "/summary",
    response_model=ApiResponse[StudentSummary],
    summary="Count active students",
    description="Returns the number of students with active status. Requires students.read.",
    responses=error_responses(401, 403),
)
def student_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("students.read")),
) -> ApiResponse[StudentSummary]:
    return ApiResponse(data=StudentSummary(active_count=service.active_student_count(db)), message="Success")


@router.get(
    "",
    response_model=ApiResponse[StudentListData],
    summary="List students",
    description=(
        "Returns coaching-class student records. Archived students are hidden unless status is "
        "archived or all. Requires students.read."
    ),
    responses=error_responses(401, 403, 422),
)
def get_students(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("students.read")),
    q: str | None = Query(default=None, max_length=100),
    status: Literal["active", "inactive", "archived", "all"] | None = None,
    grade: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: Literal["name", "code", "grade", "status", "enrollment"] = "name",
    direction: Literal["asc", "desc"] = "asc",
) -> ApiResponse[StudentListData]:
    students, total = service.list_students(
        db,
        q=q,
        status=status,
        grade=grade,
        limit=limit,
        offset=offset,
        sort=sort,
        direction=direction,
    )
    return ApiResponse(
        data=StudentListData(
            items=[to_student_list_item(student) for student in students],
            total=total,
            limit=limit,
            offset=offset,
        ),
        message="Success",
    )


@router.post(
    "",
    response_model=ApiResponse[StudentDetail],
    status_code=201,
    summary="Create a student",
    description="Creates a class-register student and an optional parent link. Requires students.create.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def post_student(
    payload: StudentCreate,
    request: Request,
    actor: User = Depends(require_permission("students.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[StudentDetail]:
    _require_parent_permission_for_link(db, actor, payload)
    student = service.create_student(db, actor=actor, payload=payload, ip_address=client_ip(request))
    return ApiResponse(data=to_student_detail(student), message="Student created.")


@router.get(
    "/{student_id}",
    response_model=ApiResponse[StudentDetail],
    summary="Get a student",
    description="Returns one student, including linked parent contact details. Requires students.read.",
    responses=error_responses(401, 403, 404),
)
def get_student(
    student_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("students.read")),
) -> ApiResponse[StudentDetail]:
    return ApiResponse(data=to_student_detail(service.require_student(db, student_id)), message="Success")


@router.patch(
    "/{student_id}",
    response_model=ApiResponse[StudentDetail],
    summary="Update a student",
    description="Updates supplied fields and rejects a stale version. Requires students.update.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def patch_student(
    student_id: uuid.UUID,
    payload: StudentUpdate,
    request: Request,
    actor: User = Depends(require_permission("students.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[StudentDetail]:
    student = service.update_student(
        db,
        actor=actor,
        student_id=student_id,
        changes=payload.model_dump(exclude_unset=True),
        ip_address=client_ip(request),
    )
    return ApiResponse(data=to_student_detail(student), message="Student updated.")


@router.post(
    "/{student_id}/archive",
    response_model=ApiResponse[StudentDetail],
    summary="Archive a student",
    description="Marks a student archived without deleting the row or guardian links. Requires students.archive.",
    responses=error_responses(401, 403, 404),
)
def archive_student(
    student_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_permission("students.archive")),
    db: Session = Depends(get_db),
) -> ApiResponse[StudentDetail]:
    student = service.archive_student(db, actor=actor, student_id=student_id, ip_address=client_ip(request))
    return ApiResponse(data=to_student_detail(student), message="Student archived.")


@router.post(
    "/{student_id}/parents",
    response_model=ApiResponse[StudentDetail],
    summary="Link a parent to a student",
    description="Creates one student-parent link. Requires students.update and parents.update.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def link_parent(
    student_id: uuid.UUID,
    payload: LinkParentRequest,
    request: Request,
    response: Response,
    actor: User = Depends(require_link_access),
    db: Session = Depends(get_db),
) -> ApiResponse[StudentDetail]:
    service.link_student_and_parent(
        db,
        actor=actor,
        student_id=student_id,
        parent_id=payload.parent_id,
        relationship=payload.relationship,
        ip_address=client_ip(request),
    )
    response.status_code = 201
    return ApiResponse(
        data=to_student_detail(service.require_student(db, student_id)),
        message="Parent linked.",
    )


@router.delete(
    "/{student_id}/parents/{parent_id}",
    response_model=ApiResponse[StudentDetail],
    summary="Unlink a parent from a student",
    description="Removes one link and leaves both records in place. Requires students.update and parents.update.",
    responses=error_responses(401, 403, 404),
)
def unlink_parent(
    student_id: uuid.UUID,
    parent_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_link_access),
    db: Session = Depends(get_db),
) -> ApiResponse[StudentDetail]:
    service.unlink_student_and_parent(
        db,
        actor=actor,
        student_id=student_id,
        parent_id=parent_id,
        ip_address=client_ip(request),
    )
    return ApiResponse(
        data=to_student_detail(service.require_student(db, student_id)),
        message="Parent unlinked.",
    )
