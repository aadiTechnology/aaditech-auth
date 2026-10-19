"""Batches and student enrollment.

A student may belong to more than one batch. The link stores ids only.
Student details stay on the students table.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base
from app.students.models import Student


class BatchStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class Batch(Base):
    __tablename__ = "batches"
    __table_args__ = (
        UniqueConstraint("batch_code", name="uq_batches_batch_code"),
        CheckConstraint(
            "status IN ('active', 'inactive', 'archived')",
            name="batches_status_known",
        ),
        CheckConstraint(
            "grade IS NULL OR grade IN ('1','2','3','4','5','6','7','8','9','10','11','12')",
            name="batches_grade_known",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    subject: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    grade: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    enrollments: Mapped[list["BatchStudent"]] = relationship(back_populates="batch")


class BatchStudent(Base):
    """One student in one batch. Removing the row does not delete the student."""

    __tablename__ = "batch_students"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("batches.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    batch: Mapped[Batch] = relationship(back_populates="enrollments")
    student: Mapped[Student] = relationship()
