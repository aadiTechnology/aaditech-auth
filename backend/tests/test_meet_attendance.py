"""Google Meet links and attendance."""

import uuid

from app.attendance.service import attendance_percentage
from app.common.time import coaching_today
from app.meet.urls import MeetUrlError, normalize_meet_url

from tests.helpers import assign_role, csrf_headers, login, register_student

VALID_MEET = "https://meet.google.com/abc-defg-hij"
LOOKUP_MEET = "https://meet.google.com/lookup/abcdefghij"


def test_meet_url_accepts_meeting_codes_and_rejects_other_destinations():
    assert normalize_meet_url(f"  {VALID_MEET}/?authuser=0 ") == f"{VALID_MEET}?authuser=0"
    assert normalize_meet_url(LOOKUP_MEET) == LOOKUP_MEET
    assert attendance_percentage(1, 3) == 33.3
    assert attendance_percentage(1, 0) is None
    for value in (
        "http://meet.google.com/abc-defg-hij",
        "https://evil.example/abc-defg-hij",
        "https://meet.google.com.evil.example/abc-defg-hij",
        "javascript:https://meet.google.com/abc-defg-hij",
        "https://meet.google.com/new",
        "https://user:pass@meet.google.com/abc-defg-hij",
        "https://meet.google.com/abc-defg-hij?redirect=https://evil.example",
    ):
        try:
            normalize_meet_url(value)
        except MeetUrlError:
            continue
        raise AssertionError(value)


async def _staff(client, *, role: str = "ADMIN", email: str = "admin@example.com"):
    assert (await register_student(client, email=email, full_name="Staff User")).status_code == 201
    assign_role(email, role)
    assert (await login(client, email=email)).status_code == 200
    return await csrf_headers(client)


