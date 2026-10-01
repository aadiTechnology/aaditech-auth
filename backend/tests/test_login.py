"""Login, logout, current user, and refresh."""

import logging

from app.main import app
from httpx import ASGITransport, AsyncClient

from tests.helpers import VALID_PASSWORD, login, register_student, set_active


async def test_login_success_sets_cookies_and_omits_secrets(client, caplog):
    assert (await register_student(client)).status_code == 201
    with caplog.at_level(logging.INFO):
        response = await login(client, remember_me=True)
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["email"] == "student@example.com"
    assert body["roles"] == ["STUDENT"]
    assert "features.read" in body["permissions"]
    assert "password_hash" not in response.text
    assert "access_token" not in response.json()["data"]
    assert "refresh_token" not in response.json()["data"]
    assert client.cookies.get("access_token")
    assert client.cookies.get("refresh_token")
    assert VALID_PASSWORD not in caplog.text


async def test_invalid_password_and_unknown_user_match(client):
    assert (await register_student(client)).status_code == 201
    wrong = await login(client, password="WrongPass1!")
    missing = await login(client, email="missing@example.com")
    assert wrong.status_code == 401
    assert missing.status_code == 401
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert missing.json()["error"] == wrong.json()["error"]


async def test_inactive_user_cannot_login(client):
    assert (await register_student(client)).status_code == 201
    set_active("student@example.com", False)
    response = await login(client)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_INACTIVE"


async def test_me_requires_authentication_and_returns_profile(client):
    anonymous = await client.get("/api/v1/auth/me")
    assert anonymous.status_code == 401
    assert (await register_student(client)).status_code == 201
    assert (await login(client)).status_code == 200
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["full_name"] == "Student User"


async def test_logout_revokes_the_session(client):
    assert (await register_student(client)).status_code == 201
    assert (await login(client)).status_code == 200
    headers = {"X-CSRF-Token": client.cookies.get("csrf_token")}
    logout = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 401


async def test_refresh_rotates_and_reuse_revokes_sessions(client):
    assert (await register_student(client)).status_code == 201
    assert (await login(client)).status_code == 200
    old_refresh = client.cookies.get("refresh_token")
    csrf = client.cookies.get("csrf_token")
    refreshed = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf})
    assert refreshed.status_code == 200
    new_refresh = client.cookies.get("refresh_token")
    assert new_refresh and new_refresh != old_refresh

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as attacker:
        reused = await attacker.post(
            "/api/v1/auth/refresh",
            headers={"X-CSRF-Token": csrf},
            cookies={"csrf_token": csrf, "refresh_token": old_refresh},
        )
        assert reused.status_code == 401

    stolen_followup = await client.post(
        "/api/v1/auth/refresh",
        headers={"X-CSRF-Token": csrf},
    )
    assert stolen_followup.status_code == 401


async def test_missing_csrf_token_is_rejected(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.com", "password": VALID_PASSWORD},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"
