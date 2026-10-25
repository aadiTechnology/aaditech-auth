"""FastAPI application factory."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.attendance.router import router as attendance_router
from app.auth.router import router as auth_router
from app.batches.router import router as batches_router
from app.common.exceptions import AppError, ErrorCode
from app.common.responses import error_content
from app.core.config import get_settings
from app.core.csrf import CSRFMiddleware
from app.core.logging import configure_logging, log_event
from app.core.security import dummy_password_hash
from app.core.security_headers import SecurityHeadersMiddleware
from app.meet.router import router as meet_router
from app.parents.router import router as parents_router
from app.permissions.router import router as permissions_router
from app.roles.router import router as roles_router
from app.students.router import router as students_router
from app.timetable.router import router as timetable_router
from app.users.router import router as users_router

logger = logging.getLogger("app.main")


def _validation_details(exc: RequestValidationError) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []
    for error in exc.errors():
        loc = [str(part) for part in error.get("loc", []) if part not in {"body", "query", "path"}]
        field = ".".join(loc) or "request"
        error_type = str(error.get("type", "invalid"))
        code = "INVALID"
        message = "Invalid value."
        if error_type == "missing":
            code = "REQUIRED"
            message = "This field is required."
        elif error_type == "string_too_long":
            code = "TOO_LONG"
            message = "This value is too long."
        elif "date" in error_type:
            code = "INVALID_DATE"
            message = "Enter a valid date."
        elif "email" in error_type or (field == "email" and error_type != "missing"):
            code = "INVALID_EMAIL"
            message = "Enter a valid email address."
        elif field == "phone":
            code = "INVALID_PHONE"
            message = "Enter a valid phone number."
        elif field == "grade":
            code = "INVALID_GRADE"
            message = "Choose a class from 1 to 12."
        elif field == "status":
            code = "INVALID_STATUS"
            message = "Choose a valid status."
        elif field == "relationship":
            code = "INVALID_RELATIONSHIP"
            message = "Choose a valid relationship."
        elif field == "full_name":
            code = "TOO_SHORT"
            message = "Full name must be at least 2 characters."
        elif field == "preferred_language":
            code = "UNSUPPORTED_LANGUAGE"
            message = "Language must be English, Marathi, or Hindi."
        elif "time" in error_type or (field in {"start_time", "end_time"} and error_type != "missing"):
            code = "INVALID_TIME"
            message = "Enter a valid time."
        elif field == "meet_url":
            code = "INVALID_URL"
            message = "Enter a valid Google Meet link."
        elif field == "weekdays" or field.startswith("weekdays"):
            code = "INVALID_WEEKDAY"
            message = "Choose each weekday once."
        details.append({"field": field, "code": code, "message": message})
    return details


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    dummy_password_hash()
    if get_settings().app_env == "production" and get_settings().email_backend == "file":
        log_event(logger, "email_backend_not_for_production")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Online Tuition API",
        version="0.1.0",
        summary="Online Tuition API",
        description=(
            "Cookie-based authentication. Access and refresh tokens are HttpOnly cookies. "
            "Authorization uses database roles and permissions. "
            "Unsafe requests require an X-CSRF-Token header matching the csrf_token cookie. "
            "Student and parent records are class-register data and are separate from login accounts. "
            "Class dates and times use Asia/Kolkata wall-clock values. "
            "Meeting links are stored on scheduled classes. Attendance is recorded by an authorized user."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_content(exc.code, exc.message, exc.details),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_content(
                ErrorCode.VALIDATION_ERROR,
                "Validation failed.",
                _validation_details(exc),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            code, message = ErrorCode.NOT_FOUND, "Resource not found."
        elif exc.status_code == 405:
            code, message = ErrorCode.METHOD_NOT_ALLOWED, "Method not allowed."
        else:
            code, message = ErrorCode.INTERNAL_ERROR, "Request could not be processed."
        return JSONResponse(status_code=exc.status_code, content=error_content(code, message))

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        log_event(logger, "unhandled_error", error_type=type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=error_content(ErrorCode.INTERNAL_ERROR, "An unexpected error occurred."),
        )

    app.add_middleware(CSRFMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Accept", "Accept-Language"],
    )
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(roles_router, prefix="/api/v1/roles", tags=["Roles"])
    app.include_router(permissions_router, prefix="/api/v1/permissions", tags=["Permissions"])
    app.include_router(students_router, prefix="/api/v1/students", tags=["Students"])
    app.include_router(parents_router, prefix="/api/v1/parents", tags=["Parents"])
    app.include_router(batches_router, prefix="/api/v1/batches", tags=["Batches"])
    app.include_router(timetable_router, prefix="/api/v1/timetable", tags=["Timetable"])
    app.include_router(meet_router, prefix="/api/v1/meet", tags=["Google Meet"])
    app.include_router(attendance_router, prefix="/api/v1/attendance", tags=["Attendance"])
    return app


app = create_app()
