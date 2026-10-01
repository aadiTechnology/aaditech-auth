"""Application error types and stable error codes."""


class ErrorCode:
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_OR_EXPIRED_TOKEN = "INVALID_OR_EXPIRED_TOKEN"
    RATE_LIMITED = "RATE_LIMITED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    CANNOT_MODIFY_OWN_ACCESS = "CANNOT_MODIFY_OWN_ACCESS"
    LAST_ADMIN = "LAST_ADMIN"
    CSRF_FAILED = "CSRF_VALIDATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"


class AppError(Exception):
    """Expected application failure with a client-safe message."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        details: list[dict[str, str]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.headers = headers or {}
