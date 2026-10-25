"""Attendance routes."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.attendance import service
from app.attendance.schemas import (
    AttendanceClassList,
    AttendanceSave,
    ClassRoster,
    HistoryData,
    SummaryData,
    TodayAttendance,
)
from app.auth.dependencies import client_ip, require_permission
from app.common.responses import ApiResponse, error_responses
from app.core.database import get_db
from app.users.models import User

router = APIRouter()


@router.get(
    "/today",
    response_model=ApiResponse[TodayAttendance],
    summary="Attendance status for today's classes",
    description=(
        "Returns today's scheduled classes and whether attendance is unrecorded, partial, or complete. "
        "Today follows Asia/Kolkata. Requires attendance.read."
    ),
    responses=error_responses(401, 403),
)
def attendance_today(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("attendance.read")),
) -> ApiResponse[TodayAttendance]:
    return ApiResponse(data=TodayAttendance(classes=service.today_classes(db)), message="Success")


@router.get(
    "/classes",
    response_model=ApiResponse[AttendanceClassList],
    summary="List classes for attendance",
    description=(
        "Returns classes for one batch in a date range of at most 62 days, with attendance completion. "
        "Requires attendance.read."
    ),
    responses=error_responses(401, 403, 404, 422),
)
def attendance_classes(
    batch_id: uuid.UUID,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    include_cancelled: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("attendance.read")),
) -> ApiResponse[AttendanceClassList]:
    items, total = service.list_attendance_classes(
        db,
        batch_id=batch_id,
        from_date=from_date,
        to_date=to_date,
        include_cancelled=include_cancelled,
    )
    return ApiResponse(data=AttendanceClassList(items=items, total=total), message="Success")


@router.get(
    "/classes/{class_id}",
    response_model=ApiResponse[ClassRoster],
    summary="Students and attendance for one class",
    description=(
        "Returns students currently enrolled in the class batch and any attendance already saved for them. "
        "A student with no row is not absent. Requires attendance.read."
    ),
    responses=error_responses(401, 403, 404),
)
def attendance_roster(
    class_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("attendance.read")),
) -> ApiResponse[ClassRoster]:
    return ApiResponse(data=service.get_roster(db, class_id), message="Success")


@router.post(
    "/classes/{class_id}",
    response_model=ApiResponse[ClassRoster],
    summary="Save attendance for a class",
    description=(
        "Creates or updates attendance for the listed students in one transaction. "
        "Students omitted from the request stay unrecorded. "
        "Each student must be enrolled in the class batch. Requires attendance.update."
    ),
    responses=error_responses(401, 403, 404, 409, 422),
)
def save_class_attendance(
    class_id: uuid.UUID,
    payload: AttendanceSave,
    request: Request,
    actor: User = Depends(require_permission("attendance.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[ClassRoster]:
    roster = service.save_attendance(
        db,
        actor=actor,
        class_id=class_id,
        marks=payload.marks,
        ip_address=client_ip(request),
    )
    return ApiResponse(data=roster, message="Attendance saved.")


@router.get(
    "/history",
    response_model=ApiResponse[HistoryData],
    summary="Attendance history",
    description=(
        "Returns saved attendance for a batch, student, or class. "
        "Unrecorded students are not included. Requires attendance.read."
    ),
    responses=error_responses(401, 403, 404, 422),
)
def attendance_history(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("attendance.read")),
    batch_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    class_id: uuid.UUID | None = None,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[HistoryData]:
    items, total = service.history(
        db,
        batch_id=batch_id,
        student_id=student_id,
        class_id=class_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data=HistoryData(items=items, total=total), message="Success")


@router.get(
    "/summary",
    response_model=ApiResponse[SummaryData],
    summary="Attendance summaries",
    description=(
        "Counts saved attendance. Percentage is present divided by present, absent, and late records. "
        "Excused records and classes with no row are excluded. Requires attendance.read."
    ),
    responses=error_responses(401, 403, 404, 422),
)
def attendance_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("attendance.read")),
    batch_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    class_id: uuid.UUID | None = None,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
) -> ApiResponse[SummaryData]:
    items = service.summaries(
        db,
        batch_id=batch_id,
        student_id=student_id,
        class_id=class_id,
        from_date=from_date,
        to_date=to_date,
    )
    return ApiResponse(data=SummaryData(items=items), message="Success")
