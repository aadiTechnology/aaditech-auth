"""Parent request and response schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.parents.models import Parent


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


class LinkedStudent(BaseModel):
    id: str
    student_code: str
    full_name: str
    grade: str | None
    relationship: str | None
    status: str


class ParentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=320)
    address: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("phone", "email", "address", "notes", mode="before")
    @classmethod
    def blank(cls, value: object) -> object:
        return _blank_to_none(value)


class ParentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    full_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=320)
    address: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)
    status: Literal["active"] | None = None

    @field_validator("phone", "email", "address", "notes", mode="before")
    @classmethod
    def blank(cls, value: object) -> object:
        return _blank_to_none(value)


class LinkStudentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: uuid.UUID
    relationship: Literal["mother", "father", "guardian", "other"] | None = None


class ParentListItem(BaseModel):
    id: str
    full_name: str
    phone: str | None
    email: str | None
    status: str
    students: list[LinkedStudent]


class ParentDetail(BaseModel):
    id: str
    full_name: str
    phone: str | None
    email: str | None
    address: str | None
    notes: str | None
    status: str
    version: int
    archived_at: datetime | None
    students: list[LinkedStudent]


class ParentListData(BaseModel):
    items: list[ParentListItem]
    total: int
    limit: int
    offset: int


def _linked_students(parent: Parent) -> list[LinkedStudent]:
    return [
        LinkedStudent(
            id=str(link.student_id),
            student_code=link.student.student_code,
            full_name=link.student.full_name,
            grade=link.student.grade,
            relationship=link.relationship_name,
            status=link.student.status,
        )
        for link in sorted(parent.links, key=lambda item: item.student.full_name.lower())
    ]


def to_parent_list_item(parent: Parent) -> ParentListItem:
    return ParentListItem(
        id=str(parent.id),
        full_name=parent.full_name,
        phone=parent.phone,
        email=parent.email,
        status=parent.status,
        students=_linked_students(parent),
    )


def to_parent_detail(parent: Parent) -> ParentDetail:
    return ParentDetail(
        id=str(parent.id),
        full_name=parent.full_name,
        phone=parent.phone,
        email=parent.email,
        address=parent.address,
        notes=parent.notes,
        status=parent.status,
        version=parent.version,
        archived_at=parent.archived_at,
        students=_linked_students(parent),
    )
