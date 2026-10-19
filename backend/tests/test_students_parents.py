"""Student and parent register API."""

import uuid

from tests.helpers import assign_role, csrf_headers, login, register_student

STUDENT_BODY = {
    "full_name": "Asha Kulkarni",
    "grade": "8",
    "school_name": "City High School",
    "enrollment_date": "2026-06-01",
    "status": "active",
}


async def _staff(client, *, role: str = "ADMIN", email: str = "admin@example.com"):
    assert (await register_student(client, email=email, full_name="Staff User")).status_code == 201
    assign_role(email, role)
    assert (await login(client, email=email)).status_code == 200
    return await csrf_headers(client)


async def _create_student(client, headers, **extra):
    body = {**STUDENT_BODY, **extra}
    return await client.post("/api/v1/students", json=body, headers=headers)


async def _create_parent(client, headers, **extra):
    body = {"full_name": "Meera Kulkarni", "phone": "9876543210", **extra}
    return await client.post("/api/v1/parents", json=body, headers=headers)


async def test_student_login_cannot_read_or_change_the_register(client):
    assert (await register_student(client)).status_code == 201
    assert (await login(client)).status_code == 200
    headers = await csrf_headers(client)
    assert (await client.get("/api/v1/students")).status_code == 403
    assert (await client.get("/api/v1/students/summary")).status_code == 403
    assert (await client.get("/api/v1/parents")).status_code == 403
    created = await _create_student(client, headers)
    assert created.status_code == 403


async def test_anonymous_register_requests_are_rejected(client):
    listing = await client.get("/api/v1/students")
    assert listing.status_code == 401
    assert listing.json()["error"]["code"] == "UNAUTHENTICATED"
    created = await client.post("/api/v1/parents", json={"full_name": "Nobody"})
    assert created.status_code == 403


