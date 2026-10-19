"""Batch enrollment and timetable API."""

import uuid
from datetime import timedelta

from app.common.time import coaching_today

from tests.helpers import assign_role, csrf_headers, login, register_student

STUDENT_BODY = {"full_name": "Asha Kulkarni", "grade": "8", "status": "active"}


async def _staff(client, *, role: str = "ADMIN", email: str = "admin@example.com"):
    assert (await register_student(client, email=email, full_name="Staff User")).status_code == 201
    assign_role(email, role)
    assert (await login(client, email=email)).status_code == 200
    return await csrf_headers(client)


async def _student(client, headers, **extra):
    response = await client.post("/api/v1/students", json={**STUDENT_BODY, **extra}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _batch(client, headers, **extra):
    body = {"name": "Evening Maths", "subject": "Maths", "grade": "8", "status": "active", **extra}
    return await client.post("/api/v1/batches", json=body, headers=headers)


def _class_body(batch_id: str, **extra):
    return {
        "batch_id": batch_id,
        "class_date": "2026-10-20",
        "start_time": "10:00:00",
        "end_time": "11:00:00",
        "topic": "Algebra",
        **extra,
    }


async def test_student_login_cannot_manage_batches_or_timetable(client):
    assert (await register_student(client)).status_code == 201
    assert (await login(client)).status_code == 200
    headers = await csrf_headers(client)
    assert (await client.get("/api/v1/batches")).status_code == 403
    assert (await client.get("/api/v1/batches/summary")).status_code == 403
    assert (await client.get("/api/v1/timetable/summary")).status_code == 403
    created = await _batch(client, headers)
    assert created.status_code == 403


async def test_anonymous_batch_and_timetable_requests_are_rejected(client):
    listing = await client.get("/api/v1/batches")
    assert listing.status_code == 401
    assert listing.json()["error"]["code"] == "UNAUTHENTICATED"
    timetable = await client.get("/api/v1/timetable", params={"from": "2026-10-19", "to": "2026-10-25"})
    assert timetable.status_code == 401
    created = await client.post("/api/v1/batches", json={"name": "Maths"})
    assert created.status_code == 403


async def test_create_view_edit_search_and_archive_batch(client):
    headers = await _staff(client)
    invalid = await _batch(client, headers, name=" ")
    assert invalid.status_code == 422
    assert invalid.json()["error"]["details"][0]["field"] == "name"

    short = await _batch(client, headers, name="A")
    assert short.status_code == 422
    assert short.json()["error"]["details"][0]["code"] == "MIN_LENGTH"

    created = await _batch(client, headers, description="Weekday group")
    assert created.status_code == 201
    batch = created.json()["data"]
    assert batch["batch_code"] == "BAT-000001"
    assert batch["name"] == "Evening Maths"
    assert batch["subject"] == "Maths"
    assert batch["status"] == "active"
    assert batch["student_count"] == 0
    assert batch["version"] == 1
    batch_id = batch["id"]

    listed = await client.get("/api/v1/batches", params={"q": "BAT-000001"})
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1
    assert listed.json()["data"]["items"][0]["name"] == "Evening Maths"
    assert "description" not in listed.json()["data"]["items"][0]

    by_subject = await client.get("/api/v1/batches", params={"subject": "maths", "grade": "8", "status": "active"})
    assert by_subject.json()["data"]["total"] == 1

    detail = await client.get(f"/api/v1/batches/{batch_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["description"] == "Weekday group"

    renamed = await client.patch(
        f"/api/v1/batches/{batch_id}",
        json={"version": 1, "name": "Morning Maths"},
        headers=headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["data"]["name"] == "Morning Maths"
    assert renamed.json()["data"]["subject"] == "Maths"
    assert renamed.json()["data"]["version"] == 2

    stale = await client.patch(
        f"/api/v1/batches/{batch_id}",
        json={"version": 1, "name": "Old name"},
        headers=headers,
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "STALE_UPDATE"

    missing = await client.get(f"/api/v1/batches/{uuid.uuid4()}")
    assert missing.status_code == 404

    archived = await client.post(f"/api/v1/batches/{batch_id}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["data"]["status"] == "archived"
    current = await client.get("/api/v1/batches")
    assert current.json()["data"]["total"] == 0
    archived_list = await client.get("/api/v1/batches", params={"status": "archived"})
    assert archived_list.json()["data"]["total"] == 1

    blocked = await client.patch(
        f"/api/v1/batches/{batch_id}",
        json={"version": archived.json()["data"]["version"], "name": "Still archived"},
        headers=headers,
    )
    assert blocked.status_code == 409


async def test_assign_multiple_students_without_duplicates_or_data_loss(client):
    headers = await _staff(client)
    first = await _student(client, headers, full_name="Asha Kulkarni")
    second = await _student(client, headers, full_name="Rahul Patil")
    created = await _batch(client, headers, student_ids=[first["id"]])
    assert created.status_code == 201
    batch_id = created.json()["data"]["id"]
    assert created.json()["data"]["student_count"] == 1
    assert created.json()["data"]["students"][0]["student_code"] == "STU-000001"
    assert created.json()["data"]["students"][0]["full_name"] == "Asha Kulkarni"

    other = await _batch(client, headers, name="Science", subject="Science", student_ids=[first["id"]])
    assert other.status_code == 201
    assert other.json()["data"]["student_count"] == 1

    added = await client.post(
        f"/api/v1/batches/{batch_id}/students",
        json={"student_ids": [second["id"]]},
        headers=headers,
    )
    assert added.status_code == 201
    names = sorted(student["full_name"] for student in added.json()["data"]["students"])
    assert names == ["Asha Kulkarni", "Rahul Patil"]
    assert added.json()["data"]["student_count"] == 2

    duplicate = await client.post(
        f"/api/v1/batches/{batch_id}/students",
        json={"student_ids": [second["id"]]},
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_ASSIGNMENT"
    listed = await client.get(f"/api/v1/batches/{batch_id}")
    assert listed.json()["data"]["student_count"] == 2

    missing_student = await client.post(
        f"/api/v1/batches/{batch_id}/students",
        json={"student_ids": [str(uuid.uuid4())]},
        headers=headers,
    )
    assert missing_student.status_code == 404

    membership = await client.get("/api/v1/batches", params={"student_id": first["id"], "status": "all"})
    assert membership.json()["data"]["total"] == 2

    removed = await client.delete(f"/api/v1/batches/{batch_id}/students/{second['id']}", headers=headers)
    assert removed.status_code == 200
    assert removed.json()["data"]["student_count"] == 1
    student_still_there = await client.get(f"/api/v1/students/{second['id']}")
    assert student_still_there.status_code == 200
    assert student_still_there.json()["data"]["full_name"] == "Rahul Patil"

    absent = await client.delete(f"/api/v1/batches/{batch_id}/students/{second['id']}", headers=headers)
    assert absent.status_code == 404


async def test_schedule_conflicts_edits_and_cancellation(client):
    headers = await _staff(client)
    batch = (await _batch(client, headers)).json()["data"]
    other = (await _batch(client, headers, name="Science", subject="Science")).json()["data"]
    batch_id = batch["id"]

    invalid = await client.post(
        "/api/v1/timetable",
        json=_class_body(batch_id, start_time="11:00:00", end_time="11:00:00"),
        headers=headers,
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["details"][0]["code"] == "END_BEFORE_START"

    backwards = await client.post(
        "/api/v1/timetable",
        json=_class_body(batch_id, start_time="12:00:00", end_time="11:00:00"),
        headers=headers,
    )
    assert backwards.status_code == 422

    created = await client.post("/api/v1/timetable", json=_class_body(batch_id), headers=headers)
    assert created.status_code == 201
    scheduled = created.json()["data"]
    assert scheduled["batch_name"] == "Evening Maths"
    assert scheduled["topic"] == "Algebra"
    assert scheduled["status"] == "scheduled"
    class_id = scheduled["id"]

    same_time_other_batch = await client.post(
        "/api/v1/timetable",
        json=_class_body(other["id"]),
        headers=headers,
    )
    assert same_time_other_batch.status_code == 201

    overlap = await client.post(
        "/api/v1/timetable",
        json=_class_body(batch_id, start_time="10:30:00", end_time="11:30:00", topic="Overlap"),
        headers=headers,
    )
    assert overlap.status_code == 409
    assert overlap.json()["error"]["code"] == "SCHEDULE_CONFLICT"

    consecutive = await client.post(
        "/api/v1/timetable",
        json=_class_body(batch_id, start_time="11:00:00", end_time="12:00:00", topic="Next"),
        headers=headers,
    )
    assert consecutive.status_code == 201
    second_id = consecutive.json()["data"]["id"]

    week = await client.get(
        "/api/v1/timetable",
        params={"from": "2026-10-19", "to": "2026-10-25", "batch_id": batch_id},
    )
    assert week.status_code == 200
    assert week.json()["data"]["total"] == 2
    assert [item["start_time"] for item in week.json()["data"]["items"]] == ["10:00:00", "11:00:00"]

    outside = await client.get(
        "/api/v1/timetable",
        params={"from": "2026-10-26", "to": "2026-11-01", "batch_id": batch_id},
    )
    assert outside.json()["data"]["total"] == 0

    moved = await client.patch(
        f"/api/v1/timetable/{second_id}",
        json={"version": 1, "start_time": "10:15:00", "end_time": "10:45:00"},
        headers=headers,
    )
    assert moved.status_code == 409

    shifted = await client.patch(
        f"/api/v1/timetable/{second_id}",
        json={"version": 1, "start_time": "12:00:00", "end_time": "13:00:00", "topic": "Geometry"},
        headers=headers,
    )
    assert shifted.status_code == 200
    assert shifted.json()["data"]["topic"] == "Geometry"
    assert shifted.json()["data"]["class_date"] == "2026-10-20"
    assert shifted.json()["data"]["version"] == 2

    cancelled = await client.post(f"/api/v1/timetable/{class_id}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "cancelled"
    active = await client.get(
        "/api/v1/timetable",
        params={"from": "2026-10-19", "to": "2026-10-25", "batch_id": batch_id},
    )
    assert active.json()["data"]["total"] == 1
    with_cancelled = await client.get(
        "/api/v1/timetable",
        params={"from": "2026-10-19", "to": "2026-10-25", "batch_id": batch_id, "include_cancelled": True},
    )
    assert with_cancelled.json()["data"]["total"] == 2

    reused = await client.post("/api/v1/timetable", json=_class_body(batch_id, topic="Replacement"), headers=headers)
    assert reused.status_code == 201

    inactive = await client.patch(
        f"/api/v1/batches/{batch_id}",
        json={"version": batch["version"], "status": "inactive"},
        headers=headers,
    )
    assert inactive.status_code == 200
    blocked = await client.post(
        "/api/v1/timetable",
        json=_class_body(batch_id, class_date="2026-10-21"),
        headers=headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "NOT_ACTIVE"


async def test_recurring_preview_and_create_are_explicit(client):
    headers = await _staff(client)
    batch_id = (await _batch(client, headers)).json()["data"]["id"]
    body = {
        "batch_id": batch_id,
        "start_date": "2026-10-19",
        "end_date": "2026-11-02",
        "weekdays": [0],
        "start_time": "17:00:00",
        "end_time": "18:00:00",
        "topic": "Weekly revision",
    }
    preview = await client.post("/api/v1/timetable/preview", json=body, headers=headers)
    assert preview.status_code == 200
    dates = [item["class_date"] for item in preview.json()["data"]["occurrences"]]
    assert dates == ["2026-10-19", "2026-10-26", "2026-11-02"]
    assert preview.json()["data"]["conflict_count"] == 0

    created = await client.post("/api/v1/timetable/recurring", json=body, headers=headers)
    assert created.status_code == 201
    assert created.json()["data"]["total"] == 3

    again = await client.post("/api/v1/timetable/recurring", json=body, headers=headers)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "SCHEDULE_CONFLICT"

    duplicate_days = await client.post(
        "/api/v1/timetable/preview",
        json={**body, "weekdays": [0, 0], "end_date": "2026-12-01"},
        headers=headers,
    )
    assert duplicate_days.status_code == 422

    default_window = await client.post(
        "/api/v1/timetable/preview",
        json={
            "batch_id": batch_id,
            "start_date": "2026-10-21",
            "weekdays": [2],
            "start_time": "09:00:00",
            "end_time": "10:00:00",
        },
        headers=headers,
    )
    assert default_window.status_code == 200
    assert len(default_window.json()["data"]["occurrences"]) == 8


async def test_archive_keeps_classes_and_dashboard_uses_live_counts(client):
    headers = await _staff(client)
    assert (await client.get("/api/v1/batches/summary")).json()["data"]["active_count"] == 0
    batch = (await _batch(client, headers)).json()["data"]
    await _batch(client, headers, name="Paused", status="inactive")
    assert (await client.get("/api/v1/batches/summary")).json()["data"]["active_count"] == 1

    today = coaching_today().isoformat()
    tomorrow = (coaching_today() + timedelta(days=1)).isoformat()
    created = await client.post(
        "/api/v1/timetable",
        json=_class_body(batch["id"], class_date=today, start_time="18:00:00", end_time="19:00:00"),
        headers=headers,
    )
    assert created.status_code == 201
    class_id = created.json()["data"]["id"]
    await client.post(
        "/api/v1/timetable",
        json=_class_body(batch["id"], class_date=tomorrow, start_time="18:00:00", end_time="19:00:00"),
        headers=headers,
    )
    summary = await client.get("/api/v1/timetable/summary")
    assert summary.status_code == 200
    assert summary.json()["data"]["today_count"] == 1
    assert len(summary.json()["data"]["upcoming"]) == 2
    assert summary.json()["data"]["upcoming"][0]["class_date"] == today

    archived = await client.post(f"/api/v1/batches/{batch['id']}/archive", headers=headers)
    assert archived.status_code == 200
    assert (await client.get("/api/v1/batches/summary")).json()["data"]["active_count"] == 0
    kept = await client.get(f"/api/v1/timetable/{class_id}")
    assert kept.status_code == 200
    assert kept.json()["data"]["status"] == "scheduled"
    students = await client.get("/api/v1/students")
    assert students.status_code == 200


async def test_teacher_can_manage_batches_and_timetable(client):
    headers = await _staff(client, role="TEACHER", email="teacher@example.com")
    created = await _batch(client, headers, name="Teacher batch")
    assert created.status_code == 201
    scheduled = await client.post(
        "/api/v1/timetable",
        json=_class_body(created.json()["data"]["id"]),
        headers=headers,
    )
    assert scheduled.status_code == 201
