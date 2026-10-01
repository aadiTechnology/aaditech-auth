"""Registration behavior."""

from tests.helpers import register_student


async def test_valid_registration_assigns_student(client):
    response = await register_student(client)
    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Registration successful. Please sign in."
    assert body["data"]["email"] == "student@example.com"
    assert body["data"]["roles"] == ["STUDENT"]
    assert "password" not in body["data"]
    assert "password_hash" not in response.text


async def test_duplicate_email_is_rejected(client):
    first = await register_student(client)
    assert first.status_code == 201
    second = await register_student(client, full_name="Another Person")
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


async def test_invalid_email_is_rejected(client):
    response = await register_student(client, email="not-an-email")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_weak_password_is_rejected(client):
    response = await register_student(client, password="short", extra={"confirm_password": "short"})
    assert response.status_code == 422
    codes = {item["code"] for item in response.json()["error"]["details"]}
    assert "TOO_SHORT" in codes


async def test_password_mismatch_is_rejected(client):
    response = await register_student(client, extra={"confirm_password": "OtherPass1!"})
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["code"] == "PASSWORD_MISMATCH"


async def test_client_cannot_choose_admin_role(client):
    response = await register_student(client, extra={"role": "ADMIN"})
    assert response.status_code == 201
    assert response.json()["data"]["roles"] == ["STUDENT"]


async def test_email_is_normalized(client):
    response = await register_student(client, email="  Student.Name@Example.com  ")
    assert response.status_code == 201
    assert response.json()["data"]["email"] == "student.name@example.com"