async def test_create_view_edit_search_and_archive_student(client):
    headers = await _staff(client)
    invalid = await _create_student(client, headers, full_name=" ")
    assert invalid.status_code == 422
    assert invalid.json()["error"]["details"][0]["field"] == "full_name"

    future = await _create_student(client, headers, date_of_birth="2999-01-01")
    assert future.status_code == 422
    assert future.json()["error"]["details"][0]["field"] == "date_of_birth"

    created = await _create_student(
        client,
        headers,
        date_of_birth="2012-04-03",
        address="12 Lake Road",
        notes="Evening batch",
    )
    assert created.status_code == 201
    student = created.json()["data"]
    assert student["student_code"] == "STU-000001"
    assert student["full_name"] == "Asha Kulkarni"
    assert student["status"] == "active"
    assert student["version"] == 1
    student_id = student["id"]

    listed = await client.get("/api/v1/students")
    assert listed.status_code == 200
    item = listed.json()["data"]["items"][0]
    assert item["student_code"] == "STU-000001"
    assert "notes" not in item
    assert "address" not in item
    assert "date_of_birth" not in item

    detail = await client.get(f"/api/v1/students/{student_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["notes"] == "Evening batch"
    assert detail.json()["data"]["address"] == "12 Lake Road"

    renamed = await client.patch(
        f"/api/v1/students/{student_id}",
        json={"version": 1, "full_name": "Asha M. Kulkarni"},
        headers=headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["data"]["full_name"] == "Asha M. Kulkarni"
    assert renamed.json()["data"]["school_name"] == "City High School"
    assert renamed.json()["data"]["version"] == 2

    stale = await client.patch(
        f"/api/v1/students/{student_id}",
        json={"version": 1, "full_name": "Stale Name"},
        headers=headers,
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "STALE_UPDATE"

    by_name = await client.get("/api/v1/students", params={"q": "asha m"})
    assert by_name.json()["data"]["total"] == 1
    by_code = await client.get("/api/v1/students", params={"q": "STU-000001"})
    assert by_code.json()["data"]["total"] == 1
    other_grade = await client.get("/api/v1/students", params={"grade": "10"})
    assert other_grade.json()["data"]["total"] == 0
    inactive = await client.get("/api/v1/students", params={"status": "inactive"})
    assert inactive.json()["data"]["total"] == 0

    archived = await client.post(f"/api/v1/students/{student_id}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["data"]["status"] == "archived"
    hidden = await client.get("/api/v1/students")
    assert hidden.json()["data"]["total"] == 0
    visible = await client.get("/api/v1/students", params={"status": "archived"})
    assert visible.json()["data"]["total"] == 1
    summary = await client.get("/api/v1/students/summary")
    assert summary.json()["data"]["active_count"] == 0

    missing = await client.get(f"/api/v1/students/{uuid.uuid4()}")
    assert missing.status_code == 404


async def test_parent_links_are_many_to_many_and_not_duplicated(client):
    headers = await _staff(client)
    first = (await _create_student(client, headers, full_name="Asha Kulkarni")).json()["data"]
    second = (await _create_student(client, headers, full_name="Rohan Kulkarni", grade="6")).json()["data"]
    mother = (await _create_parent(client, headers)).json()["data"]
    father = (
        await _create_parent(
            client,
            headers,
            full_name="Suresh Kulkarni",
            phone="9876543210",
            email="suresh@example.com",
        )
    ).json()["data"]
    assert mother["phone"] == "+919876543210"
    assert father["phone"] == "+919876543210"

    edited = await client.patch(
        f"/api/v1/parents/{mother['id']}",
        json={"version": mother["version"], "email": "meera@example.com"},
        headers=headers,
    )
    assert edited.status_code == 200
    assert edited.json()["data"]["phone"] == "+919876543210"
    assert edited.json()["data"]["email"] == "meera@example.com"

    bad_phone = await _create_parent(client, headers, full_name="Nita Rao", phone="12345")
    assert bad_phone.status_code == 422
    assert bad_phone.json()["error"]["details"][0]["field"] == "phone"

    for student_id, relationship in ((first["id"], "mother"), (second["id"], "mother")):
        linked = await client.post(
            f"/api/v1/parents/{mother['id']}/students",
            json={"student_id": student_id, "relationship": relationship},
            headers=headers,
        )
        assert linked.status_code == 201
    parent_view = await client.get(f"/api/v1/parents/{mother['id']}")
    assert {item["id"] for item in parent_view.json()["data"]["students"]} == {first["id"], second["id"]}

    second_guardian = await client.post(
        f"/api/v1/students/{first['id']}/parents",
        json={"parent_id": father["id"], "relationship": "father"},
        headers=headers,
    )
    assert second_guardian.status_code == 201
    guardians = {item["id"] for item in second_guardian.json()["data"]["parents"]}
    assert guardians == {mother["id"], father["id"]}
    assert "phone" not in (await client.get("/api/v1/students")).json()["data"]["items"][0]["parents"][0]

    duplicate = await client.post(
        f"/api/v1/students/{first['id']}/parents",
        json={"parent_id": mother["id"], "relationship": "mother"},
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_LINK"

    missing_parent = await client.post(
        f"/api/v1/students/{first['id']}/parents",
        json={"parent_id": str(uuid.uuid4()), "relationship": "guardian"},
        headers=headers,
    )
    assert missing_parent.status_code == 404

    missing_student = await client.post(
        f"/api/v1/parents/{mother['id']}/students",
        json={"student_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert missing_student.status_code == 404

    removed = await client.delete(
        f"/api/v1/students/{second['id']}/parents/{mother['id']}",
        headers=headers,
    )
    assert removed.status_code == 200
    assert mother["id"] not in {item["id"] for item in removed.json()["data"]["parents"]}
    parent_after = await client.get(f"/api/v1/parents/{mother['id']}")
    assert {item["id"] for item in parent_after.json()["data"]["students"]} == {first["id"]}


async def test_archived_records_cannot_be_linked_and_rows_remain(client):
    headers = await _staff(client)
    student = (await _create_student(client, headers)).json()["data"]
    parent = (await _create_parent(client, headers)).json()["data"]
    assert (await client.post(f"/api/v1/parents/{parent['id']}/archive", headers=headers)).status_code == 200
    blocked = await client.post(
        f"/api/v1/students/{student['id']}/parents",
        json={"parent_id": parent["id"], "relationship": "guardian"},
        headers=headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "CONFLICT"
    still_there = await client.get(f"/api/v1/parents/{parent['id']}")
    assert still_there.status_code == 200
    assert still_there.json()["data"]["status"] == "archived"


async def test_teacher_can_manage_students_and_summary_counts_active_rows(client):
    headers = await _staff(client, role="TEACHER", email="teacher@example.com")
    assert (await _create_student(client, headers, full_name="Active Child")).status_code == 201
    inactive = await _create_student(client, headers, full_name="Paused Child", status="inactive")
    assert inactive.status_code == 201
    summary = await client.get("/api/v1/students/summary")
    assert summary.status_code == 200
    assert summary.json()["data"]["active_count"] == 1

    roles = await client.get("/api/v1/roles")
    assert roles.status_code == 403


async def test_create_student_can_add_and_link_a_new_parent(client):
    headers = await _staff(client)
    created = await _create_student(
        client,
        headers,
        full_name="Nisha Rao",
        parent_link={"full_name": "Lata Rao", "phone": "+91 9988776655", "relationship": "mother"},
    )
    assert created.status_code == 201
    body = created.json()["data"]
    assert body["parents"][0]["full_name"] == "Lata Rao"
    assert body["parents"][0]["phone"] == "+919988776655"
    assert body["parents"][0]["relationship"] == "mother"

    parents = await client.get("/api/v1/parents", params={"q": "Lata"})
    assert parents.json()["data"]["total"] == 1
    assert parents.json()["data"]["items"][0]["students"][0]["full_name"] == "Nisha Rao"
