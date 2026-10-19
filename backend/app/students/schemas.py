"""Student request and response schemas."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.students.models import Student


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


class ParentName(BaseModel):
    id: str
    full_name: str
    relationship: str | None = None


class ParentContact(BaseModel):
    id: str
    full_name: str
    relationship: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str


class ParentLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_id: uuid.UUID | None = None
    full_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=320)
    relationship: Literal["mother", "father", "guardian", "other"] | None = None

    @field_validator("full_name", "phone", "email", mode="before")
    @classmethod
    def blank(cls, value: object) -> object:
        return _blank_to_none(value)


class StudentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=200)
    status: Literal["active", "inactive"] = "active"
    date_of_birth: date | None = None
    school_name: str | None = Field(default=None, max_length=200)
    grade: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    enrollment_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    parent_link: ParentLinkCreate | None = None

    @field_validator("school_name", "grade", "address", "notes", mode="before")
    @classmethod
    def blank(cls, value: object) -> object:
        return _blank_to_none(value)


class StudentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    full_name: str | None = Field(default=None, max_length=200)
    status: Literal["active", "inactive"] | None = None
    date_of_birth: date | None = None
    school_name: str | None = Field(default=None, max_length=200)
    grade: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    enrollment_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("school_name", "grade", "address", "notes", mode="before")
    @classmethod
    def blank(cls, value: object) -> object:
        return _blank_to_none(value)


class LinkParentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_id: uuid.UUID
    relationship: Literal["mother", "father", "guardian", "other"] | None = None


class StudentListItem(BaseModel):
    id: str
    student_code: str
    full_name: str
    grade: str | None
    school_name: str | None
    status: str
    enrollment_date: date | None
    parents: list[ParentName]


class StudentDetail(BaseModel):
    id: str
    student_code: str
    full_name: str
    date_of_birth: date | None
    school_name: str | None
    grade: str | None
    address: str | None
    enrollment_date: date | None
    status: str
    notes: str | None
    version: int
    archived_at: datetime | None
    parents: list[ParentContact]


class StudentListData(BaseModel):
    items: list[StudentListItem]
    total: int
    limit: int
    offset: int


class StudentSummary(BaseModel):
    active_count: int


def _parent_names(student: Student) -> list[ParentName]:
    return [
        ParentName(
            id=str(link.parent_id),
            full_name=link.parent.full_name,
            relationship=link.relationship_name,
        )
        for link in sorted(student.links, key=lambda item: item.parent.full_name.lower())
    ]


def to_student_list_item(student: Student) -> StudentListItem:
    return StudentListItem(
        id=str(student.id),
        student_code=student.student_code,
        full_name=student.full_name,
        grade=student.grade,
        school_name=student.school_name,
        status=student.status,
        enrollment_date=student.enrollment_date,
        parents=_parent_names(student),
    )


def to_student_detail(student: Student) -> StudentDetail:
    parents = [
        ParentContact(
            id=str(link.parent_id),
            full_name=link.parent.full_name,
            relationship=link.relationship_name,
            phone=link.parent.phone,
            email=link.parent.email,
            status=link.parent.status,
        )
        for link in sorted(student.links, key=lambda item: item.parent.full_name.lower())
    ]
    return StudentDetail(
        id=str(student.id),
        student_code=student.student_code,
        full_name=student.full_name,
        date_of_birth=student.date_of_birth,
        school_name=student.school_name,
        grade=student.grade,
        address=student.address,
        enrollment_date=student.enrollment_date,
        status=student.status,
        notes=student.notes,
        version=student.version,
        archived_at=student.archived_at,
        parents=parents,
    )
