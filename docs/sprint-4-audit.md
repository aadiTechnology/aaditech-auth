# Sprint 4 audit — Google Meet and attendance

This document has two parts. Sections A and B record the inspection done before Sprint 4 code was added. Section C records what was implemented afterward and the commands that were actually run.

Secret values from `.env` files are not included. Meeting URLs stored by an administrator are not secrets, but this audit does not copy live links from the coaching database.

## A. Existing project overview (initial audit)

### Technologies and architecture

- Frontend: React 19, TypeScript, Vite 7, Material UI 7, Emotion, React Router 7, i18next (English, Marathi, Hindi), Vitest, Testing Library.
- Backend: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (psycopg), Pydantic Settings, PyJWT, Argon2id.
- Local database: PostgreSQL database `onlinetution`. Tests rewrite `DATABASE_URL` to database `onlinetution_test` and do not print the URL.

The frontend boots from `frontend/src/main.tsx` and `frontend/src/app/App.tsx`. Routes live in `frontend/src/app/routes/AppRoutes.tsx`. The signed-in shell is `frontend/src/layouts/AppLayout/AppLayout.tsx`. Navigation is `frontend/src/layouts/AppLayout/nav-items.ts`. HTTP calls go through `frontend/src/services/api/client.ts` with cookies and `X-CSRF-Token`. The client supports `GET`, `POST`, `PATCH`, and `DELETE`. CORS on the API allows those methods.

The backend application is `backend/app/main.py`. Before this sprint it mounted:

- `/api/v1/auth`
- `/api/v1/users`
- `/api/v1/roles`
- `/api/v1/permissions`
- `/api/v1/students`
- `/api/v1/parents`
- `/api/v1/batches`
- `/api/v1/timetable`

Persistence models are registered in `backend/app/models.py`. Migrations present before this sprint:

- `backend/alembic/versions/0001_auth_foundation.py`
- `backend/alembic/versions/0002_students_parents.py`
- `backend/alembic/versions/0003_batches_timetable.py`

There is no Google OAuth setting, Google Calendar client, Meet conference API, `meet_url` column, or attendance table. `backend/app/core/config.py` loads database, JWT, cookie, email, and rate-limit settings only.

### Sprints 1, 2, and 3, as found in the code

Sprint 1 is present and wired: cookie login, CSRF, refresh, password reset, roles, permissions, the signed-in shell, and the dashboard summary cards.

Sprint 2 is present and wired: `students` and `parents` tables, `student_parents` links, list/create/detail/edit/archive screens, search, filters, pagination, and permission keys `students.*` and `parents.*`. A student row is a class-register record. It is not a login account. It has `student_code` values such as `STU-000001`.

Sprint 3 is present and wired: `batches`, `batch_students`, and `scheduled_classes`. A class stores `batch_id`, an Asia/Kolkata date, start and end times, topic, notes, and status `scheduled` or `cancelled`. It does not copy the batch name. Students belong to a batch through `batch_students` (`batch_id`, `student_id`). One student can be in more than one batch. Removing a student deletes only that link. Archiving a batch and cancelling a class keep the rows. Sprint 3's audit says a later attendance table should point at the class and the student, not at the enrollment link.

The dashboard reads live student, batch, and today's class counts. Pending Fees stays unavailable. Upcoming classes link to the timetable week. They do not include a meeting link.

Navigation enables Dashboard, and, when permitted, Students, Parents, Batches, and Timetable. Google Meet, Attendance, Fees, and Receipts are `comingSoon` and do not navigate.

### Relevant file paths

| Area | Path |
| --- | --- |
| Auth migration | `backend/alembic/versions/0001_auth_foundation.py` |
| Register migration | `backend/alembic/versions/0002_students_parents.py` |
| Batch and class migration | `backend/alembic/versions/0003_batches_timetable.py` |
| Scheduled class model | `backend/app/timetable/models.py` |
| Enrollment model | `backend/app/batches/models.py` |
| Model registry | `backend/app/models.py` |
| API factory | `backend/app/main.py` |
| Settings | `backend/app/core/config.py` |
| Dashboard | `frontend/src/dashboard/pages/DashboardPage.tsx` |
| Navigation | `frontend/src/layouts/AppLayout/nav-items.ts` |
| Routes | `frontend/src/app/routes/AppRoutes.tsx` |

