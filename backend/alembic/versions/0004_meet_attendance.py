"""Meeting links and attendance.

Revision ID: 0004_meet_attendance
Revises: 0003_batches_timetable
Create Date: 2026-10-19

Adds a Meet URL on scheduled classes and an attendance row per student per class.
Existing rows are kept. A missing Meet URL stays null.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_meet_attendance"
down_revision = "0003_batches_timetable"
branch_labels = None
depends_on = None

PERM_MEET_READ = "a0000000-0000-4000-8000-000000000018"
PERM_MEET_UPDATE = "a0000000-0000-4000-8000-000000000019"
PERM_ATTENDANCE_READ = "a0000000-0000-4000-8000-00000000001a"
PERM_ATTENDANCE_UPDATE = "a0000000-0000-4000-8000-00000000001b"


def upgrade() -> None:
    op.add_column("scheduled_classes", sa.Column("meet_url", sa.String(length=300), nullable=True))
    op.create_check_constraint(
        "scheduled_classes_meet_url_https",
        "scheduled_classes",
        "meet_url IS NULL OR ("
        "meet_url LIKE 'https://meet.google.com/%' "
        "AND meet_url NOT LIKE '% %' "
        "AND char_length(meet_url) <= 300"
        ")",
    )
    op.create_table(
        "attendance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scheduled_class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('present', 'absent', 'late', 'excused')",
            name="attendance_records_status_known",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR char_length(notes) <= 500",
            name="attendance_records_notes_length",
        ),
        sa.ForeignKeyConstraint(
            ["scheduled_class_id"],
            ["scheduled_classes.id"],
            ondelete="RESTRICT",
            name="fk_attendance_records_scheduled_class_id",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            ondelete="RESTRICT",
            name="fk_attendance_records_student_id",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_attendance_records_recorded_by",
        ),
        sa.UniqueConstraint("scheduled_class_id", "student_id", name="uq_attendance_class_student"),
    )
    op.create_index("ix_attendance_records_student_id", "attendance_records", ["student_id"])

    permissions = sa.table(
        "permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("key", sa.String),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(
        permissions,
        [
            {"id": PERM_MEET_READ, "key": "meet.read", "description": "View Google Meet links."},
            {"id": PERM_MEET_UPDATE, "key": "meet.update", "description": "Add or replace Google Meet links."},
            {"id": PERM_ATTENDANCE_READ, "key": "attendance.read", "description": "View attendance."},
            {
                "id": PERM_ATTENDANCE_UPDATE,
                "key": "attendance.update",
                "description": "Record and correct attendance.",
            },
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
                'meet.read', 'meet.update', 'attendance.read', 'attendance.update'
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
                WHERE key IN ('meet.read', 'meet.update', 'attendance.read', 'attendance.update')
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE key IN ('meet.read', 'meet.update', 'attendance.read', 'attendance.update')
            """
        )
    )
    op.drop_index("ix_attendance_records_student_id", table_name="attendance_records")
    op.drop_table("attendance_records")
    op.drop_constraint("scheduled_classes_meet_url_https", "scheduled_classes", type_="check")
    op.drop_column("scheduled_classes", "meet_url")
