# Sprint 3 audit — Batch management and timetable

This document has two parts. Sections A and B record the inspection done before Sprint 3 code was added. Section C records what was implemented afterward and the commands that were actually run.

Secret values from `.env` files are not included.

## A. Existing project overview (initial audit)

### Technologies and architecture

- Frontend: React 19, TypeScript, Vite 7, Material UI 7, Emotion, React Router 7, i18next (English, Marathi, Hindi), Vitest, Testing Library.
- Backend: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (psycopg), Pydantic Settings, PyJWT, Argon2id.
- Local database: PostgreSQL database `onlinetution`. Tests rewrite `DATABASE_URL` to database `onlinetution_test` and do not print the URL.

The frontend boots from `frontend/src/main.tsx` and `frontend/src/app/App.tsx`. Routes live in `frontend/src/app/routes/AppRoutes.tsx`. The signed-in shell is `frontend/src/layouts/AppLayout/AppLayout.tsx`. Navigation is `frontend/src/layouts/AppLayout/nav-items.ts`. HTTP calls go through `frontend/src/services/api/client.ts` with cookies and `X-CSRF-Token`.

The backend application is `backend/app/main.py`. Before this sprint it mounted:

- `/api/v1/auth`
- `/api/v1/users`
- `/api/v1/roles`
- `/api/v1/permissions`
- `/api/v1/students`
- `/api/v1/parents`

Persistence models are registered in `backend/app/models.py`. Migrations present before this sprint:

- `backend/alembic/versions/0001_auth_foundation.py`
- `backend/alembic/versions/0002_students_parents.py`

There is no batch table, enrollment table, scheduled-class table, batch API, or timetable API.

### Sprint 1 and Sprint 2, as found in the code

Sprint 1 is present and wired: cookie login, CSRF, refresh, password reset, roles, permissions, the signed-in shell, and the dashboard summary cards.

Sprint 2 is present and wired: `students` and `parents` tables, `student_parents` links, list/create/detail/edit/archive screens, search, filters, pagination, and permission keys `students.*` and `parents.*`. Administrators and teachers receive those keys. A login with the `STUDENT` role does not.

A student row is a class-register record. It is not a login account. It has no batch foreign key. A student can already have many parents through `student_parents`, so a many-to-many batch enrollment fits the same pattern without copying student fields onto a batch.

### Relevant file paths

| Area | Path |
| --- | --- |
| Auth migration | `backend/alembic/versions/0001_auth_foundation.py` |
| Register migration | `backend/alembic/versions/0002_students_parents.py` |
| Student model | `backend/app/students/models.py` |
| Parent model | `backend/app/parents/models.py` |
| Model registry | `backend/app/models.py` |
| API factory | `backend/app/main.py` |
| Dashboard metrics | `frontend/src/dashboard/metrics.ts` |
| Dashboard page | `frontend/src/dashboard/pages/DashboardPage.tsx` |
| Navigation | `frontend/src/layouts/AppLayout/nav-items.ts` |
| Routes | `frontend/src/app/routes/AppRoutes.tsx` |

### How authorization works

Unsafe methods require `X-CSRF-Token`. `require_permission` loads permission keys from the database. The sidebar hides an item when the signed-in user lacks its permission. Items marked `comingSoon` stay disabled and do not navigate.

`loadDashboardMetrics` reads `GET /api/v1/students/summary` for the active student count. Batches, today's classes, and pending fees are hard-coded as unavailable. The student count is not invented when the request is forbidden or fails.

Reusable UI: Material UI theme, `ErrorAlert`, `LoadingScreen`, `ConfirmDialog`, list tables, and English/Hindi/Marathi strings. The API client supports `get`, `post`, `patch`, and `delete`.

Clock timestamps in the database are timezone-aware UTC. There is no class-time timezone setting. Class dates, if added, need an explicit convention. This sprint uses Asia/Kolkata wall-clock dates and times, because the coaching classes are in India and the app has no per-user timezone.

There is no teacher-assignment table and no room table. Schedule conflicts cannot mention a teacher or a room without inventing those records.

### Business rule for this sprint

Students may belong to more than one batch, because one student can take more than one subject. The link is a `batch_students` row. It stores only the student id, the batch id, and when the link was created. Student name, school, and contact data stay on `students`.

Batches are archived, not hard-deleted. Scheduled classes are cancelled, not hard-deleted. Neither action removes student or parent rows.