### How authorization works

Unsafe methods require `X-CSRF-Token`. `require_permission` loads permission keys from the database. The sidebar hides an item when the signed-in user lacks its permission. Items marked `comingSoon` stay disabled.

`ADMIN` and `TEACHER` receive student, parent, batch, and timetable keys. A `STUDENT` login does not. There is no `meet.*` or `attendance.*` key.

Reusable UI: Material UI theme, `ErrorAlert`, `LoadingScreen`, `ConfirmDialog`, list pages, and English/Hindi/Marathi strings.

### Initial recommendation

No product decision blocked the sprint. A Meet link belongs on the existing `scheduled_classes` row, which already points at a batch. Attendance belongs in a new table that points at `scheduled_classes.id` and `students.id`. Automatic Google conference creation was not possible: there is no OAuth client, consent screen, or Calendar API. The reliable baseline is a validated link pasted by an administrator.

## B. Feature status before implementation

### Google Meet

#### 1. Google Meet link management — Missing

Evidence: navigation item `googleMeet` is `comingSoon: true` and has no route. No module, table column, or API mentions a Meet URL. A search of the application source finds the label only.

Files: `frontend/src/layouts/AppLayout/nav-items.ts`, `frontend/src/app/routes/AppRoutes.tsx`.

Missing work: a place to add, replace, view, and clear a link for a class that already exists.

Recommended action: store the URL on `scheduled_classes` and add `meet.read` and `meet.update`.

#### 2. Linking a Meet URL to a scheduled class — Missing

Evidence: `ScheduledClass` has batch, date, times, topic, notes, and status. It has no URL column.

Files: `backend/app/timetable/models.py`, `backend/alembic/versions/0003_batches_timetable.py`.

Missing work: a nullable column and an update that does not create a second class.

Recommended action: `PATCH` the existing class through a meeting endpoint that checks `version`.

#### 3. Linking a Meet URL to the correct batch — Missing

Evidence: the class already stores `batch_id`. Nothing stores a link, so the batch relationship is unused for meetings.

Missing work: read the batch through the class. Do not copy the batch onto a meeting record.

Recommended action: return `batch_id`, `batch_name`, and `batch_code` with the link.

#### 4. Creating or editing a Meet link — Missing

Evidence: class create and update schemas accept date, time, topic, and notes only.

Files: `backend/app/timetable/schemas.py`, `frontend/src/timetable/components/ClassDialog.tsx`.

Missing work: add, replace, and clear, with a stale-version rejection.

Recommended action: a dialog used from the timetable and from a Meet page.

#### 5. Opening the meeting from the timetable or dashboard — Missing

Evidence: a timetable class opens the class dialog. A dashboard class links to `/app/timetable?date=...`. Neither renders an external URL.

Files: `frontend/src/timetable/pages/TimetablePage.tsx`, `frontend/src/dashboard/pages/DashboardPage.tsx`.

Missing work: a join control that opens only a checked HTTPS Meet URL.

Recommended action: `target="_blank"` and `rel="noopener noreferrer"` after the same URL check used on the server.

#### 6. Validating Meet URLs — Missing

Evidence: no URL parser accepts or rejects Meet links. The validation catalog has no Meet code.

Missing work: reject non-HTTPS, other hosts, `javascript:`, userinfo, and redirect-style query parameters. Accept `https://meet.google.com/abc-defg-hij` and `https://meet.google.com/lookup/...`.

Recommended action: one checker on the server and the same rules in the browser before save and before open.

#### 7. Displaying upcoming class meeting links — Missing

Evidence: `GET /api/v1/timetable/summary` returns id, batch, date, time, and topic. The dashboard prints those fields only.

Files: `backend/app/timetable/schemas.py`, `frontend/src/dashboard/metrics.ts`.

Missing work: `added` or `missing` on each upcoming and today's class.

Recommended action: extend the summary. Do not invent a link.

#### 8. Secure handling of Google credentials or API configuration — Missing, with nothing to leak

Evidence: settings have no Google client id, client secret, refresh token, or API key. No source file hardcodes one.

Files: `backend/app/core/config.py`.

