"""Server-side authorization and privilege boundaries."""

from app.cli.create_admin import main as create_admin_main

from tests.helpers import assign_role, csrf_headers, login, register_student


async def _admin(client) -> None:
    assert (await register_student(client, email="admin@example.com", full_name="Admin User")).status_code == 201
    assign_role("admin@example.com", "ADMIN")
    assert (await login(client, email="admin@example.com")).status_code == 200


async def test_student_and_teacher_cannot_list_users(client):
    assert (await register_student(client)).status_code == 201
    assert (await login(client)).status_code == 200
    student = await client.get("/api/v1/users")
    assert student.status_code == 403

    assert (await register_student(client, email="teacher@example.com", full_name="Teacher User")).status_code == 201
    assign_role("teacher@example.com", "TEACHER")
    assert (await login(client, email="teacher@example.com")).status_code == 200
    teacher = await client.get("/api/v1/users")
    assert teacher.status_code == 403


async def test_unauthenticated_user_management_is_rejected(client):
    response = await client.get("/api/v1/users")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_admin_can_list_roles_and_change_another_users_role(client):
    registered = await register_student(client)
    assert registered.status_code == 201
    user_id = registered.json()["data"]["id"]
    await _admin(client)

    users = await client.get("/api/v1/users")
    assert users.status_code == 200
    assert users.json()["data"]["total"] >= 2

    roles = await client.get("/api/v1/roles")
    assert roles.status_code == 200
    role_names = {role["name"]: [item["key"] for item in role["permissions"]] for role in roles.json()["data"]}
    assert "users.read" in role_names["ADMIN"]
    assert "users.read" not in role_names["TEACHER"]
    assert "users.read" not in role_names["STUDENT"]
    assert "features.read" in role_names["STUDENT"]

    permissions = await client.get("/api/v1/permissions")
    assert permissions.status_code == 200
    assert {item["key"] for item in permissions.json()["data"]} >= {"users.read", "roles.assign"}

    changed = await client.patch(
        f"/api/v1/users/{user_id}/role",
        json={"role": "teacher"},
        headers=await csrf_headers(client),
    )
    assert changed.status_code == 200
    assert changed.json()["data"]["roles"] == ["TEACHER"]


async def test_user_cannot_change_own_role_or_escalate(client):
    registered = await register_student(client)
    user_id = registered.json()["data"]["id"]
    assert (await login(client)).status_code == 200
    own = await client.patch(
        f"/api/v1/users/{user_id}/role",
        json={"role": "ADMIN"},
        headers=await csrf_headers(client),
    )
    assert own.status_code == 403

    await _admin(client)
    me = await client.get("/api/v1/auth/me")
    admin_id = me.json()["data"]["id"]
    self_change = await client.patch(
        f"/api/v1/users/{admin_id}/role",
        json={"role": "STUDENT"},
        headers=await csrf_headers(client),
    )
    assert self_change.status_code == 403
    assert self_change.json()["error"]["code"] == "CANNOT_MODIFY_OWN_ACCESS"


async def test_admin_can_activate_and_cannot_remove_last_admin(client):
    registered = await register_student(client)
    user_id = registered.json()["data"]["id"]
    await _admin(client)
    me = await client.get("/api/v1/auth/me")
    admin_id = me.json()["data"]["id"]

    deactivated = await client.patch(
        f"/api/v1/users/{user_id}/status",
        json={"is_active": False},
        headers=await csrf_headers(client),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["data"]["is_active"] is False

    activated = await client.patch(
        f"/api/v1/users/{user_id}/status",
        json={"is_active": True},
        headers=await csrf_headers(client),
    )
    assert activated.status_code == 200

    demotion = await client.patch(
        f"/api/v1/users/{admin_id}/role",
        json={"role": "STUDENT"},
        headers=await csrf_headers(client),
    )
    assert demotion.status_code == 403

    promoted = await client.patch(
        f"/api/v1/users/{user_id}/role",
        json={"role": "ADMIN"},
        headers=await csrf_headers(client),
    )
    assert promoted.status_code == 200

    assert (await login(client, email="student@example.com")).status_code == 200
    remove_original = await client.patch(
        f"/api/v1/users/{admin_id}/role",
        json={"role": "TEACHER"},
        headers=await csrf_headers(client),
    )
    assert remove_original.status_code == 200

    me = await client.get("/api/v1/auth/me")
    remaining_admin = me.json()["data"]["id"]
    self_deactivate = await client.patch(
        f"/api/v1/users/{remaining_admin}/status",
        json={"is_active": False},
        headers=await csrf_headers(client),
    )
    assert self_deactivate.status_code == 403
    assert self_deactivate.json()["error"]["code"] == "CANNOT_MODIFY_OWN_ACCESS"


async def test_initial_admin_command_runs_once():
    assert create_admin_main(
        ["--email", "root@example.com", "--full-name", "Root Admin", "--password", "ValidPass1!"]
    ) == 0
    assert create_admin_main(
        ["--email", "other@example.com", "--full-name", "Other Admin", "--password", "ValidPass1!"]
    ) == 1
