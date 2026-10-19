"""Timetable routes."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import client_ip, require_permission
from app.common.responses import ApiResponse, error_responses
from app.core.database import get_db
from app.timetable import service
from app.timetable.schemas import (
    ClassCreate,
    ClassListData,
    ClassUpdate,
    OccurrencePreview,
    PreviewData,
    RecurringCreate,
    ScheduledClassDetail,
    TimetableSummary,
    to_class_detail,
    to_class_item,
    to_upcoming,
)
from app.users.models import User

router = APIRouter()


@router.get(
    "/summary",
    response_model=ApiResponse[TimetableSummary],
    summary="Today and upcoming classes",
    description=(
        "Returns the number of scheduled classes today and the next scheduled classes. "
        "Today follows Asia/Kolkata. Requires timetable.read."
    ),
    responses=error_responses(401, 403),
)
def timetable_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("timetable.read")),
) -> ApiResponse[TimetableSummary]:
    today_count, upcoming = service.summary(db)
    return ApiResponse(
        data=TimetableSummary(today_count=today_count, upcoming=[to_upcoming(item) for item in upcoming]),
        message="Success",
    )


@router.get(
    "",
    response_model=ApiResponse[ClassListData],
    summary="List scheduled classes",
    description=(
        "Returns classes in a date range of at most 62 days. Cancelled classes are hidden unless "
        "include_cancelled is true. Dates and times are Asia/Kolkata wall-clock values. Requires timetable.read."
    ),
    responses=error_responses(401, 403, 422),
)
def get_classes(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("timetable.read")),
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    batch_id: uuid.UUID | None = None,
    include_cancelled: bool = False,
) -> ApiResponse[ClassListData]:
    items, total = service.list_classes(
        db,
        from_date=from_date,
        to_date=to_date,
        batch_id=batch_id,
        include_cancelled=include_cancelled,
    )
    return ApiResponse(
        data=ClassListData(items=[to_class_item(item) for item in items], total=total),
        message="Success",
    )


@router.post(
    "",
    response_model=ApiResponse[ScheduledClassDetail],
    status_code=201,
    summary="Schedule a class",
    description="Creates one class for an active batch. Requires timetable.create.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def post_class(
    payload: ClassCreate,
    request: Request,
    actor: User = Depends(require_permission("timetable.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[ScheduledClassDetail]:
    item = service.create_class(db, actor=actor, payload=payload, ip_address=client_ip(request))
    return ApiResponse(data=to_class_detail(item), message="Class scheduled.")


@router.post(
    "/preview",
    response_model=ApiResponse[PreviewData],
    summary="Preview recurring classes",
    description=(
        "Lists the classes that a weekly repeat would create, including conflicts. "
        "Nothing is saved. Requires timetable.create."
    ),
    responses=error_responses(401, 403, 404, 409, 422),
)
def preview_classes(
    payload: RecurringCreate,
    _: User = Depends(require_permission("timetable.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[PreviewData]:
    occurrences, conflict_count = service.preview_recurring(db, payload)
    return ApiResponse(
        data=PreviewData(
            occurrences=[
                OccurrencePreview(
                    class_date=day,
                    start_time=payload.start_time,
                    end_time=payload.end_time,
                    conflict=conflict,
                )
                for day, conflict in occurrences
            ],
            conflict_count=conflict_count,
        ),
        message="Success",
    )


@router.post(
    "/recurring",
    response_model=ApiResponse[ClassListData],
    status_code=201,
    summary="Create recurring classes",
    description=(
        "Saves one class row for each previewed date. The whole request is rejected if any date conflicts. "
        "Requires timetable.create."
    ),
    responses=error_responses(401, 403, 404, 409, 422),
)
def post_recurring(
    payload: RecurringCreate,
    request: Request,
    actor: User = Depends(require_permission("timetable.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[ClassListData]:
    items = service.create_recurring(db, actor=actor, payload=payload, ip_address=client_ip(request))
    return ApiResponse(
        data=ClassListData(items=[to_class_item(item) for item in items], total=len(items)),
        message="Classes scheduled.",
    )


@router.get(
    "/{class_id}",
    response_model=ApiResponse[ScheduledClassDetail],
    summary="Get a scheduled class",
    description="Returns one class, including cancelled classes. Requires timetable.read.",
    responses=error_responses(401, 403, 404),
)
def get_class(
    class_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("timetable.read")),
) -> ApiResponse[ScheduledClassDetail]:
    return ApiResponse(data=to_class_detail(service.require_class(db, class_id)), message="Success")


@router.patch(
    "/{class_id}",
    response_model=ApiResponse[ScheduledClassDetail],
    summary="Update a scheduled class",
    description="Updates supplied fields, rechecks conflicts, and rejects a stale version. Requires timetable.update.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def patch_class(
    class_id: uuid.UUID,
    payload: ClassUpdate,
    request: Request,
    actor: User = Depends(require_permission("timetable.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[ScheduledClassDetail]:
    item = service.update_class(
        db,
        actor=actor,
        class_id=class_id,
        changes=payload.model_dump(exclude_unset=True),
        ip_address=client_ip(request),
    )
    return ApiResponse(data=to_class_detail(item), message="Class updated.")


@router.post(
    "/{class_id}/cancel",
    response_model=ApiResponse[ScheduledClassDetail],
    summary="Cancel a scheduled class",
    description="Marks a class cancelled and keeps the row. Requires timetable.cancel.",
    responses=error_responses(401, 403, 404),
)
def cancel_class(
    class_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_permission("timetable.cancel")),
    db: Session = Depends(get_db),
) -> ApiResponse[ScheduledClassDetail]:
    item = service.cancel_class(db, actor=actor, class_id=class_id, ip_address=client_ip(request))
    return ApiResponse(data=to_class_detail(item), message="Class cancelled.")