Missing work: none for credentials, because automatic creation is not configured. Do not add a secret to the repository.

Recommended action: keep manual links. Document that Google conference creation is future work.

#### 9. Clear handling of missing or expired meeting links — Missing

Evidence: there is no empty state for a missing link. Expiry cannot be known without the Meet API, and that API is not configured.

Missing work: a visible missing state. A note that expiry cannot be detected.

Recommended action: status `missing` when the column is null. Tell the user to paste a new link if a saved meeting does not open.

### Attendance

#### 1. Attendance page — Missing

Evidence: the sidebar item is coming soon. `AppRoutes` has no `/app/attendance` route.

Missing work: a page inside `AppLayout` for `attendance.read`.

Recommended action: batch, class, roster, save, history, and summary on one page.

#### 2. Selecting a batch and scheduled class — Missing

Evidence: batches and classes exist, but no screen selects them for attendance.

Missing work: both pickers, using existing ids.

Recommended action: query `batch` and `class` so the dashboard can link to a class.

#### 3. Loading the enrolled students — Missing

Evidence: enrollment is `batch_students`. No endpoint returns that roster for a class.

Missing work: students currently enrolled in the class's batch, with student code and name.

Recommended action: `GET /api/v1/attendance/classes/{class_id}`.

#### 4. Marking students Present or Absent — Missing

Evidence: no status field and no control.

Missing work: Present and Absent, chosen explicitly.

Recommended action: also support Late and Excused, because a coaching register needs them and they can be counted with one published rule.

#### 5. Late or Excused — Missing

Evidence: no attendance status exists, so neither optional status exists.

Missing work: store both, and do not treat Late or Excused as Present.

Recommended action: Late counts in the denominator only. Excused is stored and left out of both sides.

#### 6. Saving attendance records — Missing

Evidence: no attendance table and no save route.

Missing work: a transactional save of the marks the user included.

Recommended action: `POST /api/v1/attendance/classes/{class_id}` with `attendance.update`.

#### 7. Editing previously saved attendance — Missing

Evidence: there is no row to edit.

Missing work: update the same row and increment `version`.

Recommended action: reject a stale version with `STALE_UPDATE`.

#### 8. Preventing duplicate attendance entries — Missing

Evidence: no unique key.

Missing work: one row per student per scheduled class.

Recommended action: `UNIQUE (scheduled_class_id, student_id)`.

#### 9. Viewing attendance history — Missing

Evidence: no history query or screen.

Missing work: filter by batch, student, class, and date range, and show the class details from `scheduled_classes`.

Recommended action: `GET /api/v1/attendance/history`.

#### 10. Filtering attendance by batch, student, or date — Missing

Evidence: student and batch list filters exist for those modules. Nothing filters attendance.

Missing work: the history and summary query parameters.

Recommended action: require at least one of batch, student, or class so the endpoint cannot dump every row by accident.

#### 11. Calculating attendance summaries — Missing

Evidence: the dashboard does not calculate attendance. No count is stored.

Missing work: present, absent, late, excused, eligible, and percentage from saved rows only.

Recommended action: percentage = present / (present + absent + late) × 100, half up to one decimal. Null when the denominator is 0. Unrecorded classes are not absences.

#### 12. Protecting attendance records from unauthorized access — Missing

Evidence: there is no attendance permission. The student role is already blocked from batch and timetable APIs, but there is no attendance API to protect.

Missing work: `attendance.read` and `attendance.update` for `ADMIN` and `TEACHER` only.

Recommended action: the same `require_permission` dependency used by the other modules.

### Dashboard, before this sprint

Today's class count and the upcoming list are live. They do not show meeting status or attendance completion. Pending Fees is unavailable on purpose. That card must stay unavailable.

### Initial recommendation

Implementation can stay inside the current FastAPI app, React app, and PostgreSQL database. Do not reset the database. Add migration `0004` only.

## C. Implementation outcome

Sprint 4 is complete for manual Meet links and administrator-recorded attendance. Google does not create the meetings. The app cannot tell whether a saved link has expired. Fees and receipts were not added.

### Already complete before this sprint

