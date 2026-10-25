"""Timetable request and response schemas."""

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.meet.urls import meet_link_status
from app.timetable.models import ScheduledClass


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


class ClassCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: uuid.UUID
    class_date: date
    start_time: time
    end_time: time
    topic: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("topic", "notes", mode="before")
    @classmethod
    def blank(cls, value: object) -> object:
        return _blank_to_none(value)


class ClassUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    batch_id: uuid.UUID | None = None
    class_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    topic: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("topic", "notes", mode="before")
    @classmethod
    def blank(cls, value: object) -> object:
        return _blank_to_none(value)


class RecurringCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: uuid.UUID
    start_date: date
    end_date: date | None = None
    weekdays: list[int] = Field(min_length=1, max_length=7)
    start_time: time
    end_time: time
    topic: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("topic", "notes", mode="before")
    @classmethod
    def blank(cls, value: object) -> object:
        return _blank_to_none(value)

    @field_validator("weekdays")
    @classmethod
    def known_weekdays(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value) or any(day < 0 or day > 6 for day in value):
            raise ValueError("Choose each weekday once.")
        return value


class MeetLinkUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    meet_url: str | None = Field(default=None, max_length=300)

    @field_validator("meet_url", mode="before")
    @classmethod
    def blank(cls, value: object) -> object:
        return _blank_to_none(value)


class ScheduledClassItem(BaseModel):
    id: str
    batch_id: str
    batch_name: str
    batch_code: str
    class_date: date
    start_time: time
    end_time: time
    topic: str | None
    status: str
    meet_url: str | None
    meet_status: str


class ScheduledClassDetail(ScheduledClassItem):
    notes: str | None
    version: int
    cancelled_at: datetime | None


class ClassListData(BaseModel):
    items: list[ScheduledClassItem]
    total: int


class OccurrencePreview(BaseModel):
    class_date: date
    start_time: time
    end_time: time
    conflict: bool


class PreviewData(BaseModel):
    occurrences: list[OccurrencePreview]
    conflict_count: int


class UpcomingClass(BaseModel):
    id: str
    batch_id: str
    batch_name: str
    batch_code: str
    class_date: date
    start_time: time
    end_time: time
    topic: str | None
    meet_url: str | None
    meet_status: str


class TimetableSummary(BaseModel):
    today_count: int
    today: list[UpcomingClass]
    upcoming: list[UpcomingClass]


def to_class_item(item: ScheduledClass) -> ScheduledClassItem:
    return ScheduledClassItem(
        id=str(item.id),
        batch_id=str(item.batch_id),
        batch_name=item.batch.name,
        batch_code=item.batch.batch_code,
        class_date=item.class_date,
        start_time=item.start_time,
        end_time=item.end_time,
        topic=item.topic,
        status=item.status,
        meet_url=item.meet_url,
        meet_status=meet_link_status(item.meet_url),
    )


def to_class_detail(item: ScheduledClass) -> ScheduledClassDetail:
    return ScheduledClassDetail(
        id=str(item.id),
        batch_id=str(item.batch_id),
        batch_name=item.batch.name,
        batch_code=item.batch.batch_code,
        class_date=item.class_date,
        start_time=item.start_time,
        end_time=item.end_time,
        topic=item.topic,
        notes=item.notes,
        status=item.status,
        meet_url=item.meet_url,
        meet_status=meet_link_status(item.meet_url),
        version=item.version,
        cancelled_at=item.cancelled_at,
    )


def to_upcoming(item: ScheduledClass) -> UpcomingClass:
    return UpcomingClass(
        id=str(item.id),
        batch_id=str(item.batch_id),
        batch_name=item.batch.name,
        batch_code=item.batch.batch_code,
        class_date=item.class_date,
        start_time=item.start_time,
        end_time=item.end_time,
        topic=item.topic,
        meet_url=item.meet_url,
        meet_status=meet_link_status(item.meet_url),
    )
