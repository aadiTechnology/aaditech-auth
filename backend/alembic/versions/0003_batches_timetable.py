"""Batches, enrollment, and timetable.

Revision ID: 0003_batches_timetable
Revises: 0002_students_parents
Create Date: 2026-10-19

Class dates and clock times are Asia/Kolkata wall-clock values.
Student enrollment is many-to-many and does not copy student columns.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_batches_timetable"
down_revision = "0002_students_parents"
branch_labels = None
depends_on = None

PERM_BATCHES_READ = "a0000000-0000-4000-8000-000000000010"
PERM_BATCHES_CREATE = "a0000000-0000-4000-8000-000000000011"
PERM_BATCHES_UPDATE = "a0000000-0000-4000-8000-000000000012"
PERM_BATCHES_ARCHIVE = "a0000000-0000-4000-8000-000000000013"
PERM_TIMETABLE_READ = "a0000000-0000-4000-8000-000000000014"
PERM_TIMETABLE_CREATE = "a0000000-0000-4000-8000-000000000015"
PERM_TIMETABLE_UPDATE = "a0000000-0000-4000-8000-000000000016"
PERM_TIMETABLE_CANCEL = "a0000000-0000-4000-8000-000000000017"


def upgrade() -> None:
    op.execute(sa.text("CREATE SEQUENCE batch_code_seq START WITH 1 INCREMENT BY 1"))
    op.create_table(
        "batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("subject", sa.String(length=100), nullable=True),
        sa.Column("grade", sa.String(length=2), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'inactive', 'archived')", name="batches_status_known"),
        sa.CheckConstraint(
            "grade IS NULL OR grade IN ('1','2','3','4','5','6','7','8','9','10','11','12')",
            name="batches_grade_known",
        ),
        sa.UniqueConstraint("batch_code", name="uq_batches_batch_code"),
    )
    op.create_index("ix_batches_name", "batches", ["name"])
    op.create_index("ix_batches_subject", "batches", ["subject"])
    op.create_index("ix_batches_grade", "batches", ["grade"])
    op.create_index("ix_batches_status", "batches", ["status"])
    op.create_table(
        "batch_students",
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.id"],
            ondelete="RESTRICT",
            name="fk_batch_students_batch_id",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            ondelete="RESTRICT",
            name="fk_batch_students_student_id",
        ),
        sa.PrimaryKeyConstraint("batch_id", "student_id", name="pk_batch_students"),
    )
    op.create_index("ix_batch_students_student_id", "batch_students", ["student_id"])
    op.create_table(
        "scheduled_classes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("topic", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('scheduled', 'cancelled')",
            name="scheduled_classes_status_known",
        ),
        sa.CheckConstraint("end_time > start_time", name="scheduled_classes_time_order"),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.id"],
            ondelete="RESTRICT",
            name="fk_scheduled_classes_batch_id",
        ),
    )
    op.create_index("ix_scheduled_classes_batch_date", "scheduled_classes", ["batch_id", "class_date"])
    op.create_index("ix_scheduled_classes_class_date", "scheduled_classes", ["class_date"])
    op.create_index("ix_scheduled_classes_status", "scheduled_classes", ["status"])
    op.create_index(
        "uq_scheduled_classes_active_slot",
        "scheduled_classes",
        ["batch_id", "class_date", "start_time"],
        unique=True,
        postgresql_where=sa.text("status = 'scheduled'"),
    )

    permissions = sa.table(
        "permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("key", sa.String),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(
        permissions,
        [
            {"id": PERM_BATCHES_READ, "key": "batches.read", "description": "View batches."},
            {"id": PERM_BATCHES_CREATE, "key": "batches.create", "description": "Create batches."},
            {
                "id": PERM_BATCHES_UPDATE,
                "key": "batches.update",
                "description": "Update batches and student assignments.",
            },
            {"id": PERM_BATCHES_ARCHIVE, "key": "batches.archive", "description": "Archive batches."},
            {"id": PERM_TIMETABLE_READ, "key": "timetable.read", "description": "View the timetable."},
            {"id": PERM_TIMETABLE_CREATE, "key": "timetable.create", "description": "Schedule classes."},
            {"id": PERM_TIMETABLE_UPDATE, "key": "timetable.update", "description": "Update scheduled classes."},
            {"id": PERM_TIMETABLE_CANCEL, "key": "timetable.cancel", "description": "Cancel scheduled classes."},
        ],
    )
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT roles.id, permissions.id
            FROM roles
            CROSS JOIN permissions
            WHERE roles.name IN ('ADMIN', 'TEACHER')
              AND permissions.key IN (
                'batches.read', 'batches.create', 'batches.update', 'batches.archive',
                'timetable.read', 'timetable.create', 'timetable.update', 'timetable.cancel'
              )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions
                WHERE key IN (
                    'batches.read', 'batches.create', 'batches.update', 'batches.archive',
                    'timetable.read', 'timetable.create', 'timetable.update', 'timetable.cancel'
                )
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE key IN (
                'batches.read', 'batches.create', 'batches.update', 'batches.archive',
                'timetable.read', 'timetable.create', 'timetable.update', 'timetable.cancel'
            )
            """
        )
    )
    op.drop_index("uq_scheduled_classes_active_slot", table_name="scheduled_classes")
    op.drop_index("ix_scheduled_classes_status", table_name="scheduled_classes")
    op.drop_index("ix_scheduled_classes_class_date", table_name="scheduled_classes")
    op.drop_index("ix_scheduled_classes_batch_date", table_name="scheduled_classes")
    op.drop_table("scheduled_classes")
    op.drop_index("ix_batch_students_student_id", table_name="batch_students")
    op.drop_table("batch_students")
    op.drop_index("ix_batches_status", table_name="batches")
    op.drop_index("ix_batches_grade", table_name="batches")
    op.drop_index("ix_batches_subject", table_name="batches")
    op.drop_index("ix_batches_name", table_name="batches")
    op.drop_table("batches")
    op.execute(sa.text("DROP SEQUENCE IF EXISTS batch_code_seq"))
