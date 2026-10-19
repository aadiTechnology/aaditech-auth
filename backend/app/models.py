"""Import all models so metadata and Alembic see every table."""

from app.audit.models import AuditLog
from app.auth.models import PasswordResetToken, RefreshToken
from app.batches.models import Batch, BatchStudent
from app.parents.models import Parent
from app.permissions.models import Permission, RolePermission
from app.roles.models import Role, UserRole
from app.students.models import Student, StudentParent
from app.timetable.models import ScheduledClass
from app.users.models import User

__all__ = [
    "AuditLog",
    "Batch",
    "BatchStudent",
    "Parent",
    "PasswordResetToken",
    "Permission",
    "RefreshToken",
    "Role",
    "RolePermission",
    "ScheduledClass",
    "Student",
    "StudentParent",
    "User",
    "UserRole",
]
