"""Student and parent register.

Revision ID: 0002_students_parents
Revises: 0001_auth_foundation
Create Date: 2026-10-19
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_students_parents"
down_revision = "0001_auth_foundation"
branch_labels = None
depends_on = None

PERM_STUDENTS_READ = "a0000000-0000-4000-8000-000000000008"
PERM_STUDENTS_CREATE = "a0000000-0000-4000-8000-000000000009"
PERM_STUDENTS_UPDATE = "a0000000-0000-4000-8000-00000000000a"
PERM_STUDENTS_ARCHIVE = "a0000000-0000-4000-8000-00000000000b"
PERM_PARENTS_READ = "a0000000-0000-4000-8000-00000000000c"
PERM_PARENTS_CREATE = "a0000000-0000-4000-8000-00000000000d"
PERM_PARENTS_UPDATE = "a0000000-0000-4000-8000-00000000000e"
PERM_PARENTS_ARCHIVE = "a0000000-0000-4000-8000-00000000000f"


def upgrade() -> None:
    op.execute(sa.text("CREATE SEQUENCE student_code_seq START WITH 1 INCREMENT BY 1"))
    op.create_table(
        "students",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_code", sa.String(length=20), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("school_name", sa.String(length=200), nullable=True),
        sa.Column("grade", sa.String(length=2), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("enrollment_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'inactive', 'archived')", name="students_status_known"),
        sa.CheckConstraint(
            "grade IS NULL OR grade IN ('1','2','3','4','5','6','7','8','9','10','11','12')",
            name="students_grade_known",
        ),
        sa.UniqueConstraint("student_code", name="uq_students_student_code"),
    )
    op.create_index("ix_students_full_name", "students", ["full_name"])
    op.create_index("ix_students_grade", "students", ["grade"])
    op.create_index("ix_students_status", "students", ["status"])
    op.create_table(
        "parents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'archived')", name="parents_status_known"),
    )
    op.create_index("ix_parents_full_name", "parents", ["full_name"])
    op.create_index("ix_parents_status", "parents", ["status"])
    op.create_table(
        "student_parents",
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "relationship IS NULL OR relationship IN ('mother', 'father', 'guardian', 'other')",
            name="student_parents_relationship_known",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            ondelete="RESTRICT",
            name="fk_student_parents_student_id",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["parents.id"],
            ondelete="RESTRICT",
            name="fk_student_parents_parent_id",
        ),
        sa.PrimaryKeyConstraint("student_id", "parent_id", name="pk_student_parents"),
    )
    op.create_index("ix_student_parents_parent_id", "student_parents", ["parent_id"])

    permissions = sa.table(
        "permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("key", sa.String),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(
        permissions,
        [
            {
                "id": PERM_STUDENTS_READ,
                "key": "students.read",
                "description": "View student records.",
            },
            {
                "id": PERM_STUDENTS_CREATE,
                "key": "students.create",
                "description": "Create student records.",
            },
            {
                "id": PERM_STUDENTS_UPDATE,
                "key": "students.update",
                "description": "Update student records and guardian links.",
            },
            {
                "id": PERM_STUDENTS_ARCHIVE,
                "key": "students.archive",
                "description": "Archive student records.",
            },
            {
                "id": PERM_PARENTS_READ,
                "key": "parents.read",
                "description": "View parent and guardian records.",
            },
            {
                "id": PERM_PARENTS_CREATE,
                "key": "parents.create",
                "description": "Create parent and guardian records.",
            },
            {
                "id": PERM_PARENTS_UPDATE,
                "key": "parents.update",
                "description": "Update parent records and student links.",
            },
            {
                "id": PERM_PARENTS_ARCHIVE,
                "key": "parents.archive",
                "description": "Archive parent and guardian records.",
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
                'students.read', 'students.create', 'students.update', 'students.archive',
                'parents.read', 'parents.create', 'parents.update', 'parents.archive'
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
                    'students.read', 'students.create', 'students.update', 'students.archive',
                    'parents.read', 'parents.create', 'parents.update', 'parents.archive'
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
                'students.read', 'students.create', 'students.update', 'students.archive',
                'parents.read', 'parents.create', 'parents.update', 'parents.archive'
            )
            """
        )
    )
    op.drop_index("ix_student_parents_parent_id", table_name="student_parents")
    op.drop_table("student_parents")
    op.drop_index("ix_parents_status", table_name="parents")
    op.drop_index("ix_parents_full_name", table_name="parents")
    op.drop_table("parents")
    op.drop_index("ix_students_status", table_name="students")
    op.drop_index("ix_students_grade", table_name="students")
    op.drop_index("ix_students_full_name", table_name="students")
    op.drop_table("students")
    op.execute(sa.text("DROP SEQUENCE IF EXISTS student_code_seq"))
