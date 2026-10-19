"""Shared field checks for class-register records."""

import re
from datetime import date, timedelta

from email_validator import EmailNotValidError, validate_email

from app.common.exceptions import AppError, ErrorCode

GRADES = {str(number) for number in range(1, 13)}
RELATIONSHIPS = {"mother", "father", "guardian", "other"}
_PHONE = re.compile(r"^(?:\+91|91|0)?([6-9]\d{9})$")


def raise_if_errors(errors: list[dict[str, str]]) -> None:
    if errors:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Validation failed.", 422, details=errors)


def add_error(errors: list[dict[str, str]], field: str, code: str, message: str) -> None:
    errors.append({"field": field, "code": code, "message": message})


def clean_name(value: str | None, errors: list[dict[str, str]], field: str = "full_name") -> str | None:
    if value is None or not str(value).strip():
        add_error(errors, field, "REQUIRED", "Full name is required.")
        return None
    cleaned = " ".join(str(value).split())
    if len(cleaned) < 2:
        add_error(errors, field, "NAME_TOO_SHORT", "Full name must be at least 2 characters.")
        return None
    if len(cleaned) > 200:
        add_error(errors, field, "TOO_LONG", "Full name must be at most 200 characters.")
        return None
    return cleaned


def clean_multiline(
    value: str | None,
    errors: list[dict[str, str]],
    field: str,
    max_length: int,
) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        add_error(errors, field, "TOO_LONG", "This value is too long.")
        return None
    return cleaned


def clean_single_line(
    value: str | None,
    errors: list[dict[str, str]],
    field: str,
    max_length: int,
) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(str(value).split())
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        add_error(errors, field, "TOO_LONG", "This value is too long.")
        return None
    return cleaned


def clean_grade(value: str | None, errors: list[dict[str, str]]) -> str | None:
    if value is None or not str(value).strip():
        return None
    grade = str(value).strip()
    if grade not in GRADES:
        add_error(errors, "grade", "INVALID_GRADE", "Choose a class from 1 to 12.")
        return None
    return grade


def clean_date_of_birth(value: date | None, errors: list[dict[str, str]]) -> date | None:
    if value is None:
        return None
    today = date.today()
    if value > today or value < date(1900, 1, 1):
        add_error(errors, "date_of_birth", "INVALID_DATE", "Enter a valid date of birth.")
        return None
    return value


def clean_enrollment_date(value: date | None, errors: list[dict[str, str]]) -> date | None:
    if value is None:
        return None
    latest = date.today() + timedelta(days=366)
    if value < date(1990, 1, 1) or value > latest:
        add_error(errors, "enrollment_date", "INVALID_DATE", "Enter a valid enrollment date.")
        return None
    return value


def clean_phone(value: str | None, errors: list[dict[str, str]], field: str = "phone") -> str | None:
    if value is None or not str(value).strip():
        return None
    compact = re.sub(r"[\s\-()]", "", str(value).strip())
    match = _PHONE.fullmatch(compact)
    if match is None:
        add_error(errors, field, "INVALID_PHONE", "Enter a valid 10-digit mobile number.")
        return None
    return f"+91{match.group(1)}"


def clean_email(value: str | None, errors: list[dict[str, str]], field: str = "email") -> str | None:
    if value is None or not str(value).strip():
        return None
    try:
        normalized = validate_email(str(value).strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        add_error(errors, field, "INVALID_EMAIL", "Enter a valid email address.")
        return None
    return normalized


def clean_relationship(
    value: str | None,
    errors: list[dict[str, str]],
    field: str = "relationship",
) -> str | None:
    if value is None or not str(value).strip():
        return None
    relationship = str(value).strip().lower()
    if relationship not in RELATIONSHIPS:
        add_error(errors, field, "INVALID_RELATIONSHIP", "Choose a valid relationship.")
        return None
    return relationship


def like_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
