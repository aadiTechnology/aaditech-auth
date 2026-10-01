"""Consistent success and error response bodies."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str
    code: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class MessageData(BaseModel):
    """Empty object used when an endpoint has no resource payload."""


class ApiResponse[T](BaseModel):
    data: T
    message: str


def success_body(data: Any, message: str = "Success") -> dict[str, Any]:
    return {"data": data, "message": message}


def error_content(
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message}
    if details:
        body["details"] = details
    return {"error": body}


HTTP_ERROR_DESCRIPTIONS: dict[int, str] = {
    400: "The request could not be processed.",
    401: "Authentication is required or the session is no longer valid.",
    403: "The authenticated user does not have permission to perform this action.",
    404: "The resource does not exist.",
    409: "The request conflicts with the current state of the resource.",
    422: "The request failed validation.",
    429: "Too many requests.",
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    return {
        code: {"model": ErrorResponse, "description": HTTP_ERROR_DESCRIPTIONS[code]}
        for code in status_codes
    }


class PasswordPolicyData(BaseModel):
    min_length: int
    require_uppercase: bool
    require_lowercase: bool
    require_number: bool
    require_special: bool
    special_pattern: str = Field(description="Regular expression a special character must match.")


class CsrfData(BaseModel):
    csrf_token: str
