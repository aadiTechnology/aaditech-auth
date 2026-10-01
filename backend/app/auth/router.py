"""Authentication HTTP routes. Handlers delegate to the auth service."""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.cookies import clear_session_cookies, ensure_csrf_cookie, set_session_cookies
from app.auth.dependencies import (
    client_ip,
    get_current_user,
    limit_forgot_password,
    limit_forgot_password_email,
    limit_login,
    limit_register,
    limit_reset_password,
)
from app.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisteredUser,
    RegisterRequest,
    ResetPasswordRequest,
    UserProfile,
)
from app.auth.service import (
    GENERIC_RESET_MESSAGE,
    authenticate,
    logout,
    refresh_session,
    register_user,
    request_password_reset,
    reset_password,
)
from app.common.responses import ApiResponse, CsrfData, PasswordPolicyData, error_responses
from app.core.database import get_db
from app.core.password_policy import current_password_policy
from app.core.security import CSRF_COOKIE, REFRESH_COOKIE
from app.email.sender import EmailSender, get_email_sender
from app.users.models import User
from app.users.schemas import to_registered_user, to_user_profile

router = APIRouter()

_CSRF_NOTE = (
    " State-changing requests must send the X-CSRF-Token header that matches the csrf_token cookie "
    "issued by GET /api/v1/auth/csrf."
)


@router.get(
    "/csrf",
    response_model=ApiResponse[CsrfData],
    summary="Issue a CSRF token",
    description=(
        "Returns the double-submit CSRF token and sets it as an HttpOnly cookie. "
        "Call this before registration, login, logout, refresh, or password reset."
    ),
)
def issue_csrf(request: Request, response: Response) -> ApiResponse[CsrfData]:
    token = ensure_csrf_cookie(response, request.cookies.get(CSRF_COOKIE))
    return ApiResponse(data=CsrfData(csrf_token=token), message="Success")


@router.get(
    "/password-policy",
    response_model=ApiResponse[PasswordPolicyData],
    summary="Read the password policy",
    description="Returns the server-side password rules used by registration and password reset.",
)
def password_policy() -> ApiResponse[PasswordPolicyData]:
    return ApiResponse(
        data=PasswordPolicyData.model_validate(current_password_policy().as_dict()),
        message="Success",
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[RegisteredUser],
    summary="Register a student account",
    description=(
        "Creates an active student account. The role is assigned by the server. "
        "Clients cannot choose Admin or Teacher during registration." + _CSRF_NOTE
    ),
    responses=error_responses(403, 409, 422, 429),
    dependencies=[Depends(limit_register)],
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[RegisteredUser]:
    user = register_user(db, payload)
    return ApiResponse(
        data=to_registered_user(user),
        message="Registration successful. Please sign in.",
    )


@router.post(
    "/login",
    response_model=ApiResponse[UserProfile],
    summary="Log in",
    description=(
        "Validates email and password, then sets short-lived access and revocable refresh cookies. "
        "Tokens are not returned in the JSON body. A future MFA challenge can be inserted before "
        "the cookies are issued." + _CSRF_NOTE
    ),
    responses=error_responses(401, 403, 422, 429),
    dependencies=[Depends(limit_login)],
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> ApiResponse[UserProfile]:
    session = authenticate(db, payload, client_ip(request))
    set_session_cookies(response, session)
    return ApiResponse(data=to_user_profile(db, session.user), message="Login successful.")


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out",
    description="Revokes the current refresh token and clears authentication cookies." + _CSRF_NOTE,
    responses=error_responses(403),
)
def logout_current(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    logout(db, request.cookies.get(REFRESH_COOKIE), client_ip(request))
    clear_session_cookies(response)
    return response


@router.post(
    "/refresh",
    response_model=ApiResponse[UserProfile],
    summary="Refresh the session",
    description=(
        "Rotates the refresh cookie. A revoked refresh token cannot be reused; reuse revokes "
        "the user's sessions." + _CSRF_NOTE
    ),
    responses=error_responses(401, 403),
)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> ApiResponse[UserProfile]:
    session = refresh_session(db, request.cookies.get(REFRESH_COOKIE))
    set_session_cookies(response, session)
    return ApiResponse(data=to_user_profile(db, session.user), message="Session refreshed.")


@router.get(
    "/me",
    response_model=ApiResponse[UserProfile],
    summary="Read the current user",
    description="Returns the authenticated user, database roles, and effective permissions.",
    responses=error_responses(401),
)
def me(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiResponse[UserProfile]:
    return ApiResponse(data=to_user_profile(db, user), message="Success")


@router.post(
    "/forgot-password",
    response_model=ApiResponse[dict[str, str]],
    summary="Request a password reset",
    description=(
        "Always returns the same message. When the account exists, a single-use hashed reset "
        "token is stored and a message is sent. The raw token is not stored or logged."
        + _CSRF_NOTE
    ),
    responses=error_responses(403, 422, 429),
    dependencies=[Depends(limit_forgot_password)],
)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
) -> ApiResponse[dict[str, str]]:
    limit_forgot_password_email(payload.email)
    request_password_reset(db, payload, email_sender, client_ip(request))
    return ApiResponse(data={}, message=GENERIC_RESET_MESSAGE)


@router.post(
    "/reset-password",
    response_model=ApiResponse[dict[str, str]],
    summary="Reset a password",
    description=(
        "Consumes a valid reset token, stores a new password hash, and revokes existing sessions."
        + _CSRF_NOTE
    ),
    responses=error_responses(400, 403, 422, 429),
    dependencies=[Depends(limit_reset_password)],
)
def reset_password_route(
    payload: ResetPasswordRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, str]]:
    reset_password(db, payload, client_ip(request))
    clear_session_cookies(response)
    return ApiResponse(data={}, message="Password has been reset. Please sign in.")
