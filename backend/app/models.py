"""Import all models so metadata and Alembic see every table."""

from app.audit.models import AuditLog
from app.auth.models import PasswordResetToken, RefreshToken
from app.permissions.models import Permission, RolePermission
from app.roles.models import Role, UserRole
from app.users.models import User

__all__ = [
    "AuditLog",
    "PasswordResetToken",
    "Permission",
    "RefreshToken",
    "Role",
    "RolePermission",
    "User",
    "UserRole",
]
