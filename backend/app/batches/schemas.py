"""Batch request and response schemas."""

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.batches.models import Batch, BatchStudent
from app.timetable.models import ScheduledClass


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


class BatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    subject: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=2000)
    status: str = "active"
    student_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)

    @field_validator("subject", "grade", "description", mode="before")
    @classmethod
    def blank(cls, value: object) -> object:
        return _blank_to_none(value)


class BatchUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    name: str | None = Field(default=None, max_length=200)
    subject: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = None

    @field_validator("subject", "grade", "description", mode="before")
    @classmethod
    def blank(cls, value: object) -> object:
        return _blank_to_none(value)


class AssignStudentsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)


class NextClass(BaseModel):
    id: str
    class_date: date
    start_time: time
    end_time: time


class BatchStudentItem(BaseModel):
    id: str
    student_code: str
    full_name: str
    grade: str | None
    status: str


class BatchListItem(BaseModel):
    id: str
    batch_code: str
    name: str
    subject: str | None
    grade: str | None
    status: str
    student_count: int
    next_class: NextClass | None


class BatchDetail(BaseModel):
    id: str
    batch_code: str
    name: str
    subject: str | None
    grade: str | None
    description: str | None
    status: str
    version: int
    archived_at: datetime | None
    student_count: int
    students: list[BatchStudentItem]
    next_class: NextClass | None


class BatchListData(BaseModel):
    items: list[BatchListItem]
    total: int
    limit: int
    offset: int


class BatchSummary(BaseModel):
    active_count: int


def _next_class(item: ScheduledClass | None) -> NextClass | None:
    if item is None:
        return None
    return NextClass(
        id=str(item.id),
        class_date=item.class_date,
        start_time=item.start_time,
        end_time=item.end_time,
    )


def _student_item(link: BatchStudent) -> BatchStudentItem:
    student = link.student
    return BatchStudentItem(
        id=str(student.id),
        student_code=student.student_code,
        full_name=student.full_name,
        grade=student.grade,
        status=student.status,
    )


def to_batch_list_item(batch: Batch, *, student_count: int, upcoming: ScheduledClass | None) -> BatchListItem:
    return BatchListItem(
        id=str(batch.id),
        batch_code=batch.batch_code,
        name=batch.name,
        subject=batch.subject,
        grade=batch.grade,
        status=batch.status,
        student_count=student_count,
        next_class=_next_class(upcoming),
    )


def to_batch_detail(batch: Batch, *, upcoming: ScheduledClass | None) -> BatchDetail:
    students = [
        _student_item(link)
        for link in sorted(batch.enrollments, key=lambda item: item.student.full_name.lower())
    ]
    return BatchDetail(
        id=str(batch.id),
        batch_code=batch.batch_code,
        name=batch.name,
        subject=batch.subject,
        grade=batch.grade,
        description=batch.description,
        status=batch.status,
        version=batch.version,
        archived_at=batch.archived_at,
        student_count=len(students),
        students=students,
        next_class=_next_class(upcoming),
    )