## B. Feature status before implementation

### Batch management

#### 1. Batch list — Missing

Evidence: `AppRoutes` has no `/app/batches` route. The sidebar item is `comingSoon: true` and has no `to`. No component renders a batch table.

Files: `frontend/src/app/routes/AppRoutes.tsx`, `frontend/src/layouts/AppLayout/nav-items.ts`.

Missing work: a protected list with search, filters, student counts, status, and actions.

Recommended action: add the page inside `AppLayout` for `batches.read`.

#### 2. Create batch — Missing

Evidence: no batch form and no `POST` batch route.

Missing work: required name, optional subject, grade, and description, server-side checks, and a generated batch id.

Recommended action: add `POST /api/v1/batches` and a create form. Generate `BAT-######` the same way student ids are generated.

#### 3. Edit batch — Missing

Evidence: no batch update form or `PATCH` route.

Missing work: load current values, reject a stale version, and leave untouched fields alone.

Recommended action: follow the student update flow, including `version`.

#### 4. View batch details — Missing

Evidence: no detail route or component.

Missing work: batch fields, assigned students, student count, status, and the next class.

Recommended action: add `/app/batches/:batchId`.

#### 5. Archive or safely delete a batch — Missing

Evidence: no batch row exists, so nothing can be archived. Student archive already avoids hard delete because later modules must keep history.

Missing work: a confirmed archive that keeps the row, enrollments, and classes.

Recommended action: store `active`, `inactive`, and `archived`. Do not offer hard delete.

#### 6. Assign students to batches — Missing

Evidence: `Student` has no batch relationship. `student_parents` is the only link table, and it links guardians.

Missing work: a many-to-many enrollment table and an assign action that uses existing student ids.

Recommended action: add `batch_students` with a primary key of `(batch_id, student_id)` so the same pair cannot be stored twice.

#### 7. Remove students from batches — Missing

Evidence: no enrollment row to remove.

Missing work: delete the link only. Leave the student row in place.

Recommended action: `DELETE /api/v1/batches/{id}/students/{student_id}` with confirmation in the UI.

#### 8. Batch search and filtering — Missing

Evidence: student listing can search name and code and filter grade and status. Nothing equivalent exists for batches.

Missing work: search by batch name or code, filter by status, subject, and grade, plus sort and pagination.

Recommended action: put those parameters on the list endpoint and the list page.

#### 9. Batch status management — Missing

Evidence: student status is `active`, `inactive`, or `archived`. Batches have no status.

Missing work: the same three values. New classes should require an active batch. Archive is a separate action.

Recommended action: default new batches to `active`.

#### 10. Database persistence and authorization — Missing

Evidence: `backend/app/models.py` does not import a batch model. `create_app` does not mount a batch router. Permissions stop at student and parent keys.

Missing work: tables, migration `0003`, and `batches.read`, `batches.create`, `batches.update`, `batches.archive` for `ADMIN` and `TEACHER`.

Recommended action: add the migration without editing `0001` or `0002` and without deleting existing rows.

### Timetable management

#### 1. Timetable page — Missing

Evidence: the sidebar item is coming soon. No `/app/timetable` route exists.

Missing work: a week view with loading, empty, and error states.

Recommended action: build the week with Material UI layout. Do not add a calendar library.

#### 2. Weekly schedule display — Missing

Evidence: no schedule component and no class query.

Missing work: previous week, next week, and a return to the current week, in Asia/Kolkata.

Recommended action: derive the week in a small date helper and load classes with `from` and `to`.

#### 3. Create scheduled class — Missing

Evidence: no class table and no create form.

Missing work: batch, date, start, end, optional topic and notes.

Recommended action: the class row stores `batch_id` only. Batch name is read from `batches`.

#### 4. Edit scheduled class — Missing

Evidence: no class update API.

Missing work: load the current row, validate, recheck conflicts, and save with a version check.

Recommended action: `PATCH /api/v1/timetable/{id}`.

#### 5. Cancel or remove a scheduled class — Missing

Evidence: no class status.

Missing work: cancellation that keeps the row. Attendance does not exist yet, and a later attendance table must be able to point at the class.

Recommended action: status `scheduled` or `cancelled`. Hide cancelled rows unless the user asks to see them. Do not delete the row.

#### 6. Assign a class to a batch — Missing

Evidence: no class row, so no batch reference.

Missing work: a required `batch_id` that must already exist.

