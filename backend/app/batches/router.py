"""Batch register routes."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import client_ip, require_permission
from app.batches import service
from app.batches.schemas import (
    AssignStudentsRequest,
    BatchCreate,
    BatchDetail,
    BatchListData,
    BatchSummary,
    BatchUpdate,
    to_batch_detail,
    to_batch_list_item,
)
from app.common.responses import ApiResponse, error_responses
from app.core.database import get_db
from app.users.models import User

router = APIRouter()


@router.get(
    "/summary",
    response_model=ApiResponse[BatchSummary],
    summary="Count active batches",
    description="Returns the number of batches with active status. Requires batches.read.",
    responses=error_responses(401, 403),
)
def batch_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("batches.read")),
) -> ApiResponse[BatchSummary]:
    return ApiResponse(data=BatchSummary(active_count=service.active_batch_count(db)), message="Success")


@router.get(
    "",
    response_model=ApiResponse[BatchListData],
    summary="List batches",
    description=(
        "Returns batches. Archived batches are hidden unless status is archived or all. "
        "Requires batches.read."
    ),
    responses=error_responses(401, 403, 422),
)
def get_batches(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("batches.read")),
    q: str | None = Query(default=None, max_length=100),
    status: Literal["active", "inactive", "archived", "all"] | None = None,
    subject: str | None = Query(default=None, max_length=100),
    grade: str | None = Query(default=None, max_length=20),
    student_id: uuid.UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: Literal["name", "code", "subject", "grade", "status", "students"] = "name",
    direction: Literal["asc", "desc"] = "asc",
) -> ApiResponse[BatchListData]:
    batches, total, counts = service.list_batches(
        db,
        q=q,
        status=status,
        subject=subject,
        grade=grade,
        student_id=student_id,
        limit=limit,
        offset=offset,
        sort=sort,
        direction=direction,
    )
    upcoming = service.upcoming_for(db, batches)
    return ApiResponse(
        data=BatchListData(
            items=[
                to_batch_list_item(
                    batch,
                    student_count=counts.get(batch.id, 0),
                    upcoming=upcoming.get(batch.id),
                )
                for batch in batches
            ],
            total=total,
            limit=limit,
            offset=offset,
        ),
        message="Success",
    )


@router.post(
    "",
    response_model=ApiResponse[BatchDetail],
    status_code=201,
    summary="Create a batch",
    description="Creates a batch and optional student assignments. Requires batches.create.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def post_batch(
    payload: BatchCreate,
    request: Request,
    actor: User = Depends(require_permission("batches.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[BatchDetail]:
    batch = service.create_batch(db, actor=actor, payload=payload, ip_address=client_ip(request))
    upcoming = service.upcoming_for(db, [batch])
    return ApiResponse(data=to_batch_detail(batch, upcoming=upcoming.get(batch.id)), message="Batch created.")


@router.get(
    "/{batch_id}",
    response_model=ApiResponse[BatchDetail],
    summary="Get a batch",
    description="Returns one batch, including assigned students. Requires batches.read.",
    responses=error_responses(401, 403, 404),
)
def get_batch(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("batches.read")),
) -> ApiResponse[BatchDetail]:
    batch = service.require_batch(db, batch_id)
    upcoming = service.upcoming_for(db, [batch])
    return ApiResponse(data=to_batch_detail(batch, upcoming=upcoming.get(batch.id)), message="Success")


@router.patch(
    "/{batch_id}",
    response_model=ApiResponse[BatchDetail],
    summary="Update a batch",
    description="Updates supplied fields and rejects a stale version. Requires batches.update.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def patch_batch(
    batch_id: uuid.UUID,
    payload: BatchUpdate,
    request: Request,
    actor: User = Depends(require_permission("batches.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[BatchDetail]:
    batch = service.update_batch(
        db,
        actor=actor,
        batch_id=batch_id,
        changes=payload.model_dump(exclude_unset=True),
        ip_address=client_ip(request),
    )
    upcoming = service.upcoming_for(db, [batch])
    return ApiResponse(data=to_batch_detail(batch, upcoming=upcoming.get(batch.id)), message="Batch updated.")


@router.post(
    "/{batch_id}/archive",
    response_model=ApiResponse[BatchDetail],
    summary="Archive a batch",
    description=(
        "Marks a batch archived without deleting the row, student links, or scheduled classes. "
        "Requires batches.archive."
    ),
    responses=error_responses(401, 403, 404),
)
def archive_batch(
    batch_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_permission("batches.archive")),
    db: Session = Depends(get_db),
) -> ApiResponse[BatchDetail]:
    batch = service.archive_batch(db, actor=actor, batch_id=batch_id, ip_address=client_ip(request))
    upcoming = service.upcoming_for(db, [batch])
    return ApiResponse(data=to_batch_detail(batch, upcoming=upcoming.get(batch.id)), message="Batch archived.")


@router.post(
    "/{batch_id}/students",
    response_model=ApiResponse[BatchDetail],
    summary="Assign students to a batch",
    description=(
        "Adds student links. Existing students and their other batches are left unchanged. "
        "Requires batches.update."
    ),
    responses=error_responses(401, 403, 404, 409, 422),
)
def assign_students(
    batch_id: uuid.UUID,
    payload: AssignStudentsRequest,
    request: Request,
    response: Response,
    actor: User = Depends(require_permission("batches.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[BatchDetail]:
    batch = service.assign_students(
        db,
        actor=actor,
        batch_id=batch_id,
        student_ids=payload.student_ids,
        ip_address=client_ip(request),
    )
    response.status_code = 201
    upcoming = service.upcoming_for(db, [batch])
    return ApiResponse(data=to_batch_detail(batch, upcoming=upcoming.get(batch.id)), message="Students assigned.")


@router.delete(
    "/{batch_id}/students/{student_id}",
    response_model=ApiResponse[BatchDetail],
    summary="Remove a student from a batch",
    description="Removes one enrollment and leaves the student record in place. Requires batches.update.",
    responses=error_responses(401, 403, 404),
)
def remove_student(
    batch_id: uuid.UUID,
    student_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_permission("batches.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[BatchDetail]:
    batch = service.remove_student(
        db,
        actor=actor,
        batch_id=batch_id,
        student_id=student_id,
        ip_address=client_ip(request),
    )
    upcoming = service.upcoming_for(db, [batch])
    return ApiResponse(data=to_batch_detail(batch, upcoming=upcoming.get(batch.id)), message="Student removed.")