- Sprint 1: cookie login, CSRF, refresh, password reset, roles, permissions, app shell, and dashboard cards.
- Sprint 2: student and parent register, search, archive, and guardian links. Students keep `student_code`.
- Sprint 3: batches, many-to-many enrollment, timetable, conflict checks, cancel, and live dashboard counts for students, batches, and today's classes.

### Implemented in this sprint

- A Meet URL is stored on the existing `scheduled_classes` row. Adding a link does not create a class or a batch. The batch is the class's `batch_id`.
- Accepted URLs are HTTPS on `meet.google.com`: a code such as `abc-defg-hij`, or `/lookup/` plus 10 to 64 letters, numbers, `_`, or `-`. Optional short query parameters are kept. `http`, other hosts, userinfo, fragments, `javascript:`, and redirect-style parameters are rejected. The same rules run in the browser before save and before a join link is rendered.
- Join links use `target="_blank"` and `rel="noopener noreferrer"`.
- Timetable cards and the dashboard show Link added or Link missing. A missing class has an explanation. The Meet page lists the next 14 days.
- Cancelled classes keep the current link. The link cannot be changed after cancel.
- Attendance rows point at `scheduled_classes` and `students`. They do not point at `batch_students`. Removing a student, cancelling a class, or archiving a batch leaves the attendance rows in place.
- Statuses are Present, Absent, Late, and Excused. A student with no row is not absent. The roster shows "Not recorded". Save writes only the students included in the request.
- One database unique key allows one row per student per class. A second save updates that row when `version` matches. A stale version returns 409. A student who is not enrolled in that class's batch is rejected. New marks cannot be added to a cancelled class. Existing marks on a cancelled class can be corrected.
- History filters by batch, student, class, and dates. Summary uses saved rows only.
- Percentage = Present ÷ (Present + Absent + Late) × 100, rounded half up to one decimal. Late is not Present. Excused is excluded from both sides. The percentage is null when there is no eligible row.
- Dashboard "Today's classes" lists real classes, join links, and a count of classes with no link. "Attendance today" links to the class roster and shows not recorded, partial, or saved. A forbidden module stays "not available". Pending Fees is unchanged.
- `ADMIN` and `TEACHER` receive `meet.read`, `meet.update`, `attendance.read`, and `attendance.update`. A student login does not. Anonymous requests receive 401.

### Attendance policy

| Status | In the numerator | In the denominator |
| --- | --- | --- |
| Present | Yes | Yes |
| Absent | No | Yes |
| Late | No | Yes |
| Excused | No | No |
| No row saved | No | No |

Completion for a class compares saved rows with students enrolled now: `not_recorded`, `partial`, `complete`, or `no_students`.

### Still partial or out of scope

- Automatic Google Meet creation is not implemented. There is no OAuth client, Calendar API, or conference-creation call. Do not treat a pasted link as proof that Google verified attendance.
- Expired links cannot be detected. The Meet page says so and asks for a new link when a meeting does not open.
- Fees and receipts stay disabled. Pending Fees stays unavailable.
- The timetable and Meet batch pickers still load up to 100 batches.
- A signed-in browser session during this check was a `STUDENT` login. That account was correctly denied `/app/meet` and `/app/attendance`, and the dashboard did not invent counts. An administrator click-through in the browser was not done, because that would have used the coaching database. The administrator flows were executed against `onlinetution_test`.

### Database migration

Revision `0004_meet_attendance` revises `0003_batches_timetable`. It adds nullable `scheduled_classes.meet_url`, check `scheduled_classes_meet_url_https`, table `attendance_records`, unique `(scheduled_class_id, student_id)`, and the four permissions for `ADMIN` and `TEACHER`. It does not delete rows.

From `backend/`:

```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
```

That command was run against the configured local database and applied `0003_batches_timetable -> 0004_meet_attendance`. `alembic current` then reported `0004_meet_attendance (head)`. Tests apply the same revision to `onlinetution_test` and truncate test rows, including `attendance_records`.

The API process that was already listening on port 8000 had been started before these routes existed and was not using reload. It was stopped and started again so `/api/v1/meet` and `/api/v1/attendance` are loaded. Anonymous calls to both return 401 `UNAUTHENTICATED`.

### Files created