Recommended action: reject unknown and archived batches. Allow new classes only on active batches.

#### 7. Set date, start time, and end time — Missing

Evidence: no time columns.

Missing work: date and time validation, including end after start.

Recommended action: store `class_date` as a date and `start_time` / `end_time` as times. Interpret them as Asia/Kolkata wall-clock values. Do not convert them to UTC, because the screen asks for a clock time, not an instant.

#### 8. Recurring class schedules — Missing

Evidence: no recurrence fields and no occurrence generator.

Missing work: weekday repeat, a start date, an optional end date, and a preview before save.

Recommended action: expand the preview into ordinary class rows in one transaction. Do not store a hidden series that creates classes without showing them. Cap the batch at 60 classes. If the end date is empty, use eight weeks. Editing or cancelling later changes one class, not the whole series.

#### 9. Schedule conflict validation — Missing

Evidence: no class rows to compare.

Missing work: reject `end <= start`, reject overlaps for the same batch, allow a class that starts when another ends, and recheck on edit.

Recommended action: overlap is `new_start < existing_end AND new_end > existing_start`, ignoring cancelled rows and the row being edited. Lock the batch row during the write. Add a partial unique index on active `(batch_id, class_date, start_time)`.

Teacher and room overlap cannot be checked. Those resources are not in the schema. Do not add them in this sprint.

#### 10. Dashboard integration — Partial

Evidence: the dashboard renders four cards. Only Total Students calls an API. Total Batches and Today's Classes are fixed as unavailable in `frontend/src/dashboard/metrics.ts`. Pending Fees is also unavailable, which is correct because fees are out of scope. Cards do not link anywhere. There is no upcoming-class list.

Files: `frontend/src/dashboard/metrics.ts`, `frontend/src/dashboard/pages/DashboardPage.tsx`, `frontend/src/dashboard/components/SummaryCard.tsx`.

Missing work: live active-batch and today's-class counts, an upcoming list, and links to the new pages.

Recommended action: add summary endpoints and keep Pending Fees unavailable. Keep the existing card layout.

#### 11. Responsive layout and error states — Partial

Evidence: `AppLayout` already switches between a permanent sidebar and a drawer. Student and parent pages stack on narrow screens and reuse `ErrorAlert`, `LoadingScreen`, and `ConfirmDialog`. No batch or timetable screen exists to use them.

Missing work: a week grid that becomes a single column on a phone, plus the same loading, empty, and error patterns.

Recommended action: reuse the Sprint 2 page structure. Do not restyle login, students, or parents.

### Initial recommendation

No blocker required a product decision. The student register can be linked with a new enrollment table. Implementation can stay inside the current FastAPI app, React app, and PostgreSQL database.

## C. Implementation outcome

Sprint 3 is complete for the scoped modules. Google Meet, attendance, fees, and receipts were not added. Pending Fees on the dashboard stays unavailable on purpose.

### Already complete before this sprint

- Sprint 1: cookie login, CSRF, refresh, password reset, roles, permissions, app shell, and dashboard cards.
- Sprint 2: student and parent register, search, archive, and guardian links. Students had no batch column, so enrollment did not need to copy student data.

### Implemented in this sprint

- Batches: list, create, edit, detail, archive, search, filters, sort, and pagination.
- Many-to-many enrollment in `batch_students`. One student can be in more than one batch. Assigning does not copy or overwrite the student row. The same pair cannot be stored twice.
- Timetable week view, create, edit, and cancel. Cancel keeps the row and hides it unless "Show cancelled classes" is on.
- Weekly repeat with a preview. Saving writes one class row per shown date, at most 60. An empty end date means eight weeks. Later edits and cancellations change that one class only.
- Conflict checks: end time must be later than the start; overlapping times for the same batch are rejected; a class that starts when another ends is allowed. The batch row is locked during the write. A partial unique index blocks two active classes for the same batch, date, and start time.
- Dashboard cards for active batches and today's classes use the API. Upcoming classes link to the matching week. Pending Fees is unchanged.
- Student detail shows batch membership for users who can read batches.
- Navigation enables Batches and Timetable for `batches.read` and `timetable.read`.

### Business rules

- Batch status is `active`, `inactive`, or `archived`. New classes require an active batch. Archive does not delete students, enrollment rows, or classes.
- Class `class_date`, `start_time`, and `end_time` are Asia/Kolkata wall-clock values. They are not converted to UTC. "Today" and the current week use that zone.
- There is no teacher table and no room table. Overlaps are checked per batch only.
- Removing a student deletes only the enrollment row. A later attendance module should point at the class and the student, not at this link, so removal does not erase class history.

