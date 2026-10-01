"""Double-submit CSRF protection for cookie-authenticated requests."""

import secrets

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.common.exceptions import ErrorCode
from app.common.responses import error_content
from app.core.security import CSRF_COOKIE, CSRF_HEADER

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def tokens_match(expected: str, provided: str) -> bool:
    if len(expected) != len(provided):
        return False
    return secrets.compare_digest(expected, provided)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in SAFE_METHODS:
            return await call_next(request)
        cookie_token = request.cookies.get(CSRF_COOKIE, "")
        header_token = request.headers.get(CSRF_HEADER, "")
        if not cookie_token or not header_token or not tokens_match(cookie_token, header_token):
            return JSONResponse(
                status_code=403,
                content=error_content(
                    ErrorCode.CSRF_FAILED,
                    "The request could not be verified. Refresh the page and try again.",
                ),
            )
        return await call_next(request)
