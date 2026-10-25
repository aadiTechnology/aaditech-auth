"""Attendance request and response schemas."""

import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AttendanceStatusValue = Literal["present", "absent", "late", "excused"]
CompletionValue = Literal["not_recorded", "partial", "complete", "no_students"]


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


class AttendanceMarkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: uuid.UUID
    status: AttendanceStatusValue
    notes: str | None = Field(default=None, max_length=500)
    version: int | None = Field(default=None, ge=1)

    @field_validator("notes", mode="before")
    @classmethod
    def blank(cls, value: object) -> object:
        return _blank_to_none(value)


class AttendanceSave(BaseModel):
    model_config = ConfigDict(extra="forbid")

    marks: list[AttendanceMarkIn] = Field(min_length=1, max_length=200)


class RosterMark(BaseModel):
    id: str
    status: AttendanceStatusValue
    notes: str | None
    version: int
    updated_at: datetime


class RosterStudent(BaseModel):
    student_id: str
    student_code: str
    full_name: str
    student_status: str
    attendance: RosterMark | None


class ClassRoster(BaseModel):
    id: str
    batch_id: str
    batch_name: str
    batch_code: str
    class_date: date
    start_time: time
    end_time: time
    topic: str | None
    class_status: str
    completion: CompletionValue
    enrolled_count: int
    recorded_count: int
    students: list[RosterStudent]


class AttendanceClassItem(BaseModel):
    id: str
    batch_id: str
    batch_name: str
    batch_code: str
    class_date: date
    start_time: time
    end_time: time
    topic: str | None
    class_status: str
    completion: CompletionValue
    enrolled_count: int
    recorded_count: int


class AttendanceClassList(BaseModel):
    items: list[AttendanceClassItem]
    total: int


class TodayAttendance(BaseModel):
    classes: list[AttendanceClassItem]


class HistoryItem(BaseModel):
    id: str
    scheduled_class_id: str
    student_id: str
    student_code: str
    full_name: str
    batch_id: str
    batch_name: str
    batch_code: str
    class_date: date
    start_time: time
    end_time: time
    topic: str | None
    class_status: str
    status: AttendanceStatusValue
    notes: str | None
    version: int
    updated_at: datetime


class HistoryData(BaseModel):
    items: list[HistoryItem]
    total: int


class SummaryItem(BaseModel):
    student_id: str
    student_code: str
    full_name: str
    present: int
    absent: int
    late: int
    excused: int
    recorded: int
    eligible: int
    percentage: float | None


class SummaryData(BaseModel):
    items: list[SummaryItem]
