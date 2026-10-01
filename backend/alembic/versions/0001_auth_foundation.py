"""Authentication and authorization schema.

Revision ID: 0001_auth_foundation
Revises:
Create Date: 2026-09-29
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_auth_foundation"
down_revision = None
branch_labels = None
depends_on = None

ROLE_ADMIN = "b0000000-0000-4000-8000-000000000001"
ROLE_TEACHER = "b0000000-0000-4000-8000-000000000002"
ROLE_STUDENT = "b0000000-0000-4000-8000-000000000003"

PERM_USERS_READ = "a0000000-0000-4000-8000-000000000001"
PERM_USERS_CREATE = "a0000000-0000-4000-8000-000000000002"
PERM_USERS_UPDATE = "a0000000-0000-4000-8000-000000000003"
PERM_USERS_DELETE = "a0000000-0000-4000-8000-000000000004"
PERM_ROLES_READ = "a0000000-0000-4000-8000-000000000005"
PERM_ROLES_ASSIGN = "a0000000-0000-4000-8000-000000000006"
PERM_FEATURES_READ = "a0000000-0000-4000-8000-000000000007"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("preferred_language", sa.String(length=8), server_default=sa.text("'en'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("email_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("session_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("email = lower(btrim(email))", name="email_normalized"),
        sa.CheckConstraint(
            "preferred_language IN ('en', 'mr', 'hi')",
            name="preferred_language_supported",
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.UniqueConstraint("key", name="uq_permissions_key"),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_user_roles_user_id"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE", name="fk_user_roles_role_id"),
        sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_user_roles"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])
    op.create_table(
        "role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE", name="fk_role_permissions_role_id"),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            ondelete="CASCADE",
            name="fk_role_permissions_permission_id",
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_refresh_tokens_user_id"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_password_reset_tokens_user_id",
        ),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL", name="fk_audit_logs_actor_id"),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    roles = sa.table(
        "roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(
        roles,
        [
            {
                "id": ROLE_ADMIN,
                "name": "ADMIN",
                "description": "Full access to protected application functionality.",
            },
            {
                "id": ROLE_TEACHER,
                "name": "TEACHER",
                "description": "Teaching access limited to permissions granted on this role.",
            },
            {
                "id": ROLE_STUDENT,
                "name": "STUDENT",
                "description": "Learner access limited to permissions granted on this role.",
            },
        ],
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
            {"id": PERM_USERS_READ, "key": "users.read", "description": "View user accounts and their roles."},
            {"id": PERM_USERS_CREATE, "key": "users.create", "description": "Create user accounts."},
            {"id": PERM_USERS_UPDATE, "key": "users.update", "description": "Update account status."},
            {"id": PERM_USERS_DELETE, "key": "users.delete", "description": "Delete user accounts."},
            {"id": PERM_ROLES_READ, "key": "roles.read", "description": "View roles and their permissions."},
            {"id": PERM_ROLES_ASSIGN, "key": "roles.assign", "description": "Assign roles to other users."},
            {"id": PERM_FEATURES_READ, "key": "features.read", "description": "Use the authenticated application."},
        ],
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", postgresql.UUID(as_uuid=True)),
        sa.column("permission_id", postgresql.UUID(as_uuid=True)),
    )
    admin_permissions = [
        PERM_USERS_READ,
        PERM_USERS_CREATE,
        PERM_USERS_UPDATE,
        PERM_USERS_DELETE,
        PERM_ROLES_READ,
        PERM_ROLES_ASSIGN,
        PERM_FEATURES_READ,
    ]
    op.bulk_insert(
        role_permissions,
        [{"role_id": ROLE_ADMIN, "permission_id": permission_id} for permission_id in admin_permissions]
        + [
            {"role_id": ROLE_TEACHER, "permission_id": PERM_FEATURES_READ},
            {"role_id": ROLE_STUDENT, "permission_id": PERM_FEATURES_READ},
        ],
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("password_reset_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
