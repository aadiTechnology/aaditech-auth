"""Scheduled classes.

class_date, start_time, and end_time are Asia/Kolkata wall-clock values.
A class points at a batch. It does not copy the batch name or subject.
"""

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.batches.models import Batch
from app.core.database import Base


class ClassStatus:
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"


class ScheduledClass(Base):
    __tablename__ = "scheduled_classes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled', 'cancelled')",
            name="scheduled_classes_status_known",
        ),
        CheckConstraint("end_time > start_time", name="scheduled_classes_time_order"),
        CheckConstraint(
            "meet_url IS NULL OR ("
            "meet_url LIKE 'https://meet.google.com/%' "
            "AND meet_url NOT LIKE '% %' "
            "AND char_length(meet_url) <= 300"
            ")",
            name="scheduled_classes_meet_url_https",
        ),
        Index("ix_scheduled_classes_batch_date", "batch_id", "class_date"),
        Index("ix_scheduled_classes_class_date", "class_date"),
        Index(
            "uq_scheduled_classes_active_slot",
            "batch_id",
            "class_date",
            "start_time",
            unique=True,
            postgresql_where=text("status = 'scheduled'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("batches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    class_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    topic: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meet_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    batch: Mapped[Batch] = relationship()
