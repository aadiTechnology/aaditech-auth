"""Student register and student-parent links.

A student row is a coaching-class record. It is not a login account.
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base

if TYPE_CHECKING:
    from app.parents.models import Parent


class StudentStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("student_code", name="uq_students_student_code"),
        CheckConstraint(
            "status IN ('active', 'inactive', 'archived')",
            name="students_status_known",
        ),
        CheckConstraint(
            "grade IS NULL OR grade IN ('1','2','3','4','5','6','7','8','9','10','11','12')",
            name="students_grade_known",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_code: Mapped[str] = mapped_column(String(20), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    school_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    enrollment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    links: Mapped[list["StudentParent"]] = relationship(back_populates="student")


class StudentParent(Base):
    """One guardian contact for one student. The same parent can appear on many students."""

    __tablename__ = "student_parents"
    __table_args__ = (
        CheckConstraint(
            "relationship IS NULL OR relationship IN ('mother', 'father', 'guardian', 'other')",
            name="student_parents_relationship_known",
        ),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    parent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("parents.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    relationship_name: Mapped[str | None] = mapped_column("relationship", String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    student: Mapped[Student] = relationship(back_populates="links")
    parent: Mapped["Parent"] = relationship(back_populates="links")