### Still partial or out of scope

- Pending Fees: unavailable until the fees sprint.
- Google Meet, attendance, fees, and receipts: navigation stays disabled.
- Editing one class from a repeat does not change the other dates.
- The timetable batch picker loads up to 100 batches.
- Authenticated screens were not clicked in the browser during this session. There was no signed-in browser session, and a test account was not created in the local coaching database. Guest visits to `/app/batches` return to the login page. The live API rejects an anonymous batch list with 401.

### Database migration

Revision `0003_batches_timetable` revises `0002_students_parents`. It creates `batches`, `batch_students`, `scheduled_classes`, `batch_code_seq`, and the batch and timetable permissions for `ADMIN` and `TEACHER`. It does not delete existing rows.

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

This machine's virtual environment is `backend/venv`, so the command used here was `.\venv\Scripts\python.exe -m alembic upgrade head`. That command was run against the configured local database and applied `0002_students_parents -> 0003_batches_timetable`. Tests apply the same revision to `onlinetution_test` and truncate only test rows.

### Files created

- `backend/alembic/versions/0003_batches_timetable.py`
- `backend/app/common/time.py`
- `backend/app/batches/` models, schemas, service, router
- `backend/app/timetable/` models, schemas, service, router
- `backend/tests/test_batches_timetable.py`
- `frontend/src/batches/` API, types, validation, list, form, and detail pages
- `frontend/src/timetable/` API, types, validation, week helper, week page, and class dialog
- `frontend/src/i18n/locales/{en,hi,mr}/batches.json`
- `frontend/src/i18n/locales/{en,hi,mr}/timetable.json`
- `docs/sprint-3-audit.md`

### Files modified

- `backend/app/models.py`, `backend/app/main.py`, `backend/app/common/exceptions.py`, `backend/tests/conftest.py`
- `frontend/src/app/routes/AppRoutes.tsx`
- `frontend/src/layouts/AppLayout/nav-items.ts`
- `frontend/src/i18n/index.ts` and the English, Hindi, and Marathi common, validation, dashboard, and student strings
- `frontend/src/dashboard/metrics.ts`, `DashboardPage.tsx`, `SummaryCard.tsx`
- `frontend/src/students/pages/StudentDetailPage.tsx`
- `frontend/src/roster/format.ts`
- `README.md`

### Tests and commands actually run

| Command | Result |
| --- | --- |
| `backend`: `.\venv\Scripts\python.exe -m pytest -q --tb=line` | 43 passed |
| `backend`: `.\venv\Scripts\python.exe -m ruff check app tests` | All checks passed |
| `backend`: `.\venv\Scripts\python.exe -m mypy app` | No issues in 67 source files |
| `frontend`: `npm test` | 15 files, 47 tests passed |
| `frontend`: `npm run lint` | Passed |
| `frontend`: `npm run build` | `tsc --noEmit` and the Vite build passed |

The new API tests cover create, list, detail, edit, stale version, search, assign one and many students, duplicate assignment, remove, archive, invalid times, overlap, consecutive classes, cancel, reuse of a cancelled slot, recurring preview and create, dashboard counts, teacher access, and student-role rejection. Frontend tests cover the batch list, the week grid, week navigation, dashboard links, and the India calendar date.

### Manual check

1. From `backend/`, apply migrations with the command above and start the API: `.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
2. From `frontend/`, run `npm run dev` and open `http://localhost:5173`.
3. Sign in as an administrator or teacher.
4. Create a batch, assign students from the detail page, and confirm the same student can join a second batch.
5. Open Timetable, add a class, move to next week and back with This week, then edit and cancel a class.
6. Try a second class that overlaps the first. It should be rejected. A class that starts when the first ends should save.
7. Turn on Repeat weekly, preview the dates, then save.
8. Confirm the dashboard batch count, today's classes, and upcoming list match those records. Pending Fees should still say it is not available yet.
9. Open a student and confirm the batch names. Archive a batch and confirm the student and class rows remain.

### Final status

**Complete.** Batch management, student assignment, the timetable, conflict checks, and the related dashboard cards are implemented on the existing app and database. The limits above are recorded so later sprints do not assume a teacher, a room, or a recurring series editor.
