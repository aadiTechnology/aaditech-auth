"""Password reset tokens are single-use, expiring, and session-revoking."""

import logging

from app.email.sender import get_memory_sender
from app.main import app
from httpx import ASGITransport, AsyncClient

from tests.helpers import (
    VALID_PASSWORD,
    csrf_headers,
    expire_reset_tokens,
    latest_reset_token,
    login,
    register_student,
)


async def _request_reset(client: AsyncClient, email: str = "student@example.com"):
    return await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
        headers=await csrf_headers(client),
    )


async def _reset(client: AsyncClient, token: str, password: str = "NewValid1!"):
    return await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": password, "confirm_password": password},
        headers=await csrf_headers(client),
    )


async def test_unknown_email_gets_generic_response(client):
    response = await _request_reset(client, "nobody@example.com")
    assert response.status_code == 200
    assert response.json()["message"].startswith("If an account exists")
    assert get_memory_sender().messages == []


async def test_valid_reset_changes_password_and_revokes_sessions(client, caplog):
    assert (await register_student(client)).status_code == 201
    assert (await login(client)).status_code == 200
    old_access = client.cookies.get("access_token")
    old_refresh = client.cookies.get("refresh_token")
    csrf = client.cookies.get("csrf_token")

    with caplog.at_level(logging.INFO):
        requested = await _request_reset(client)
    assert requested.status_code == 200
    token = latest_reset_token()
    assert token not in caplog.text

    reset = await _reset(client, token)
    assert reset.status_code == 200

    old_password = await login(client, password=VALID_PASSWORD)
    assert old_password.status_code == 401
    new_password = await login(client, password="NewValid1!")
    assert new_password.status_code == 200

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as old_session:
        me = await old_session.get("/api/v1/auth/me", cookies={"access_token": old_access})
        assert me.status_code == 401
        refresh = await old_session.post(
            "/api/v1/auth/refresh",
            headers={"X-CSRF-Token": csrf},
            cookies={"csrf_token": csrf, "refresh_token": old_refresh},
        )
        assert refresh.status_code == 401


async def test_invalid_expired_and_reused_tokens_are_rejected(client):
    assert (await register_student(client)).status_code == 201
    invalid = await _reset(client, "this-token-does-not-exist-anywhere")
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "INVALID_OR_EXPIRED_TOKEN"

    assert (await _request_reset(client)).status_code == 200
    expire_reset_tokens("student@example.com")
    expired = await _reset(client, latest_reset_token())
    assert expired.status_code == 400
    assert expired.json()["error"]["message"] == invalid.json()["error"]["message"]

    assert (await _request_reset(client)).status_code == 200
    token = latest_reset_token()
    assert (await _reset(client, token, "Another1!")).status_code == 200
    reused = await _reset(client, token, "Another2!")
    assert reused.status_code == 400
    assert reused.json()["error"]["code"] == "INVALID_OR_EXPIRED_TOKEN"