- `backend/alembic/versions/0004_meet_attendance.py`
- `backend/app/meet/` URL check, service, and router
- `backend/app/attendance/` model, schemas, service, and router
- `backend/tests/test_meet_attendance.py`
- `frontend/src/meet/` URL check, API, join link, link dialog, and Meet page
- `frontend/src/attendance/` types, API, and attendance page
- `frontend/src/i18n/locales/{en,hi,mr}/meet.json`
- `frontend/src/i18n/locales/{en,hi,mr}/attendance.json`
- `docs/sprint-4-audit.md`

### Files modified

- `backend/app/models.py`, `backend/app/main.py`, `backend/app/common/exceptions.py`, `backend/tests/conftest.py`
- `backend/app/timetable/models.py`, `schemas.py`, `service.py`, `router.py`
- `frontend/src/app/routes/AppRoutes.tsx`
- `frontend/src/layouts/AppLayout/nav-items.ts` and `AppLayout.test.tsx`
- `frontend/src/i18n/index.ts` and the English, Hindi, and Marathi common, validation, and dashboard strings
- `frontend/src/dashboard/metrics.ts`, `metrics.test.ts`, `DashboardPage.tsx`, `DashboardPage.test.tsx`
- `frontend/src/timetable/types.ts`, `TimetablePage.tsx`, `TimetablePage.test.tsx`

### Tests and commands actually run

| Command | Result |
| --- | --- |
| `backend`: `.\venv\Scripts\python.exe -m pytest -q --tb=line` | 48 passed, 4 existing deprecation warnings |
| `backend`: `.\venv\Scripts\python.exe -m ruff check app tests` | All checks passed |
| `backend`: `.\venv\Scripts\python.exe -m mypy app` | No issues in 76 source files |
| `frontend`: `npm test` | 18 files, 51 tests passed |
| `frontend`: `npm run lint` | Passed |
| `frontend`: `npm run build` | `tsc --noEmit` and the Vite build passed |

The new API tests cover URL acceptance and rejection, add, replace, clear, stale version, the link staying on the same class and batch, teacher attendance, present and absent, partial save, unmarked students left out of the percentage, edit without a duplicate row, duplicate payload rejection, a student from another batch, history filters, Late and Excused arithmetic (1 present / 3 eligible = 33.3%), history after removal, cancel, and archive, and anonymous and student-role rejection.

Frontend tests cover the Meet URL checker, the Meet page join link and missing state, attendance save of only the marked student, timetable join link, dashboard join and attendance links, and navigation.

Browser check on `http://localhost:5173`, already signed in as a student named Ayush:

- Dashboard shows Today's classes and Attendance today as not available. It does not show a zero count.
- Navigation shows Fees and Receipts as Coming soon. Google Meet and Attendance are not links for that role.
- `/app/meet` and `/app/attendance` redirect to Access denied.

### Manual check

1. From `backend/`, apply migrations with the command above and start the API: `.\venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000`
2. From `frontend/`, run `npm run dev` and open `http://localhost:5173`.
3. Sign in as an administrator or teacher.
4. Open Timetable, choose a scheduled class, and add `https://meet.google.com/abc-defg-hij`. Confirm Link added, then Join meeting. Replace it, then remove it and confirm Link missing.
5. Try `https://evil.example/meet` and an `http://` Meet URL. Both should be rejected, and Join should not render them.
6. Open Google Meet and confirm the same class and batch. The page should say that expiry cannot be detected.
7. Open Attendance, select the batch and class, and confirm the enrolled students. Leave one unmarked, mark another Present, and save. Reload and confirm the statuses. The unmarked student stays "Not recorded".
8. Change Present to Absent and save again. History for that student and date should still be one row.
9. Use Mark all present only after confirming the dialog, then save.
10. Open the summary and confirm the percentage matches Present ÷ (Present + Absent + Late). Excused rows should not increase or reduce it.
11. Cancel the class or archive the batch and confirm the history is still listed.
12. Sign in as a student login and confirm Meet and Attendance are denied. Pending Fees should still say it is not available yet.

### Final status

**Complete.** Manual Google Meet links and attendance marking, editing, history, and summaries are implemented on the existing classes, batches, and students. Automatic Google meeting creation and fee collection remain out of scope.