async def _student_record(client, headers, **extra):
    response = await client.post(
        "/api/v1/students",
        json={"full_name": "Asha Kulkarni", "grade": "8", "status": "active", **extra},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _batch(client, headers, **extra):
    response = await client.post(
        "/api/v1/batches",
        json={"name": "Evening Maths", "subject": "Maths", "grade": "8", "status": "active", **extra},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def _scheduled(client, headers, batch_id: str, **extra):
    body = {
        "batch_id": batch_id,
        "class_date": "2026-10-20",
        "start_time": "10:00:00",
        "end_time": "11:00:00",
        "topic": "Algebra",
        **extra,
    }
    response = await client.post("/api/v1/timetable", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def test_anonymous_and_student_cannot_manage_meetings_or_attendance(client):
    assert (await client.get("/api/v1/meet/upcoming")).status_code == 401
    assert (await client.get("/api/v1/attendance/today")).status_code == 401
    assert (await register_student(client)).status_code == 201
    assert (await login(client)).status_code == 200
    headers = await csrf_headers(client)
    assert (await client.get("/api/v1/meet/upcoming")).status_code == 403
    assert (await client.get("/api/v1/attendance/today")).status_code == 403
    denied = await client.patch(
        f"/api/v1/meet/classes/{uuid.uuid4()}",
        json={"version": 1, "meet_url": VALID_MEET},
        headers=headers,
    )
    assert denied.status_code == 403
    denied_attendance = await client.post(
        f"/api/v1/attendance/classes/{uuid.uuid4()}",
        json={"marks": [{"student_id": str(uuid.uuid4()), "status": "present"}]},
        headers=headers,
    )
    assert denied_attendance.status_code == 403


async def test_meet_link_is_saved_on_the_existing_class(client):
    headers = await _staff(client)
    batch = await _batch(client, headers)
    scheduled = await _scheduled(client, headers, batch["id"])
    assert scheduled["meet_url"] is None
    assert scheduled["meet_status"] == "missing"

    unsafe = await client.patch(
        f"/api/v1/meet/classes/{scheduled['id']}",
        json={"version": scheduled["version"], "meet_url": "https://evil.example/meet"},
        headers=headers,
    )
    assert unsafe.status_code == 422
    assert unsafe.json()["error"]["details"][0]["code"] == "INVALID_URL"

    saved = await client.patch(
        f"/api/v1/meet/classes/{scheduled['id']}",
        json={"version": scheduled["version"], "meet_url": f"{VALID_MEET}?authuser=0"},
        headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json()["data"]["meet_url"] == f"{VALID_MEET}?authuser=0"
    assert saved.json()["data"]["meet_status"] == "added"
    assert saved.json()["data"]["batch_id"] == batch["id"]
    assert saved.json()["data"]["version"] == 2

    listed = await client.get("/api/v1/timetable", params={"from": "2026-10-20", "to": "2026-10-20"})
    assert listed.json()["data"]["items"][0]["id"] == scheduled["id"]
    assert listed.json()["data"]["items"][0]["meet_url"] == f"{VALID_MEET}?authuser=0"

    replaced = await client.patch(
        f"/api/v1/meet/classes/{scheduled['id']}",
        json={"version": 2, "meet_url": LOOKUP_MEET},
        headers=headers,
    )
    assert replaced.status_code == 200
    assert replaced.json()["data"]["meet_url"] == LOOKUP_MEET

    stale = await client.patch(
        f"/api/v1/meet/classes/{scheduled['id']}",
        json={"version": 2, "meet_url": VALID_MEET},
        headers=headers,
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "STALE_UPDATE"

    cleared = await client.patch(
        f"/api/v1/meet/classes/{scheduled['id']}",
        json={"version": replaced.json()["data"]["version"], "meet_url": None},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["data"]["meet_status"] == "missing"
    upcoming = await client.get("/api/v1/meet/upcoming", params={"from": "2026-10-20", "to": "2026-10-20"})
    assert upcoming.status_code == 200
    assert upcoming.json()["data"]["items"][0]["meet_status"] == "missing"


async def test_teacher_can_record_and_correct_attendance_without_duplicates(client):
    headers = await _staff(client, role="TEACHER", email="teacher@example.com")
    first = await _student_record(client, headers, full_name="Asha Kulkarni")
    second = await _student_record(client, headers, full_name="Rahul Patil")
    outsider = await _student_record(client, headers, full_name="Meera Joshi")
    batch = await _batch(client, headers, student_ids=[first["id"], second["id"]])
    scheduled = await _scheduled(client, headers, batch["id"])
    class_id = scheduled["id"]

    roster = await client.get(f"/api/v1/attendance/classes/{class_id}")
    assert roster.status_code == 200
    assert roster.json()["data"]["completion"] == "not_recorded"
    assert [student["full_name"] for student in roster.json()["data"]["students"]] == [
        "Asha Kulkarni",
        "Rahul Patil",
    ]
    assert all(student["attendance"] is None for student in roster.json()["data"]["students"])

    unrelated = await client.post(
        f"/api/v1/attendance/classes/{class_id}",
        json={"marks": [{"student_id": outsider["id"], "status": "absent"}]},
        headers=headers,
    )
    assert unrelated.status_code == 422
    assert unrelated.json()["error"]["details"][0]["code"] == "STUDENT_NOT_IN_BATCH"

    saved = await client.post(
        f"/api/v1/attendance/classes/{class_id}",
        json={"marks": [{"student_id": first["id"], "status": "present", "notes": "On time"}]},
        headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json()["data"]["completion"] == "partial"
    asha = next(student for student in saved.json()["data"]["students"] if student["student_id"] == first["id"])
    rahul = next(student for student in saved.json()["data"]["students"] if student["student_id"] == second["id"])
    assert asha["attendance"]["status"] == "present"
    assert asha["attendance"]["version"] == 1
    assert rahul["attendance"] is None

    summary = await client.get("/api/v1/attendance/summary", params={"batch_id": batch["id"]})
    by_name = {item["full_name"]: item for item in summary.json()["data"]["items"]}
    assert by_name["Asha Kulkarni"]["percentage"] == 100.0
    assert by_name["Rahul Patil"]["eligible"] == 0
    assert by_name["Rahul Patil"]["absent"] == 0
    assert by_name["Rahul Patil"]["percentage"] is None

    edited = await client.post(
        f"/api/v1/attendance/classes/{class_id}",
        json={"marks": [{"student_id": first["id"], "status": "absent", "version": 1}]},
        headers=headers,
    )
    assert edited.status_code == 200
    edited_asha = next(student for student in edited.json()["data"]["students"] if student["student_id"] == first["id"])
    assert edited_asha["attendance"]["status"] == "absent"
    assert edited_asha["attendance"]["version"] == 2

    stale = await client.post(
        f"/api/v1/attendance/classes/{class_id}",
        json={"marks": [{"student_id": first["id"], "status": "present", "version": 1}]},
        headers=headers,
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "STALE_UPDATE"

    history = await client.get(
        "/api/v1/attendance/history",
        params={"student_id": first["id"], "from": "2026-10-01", "to": "2026-10-31"},
    )
    assert history.status_code == 200
    assert history.json()["data"]["total"] == 1
    assert history.json()["data"]["items"][0]["status"] == "absent"
    assert history.json()["data"]["items"][0]["scheduled_class_id"] == class_id
    assert history.json()["data"]["items"][0]["batch_name"] == "Evening Maths"

    duplicate = await client.post(
        f"/api/v1/attendance/classes/{class_id}",
        json={
            "marks": [
                {"student_id": second["id"], "status": "late"},
                {"student_id": second["id"], "status": "present"},
            ]
        },
        headers=headers,
    )
    assert duplicate.status_code == 422


async def test_summary_policy_and_history_survive_cancel_archive_and_removal(client):
    headers = await _staff(client)
    present = await _student_record(client, headers, full_name="Asha Kulkarni")
    absent = await _student_record(client, headers, full_name="Rahul Patil")
    late = await _student_record(client, headers, full_name="Meera Joshi")
    excused = await _student_record(client, headers, full_name="Kabir Shah")
    batch = await _batch(
        client,
        headers,
        student_ids=[present["id"], absent["id"], late["id"], excused["id"]],
    )
    scheduled = await _scheduled(client, headers, batch["id"])
    class_id = scheduled["id"]
    saved = await client.post(
        f"/api/v1/attendance/classes/{class_id}",
        json={
            "marks": [
                {"student_id": present["id"], "status": "present"},
                {"student_id": absent["id"], "status": "absent"},
                {"student_id": late["id"], "status": "late"},
                {"student_id": excused["id"], "status": "excused"},
            ]
        },
        headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json()["data"]["completion"] == "complete"

    summary = await client.get("/api/v1/attendance/summary", params={"class_id": class_id})
    totals = {"present": 0, "absent": 0, "late": 0, "excused": 0, "eligible": 0}
    for item in summary.json()["data"]["items"]:
        for key in totals:
            totals[key] += item[key]
    assert totals == {"present": 1, "absent": 1, "late": 1, "excused": 1, "eligible": 3}
    asha = next(item for item in summary.json()["data"]["items"] if item["student_id"] == present["id"])
    assert asha["percentage"] == 100.0

    removed = await client.delete(f"/api/v1/batches/{batch['id']}/students/{excused['id']}", headers=headers)
    assert removed.status_code == 200
    roster = await client.get(f"/api/v1/attendance/classes/{class_id}")
    assert excused["id"] not in {student["student_id"] for student in roster.json()["data"]["students"]}
    kept = await client.get("/api/v1/attendance/history", params={"student_id": excused["id"]})
    assert kept.json()["data"]["total"] == 1
    blocked = await client.post(
        f"/api/v1/attendance/classes/{class_id}",
        json={"marks": [{"student_id": excused["id"], "status": "present", "version": 1}]},
        headers=headers,
    )
    assert blocked.status_code == 422

    cancelled = await client.post(f"/api/v1/timetable/{class_id}/cancel", headers=headers)
    assert cancelled.status_code == 200
    still_there = await client.get("/api/v1/attendance/history", params={"class_id": class_id})
    assert still_there.json()["data"]["total"] == 4
    corrected = await client.post(
        f"/api/v1/attendance/classes/{class_id}",
        json={"marks": [{"student_id": late["id"], "status": "present", "version": 1}]},
        headers=headers,
    )
    assert corrected.status_code == 200
    outsider = await _student_record(client, headers, full_name="New Student")
    await client.post(
        f"/api/v1/batches/{batch['id']}/students",
        json={"student_ids": [outsider["id"]]},
        headers=headers,
    )
    added = await client.post(
        f"/api/v1/attendance/classes/{class_id}",
        json={"marks": [{"student_id": outsider["id"], "status": "present"}]},
        headers=headers,
    )
    assert added.status_code == 409
    assert added.json()["error"]["code"] == "CLASS_CANCELLED"

    today = coaching_today().isoformat()
    today_class = await _scheduled(
        client,
        headers,
        batch["id"],
        class_date=today,
        start_time="18:00:00",
        end_time="19:00:00",
    )
    today_status = await client.get("/api/v1/attendance/today")
    assert today_status.status_code == 200
    match = [item for item in today_status.json()["data"]["classes"] if item["id"] == today_class["id"]]
    assert match
    assert match[0]["completion"] == "not_recorded"

    archived = await client.post(f"/api/v1/batches/{batch['id']}/archive", headers=headers)
    assert archived.status_code == 200
    after_archive = await client.get("/api/v1/attendance/history", params={"batch_id": batch["id"]})
    assert after_archive.json()["data"]["total"] == 4
