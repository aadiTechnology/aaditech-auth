"""Meeting-link routes.

These routes read and update the link stored on a scheduled class.
They do not create a class, a batch, or a Google Calendar event.
"""

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import client_ip, require_permission
from app.common.responses import ApiResponse, error_responses
from app.common.time import coaching_today
from app.core.database import get_db
from app.meet.service import set_meet_link
from app.timetable.schemas import ClassListData, MeetLinkUpdate, ScheduledClassDetail, to_class_detail, to_class_item
from app.timetable.service import list_classes, require_class
from app.users.models import User

router = APIRouter()


@router.get(
    "/upcoming",
    response_model=ApiResponse[ClassListData],
    summary="List classes and their meeting links",
    description=(
        "Returns scheduled classes in a date range of at most 62 days, including whether a Meet link is saved. "
        "Dates default to today through the next 14 days in Asia/Kolkata. Requires meet.read."
    ),
    responses=error_responses(401, 403, 422),
)
def upcoming_meetings(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("meet.read")),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    batch_id: uuid.UUID | None = None,
) -> ApiResponse[ClassListData]:
    start = from_date or coaching_today()
    end = to_date or (start + timedelta(days=14))
    items, total = list_classes(db, from_date=start, to_date=end, batch_id=batch_id, include_cancelled=False)
    return ApiResponse(
        data=ClassListData(items=[to_class_item(item) for item in items], total=total),
        message="Success",
    )


@router.get(
    "/classes/{class_id}",
    response_model=ApiResponse[ScheduledClassDetail],
    summary="Get a class meeting link",
    description="Returns one scheduled class and its Meet link. Requires meet.read.",
    responses=error_responses(401, 403, 404),
)
def get_meeting(
    class_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("meet.read")),
) -> ApiResponse[ScheduledClassDetail]:
    return ApiResponse(data=to_class_detail(require_class(db, class_id)), message="Success")


@router.patch(
    "/classes/{class_id}",
    response_model=ApiResponse[ScheduledClassDetail],
    summary="Add or replace a meeting link",
    description=(
        "Stores a Google Meet URL on an existing scheduled class, or clears it when meet_url is null. "
        "Requires meet.update. A stale version is rejected."
    ),
    responses=error_responses(401, 403, 404, 409, 422),
)
def patch_meeting(
    class_id: uuid.UUID,
    payload: MeetLinkUpdate,
    request: Request,
    actor: User = Depends(require_permission("meet.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[ScheduledClassDetail]:
    item = set_meet_link(
        db,
        actor=actor,
        class_id=class_id,
        version=payload.version,
        meet_url=payload.meet_url,
        ip_address=client_ip(request),
    )
    message = "Meeting link saved." if item.meet_url else "Meeting link removed."
    return ApiResponse(data=to_class_detail(item), message=message)
