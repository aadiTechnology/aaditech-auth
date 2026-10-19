# Sprint 2 audit — Student and parent management

This document records the inspection performed before Sprint 2 implementation, then the work completed afterward. The initial findings below describe the repository as it existed before student and parent records were added.

Secret values from `.env` files are not included.

## A. Existing project overview (initial audit)

### Technologies and architecture

- Frontend: React 19, TypeScript, Vite 7, Material UI 7, Emotion, React Router 7, i18next (English, Marathi, Hindi), Vitest, Testing Library.
- Backend: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (psycopg), Pydantic Settings, PyJWT, Argon2id.
- Local database: PostgreSQL database `onlinetution`, documented on port 5433. Tests rewrite `DATABASE_URL` to database `onlinetution_test` and do not print the URL.

The frontend boots from `frontend/src/main.tsx` and `frontend/src/app/App.tsx`. Routes live in `frontend/src/app/routes/AppRoutes.tsx`. The signed-in shell is `frontend/src/layouts/AppLayout/AppLayout.tsx` with sidebar config in `frontend/src/layouts/AppLayout/nav-items.ts`. Session state is `frontend/src/store/auth-context.tsx`. HTTP calls go through `frontend/src/services/api/client.ts`, which sends cookies and `X-CSRF-Token`.

The backend application is `backend/app/main.py`. It mounts only:

- `/api/v1/auth`
- `/api/v1/users`
- `/api/v1/roles`
- `/api/v1/permissions`

Persistence models are registered in `backend/app/models.py`. The only migration is `backend/alembic/versions/0001_auth_foundation.py`.

### Existing student and parent functionality

None. There is no student table, parent table, student API, parent API, student page, or parent page.

The word "student" in Sprint 1 means a login role. Public registration always creates a `STUDENT` account in `users` and ignores any role sent by the client. That account can sign in. It is not a coaching-class register entry and does not store a school, grade, guardian, or enrollment date.

`README.md` states that the repository does not include classes, attendance, fees, or other ERP features. That description matched the code at the start of this sprint.

### Relevant file paths

| Area | Path |
| --- | --- |
| Schema migration | `backend/alembic/versions/0001_auth_foundation.py` |
| Login user model | `backend/app/users/models.py` |
| Roles and permissions | `backend/app/roles/models.py`, `backend/app/permissions/models.py` |
| Authorization dependencies | `backend/app/auth/dependencies.py` |
| API client | `frontend/src/services/api/client.ts` |
| Route guards | `frontend/src/access/components/RouteGuards.tsx` |
| Navigation | `frontend/src/layouts/AppLayout/nav-items.ts`, `frontend/src/layouts/AppLayout/AppSidebar.tsx` |
| Dashboard | `frontend/src/dashboard/pages/DashboardPage.tsx`, `frontend/src/dashboard/metrics.ts` |
| List UI pattern | `frontend/src/access/pages/AccessManagementPage.tsx` |
| Locale files | `frontend/src/i18n/locales/{en,hi,mr}/` |
| Backend tests | `backend/tests/` |
| Frontend tests | `frontend/src/**/*.test.tsx` |

### Database models and relationships

Tables created by `0001_auth_foundation`:

- `users` — email, Argon2id `password_hash`, name, language, active flag, session version.
- `roles` — seeded `ADMIN`, `TEACHER`, `STUDENT`.
- `permissions` and `role_permissions`.
- `user_roles`.
- `refresh_tokens`, `password_reset_tokens`.
- `audit_logs`.

Seeded permission keys: `users.read`, `users.create`, `users.update`, `users.delete`, `roles.read`, `roles.assign`, `features.read`.

`ADMIN` receives every seeded permission. `TEACHER` and `STUDENT` receive only `features.read`. There is no foreign key from a class register to `users`, because the register does not exist.

### How Sprint 1 authentication protects routes

- Login sets HttpOnly `access_token` and `refresh_token` cookies. Tokens are not returned in JSON and are not stored in `localStorage`.
- Unsafe methods require `X-CSRF-Token` to match the `csrf_token` cookie (`backend/app/core/csrf.py`).
- `get_current_user` rejects a missing, invalid, inactive, or stale session (`backend/app/auth/dependencies.py`).
- `require_permission` checks permission keys loaded from the database. It does not trust the role name by itself.
- The frontend `ProtectedRoute` sends anonymous users to `/login`. `PermissionRoute` sends signed-in users without the required permission to `/app/access-denied`.
- Dashboard route `/app` requires a session only. It does not require a roster permission.
- Access management requires `users.read`.

Navigation marks Students and Parents as coming soon. Those items are disabled buttons and do not navigate (`frontend/src/layouts/AppLayout/nav-items.ts`).

`loadDashboardMetrics` in `frontend/src/dashboard/metrics.ts` returns "unavailable" for Total Students, Total Batches, Today's Classes, and Pending Fees. It does not invent counts.

Reusable UI already in place: Material UI theme, `ErrorAlert`, `LoadingScreen`, `AppLayout` sidebar and account menu, access-management cards, confirmation dialogs, and English/Hindi/Marathi strings. The API client has `get`, `post`, and `patch`. It has no `delete` helper. List responses use `{ data, message }` with `items` and `total`.

## B. Feature status (before this implementation)

### Student management

#### 1. Student list page — Missing

Evidence: `AppRoutes` has no `/app/students` route. The sidebar item is `comingSoon: true` and has no `to`. No component renders a student table.

Files: `frontend/src/app/routes/AppRoutes.tsx`, `frontend/src/layouts/AppLayout/nav-items.ts`.

Missing work: a protected list with search, filters, pagination, and actions.

Recommended action: add the page inside `AppLayout` and enable the nav item for users with `students.read`.

#### 2. Add student form — Missing

Evidence: no student form component and no `POST` student route.

Missing work: required-name validation, optional class fields, submit lock, and server persistence.

Recommended action: add a create form that posts to the backend.

#### 3. Student details page — Missing

Evidence: no detail route or component.

Missing work: a read view for one student, including linked guardians, with a not-found state.

Recommended action: add `/app/students/:studentId`.

#### 4. Edit student information — Missing

Evidence: no update form and no student `PATCH` route.

Missing work: load current values, validate, save, and keep untouched fields.

Recommended action: add an edit form and a version check so a stale form does not overwrite a newer save.

#### 5. Delete or archive student — Missing

Evidence: no delete or archive API. Future batches, attendance, fees, and receipts are not built, but the sprint requires those future references to survive.

Missing work: a confirmed archive action. Hard delete would be unsafe once those modules exist, and there is no business rule that says a student row should disappear.

Recommended action: store `active`, `inactive`, and `archived`. Archive sets `archived` and does not remove the row.

#### 6. Student search and filtering — Missing

Evidence: user listing supports only `limit` and `offset` (`backend/app/users/router.py`). There is no student query.

Missing work: search by name or student code, filter by grade and status, sort, and paginate.

Recommended action: put those parameters on the list endpoint and the list page.

#### 7. Form validation — Missing

Evidence: auth forms validate email and password. Nothing validates a class register.

Files: `frontend/src/auth/pages/LoginPage.tsx`, `backend/app/main.py` (`_validation_details`).

Missing work: server-side checks for name, dates, grade, and optional parent contact, plus field messages in the form.

Recommended action: reject invalid bodies with the existing `{ error: { code, message, details } }` shape.

#### 8. Backend APIs and database persistence — Missing

Evidence: `backend/app/models.py` imports only auth, user, role, permission, and audit models. `create_app` does not mount a roster router.

Missing work: tables, migration, and authenticated CRUD.

Recommended action: add Alembic revision `0002` without editing `0001` or resetting data.

#### 9. Loading, empty, success, and error states — Partial

Evidence: `LoadingScreen`, `ErrorAlert`, and access-management notices exist. They are not used for students.

Files: `frontend/src/components/common/LoadingScreen.tsx`, `frontend/src/components/common/ErrorAlert.tsx`.

Missing work: student-page states. Reuse the existing components.

Recommended action: loading on first fetch, empty copy when the register is blank, inline errors, and a success alert after save or archive.

#### 10. Responsive layout — Partial

Evidence: `AppLayout` uses a permanent sidebar from the desktop breakpoint and a temporary drawer below it. Page padding is smaller on phones. Auth and access pages stack on narrow screens. No student layout exists.

Files: `frontend/src/layouts/AppLayout/AppLayout.tsx`, `frontend/src/layouts/AppLayout/useDesktopLayout.ts`.

Missing work: a student list and form that remain usable on a phone.

Recommended action: keep the Sprint 1 shell and stack form fields. Let the table scroll horizontally and hide secondary columns on small screens.

### Parent management

#### 1. Parent/guardian list or management view — Missing

Evidence: Parents is a disabled coming-soon nav item. No page or route exists.

Recommended action: add `/app/parents` behind `parents.read`.

#### 2. Add parent details — Missing

Evidence: no parent form or create API.

Recommended action: add a create form for name and optional contact fields.

#### 3. Edit parent details — Missing

Evidence: no parent update API or form.

Recommended action: add a patch form with the same version check used for students.

#### 4. View parent details — Missing

Evidence: no detail page.

Recommended action: show the saved contact fields and the linked students.

#### 5. Link parents to students — Missing

Evidence: no association table.

Recommended action: add a link table and explicit link and unlink actions. Do not copy a parent row onto each student.

#### 6. Multiple students for one parent or guardian — Missing

Evidence: no relationship to extend. A many-to-many link is the fit, because siblings share a guardian and one student can have more than one guardian. Sprint 1 does not already use a different relationship.

Recommended action: create `student_parents` with a unique pair of student and parent, and store the relationship on that pair.

#### 7. Search and filtering — Missing

Evidence: no parent query.

Recommended action: search by name, phone, or email, and filter by active or archived.

#### 8. Backend APIs and database persistence — Missing

Evidence: same as the student API gap.

Recommended action: add parent CRUD, link, and unlink on the existing FastAPI app and PostgreSQL database.

#### 9. Form validation and error handling — Missing

Evidence: email validation exists for login accounts. Phone validation does not. Parent email must not be treated as a unique login.

Recommended action: require the parent name, validate phone and email only when they are supplied, and allow the same phone on more than one parent.

#### 10. Responsive layout — Partial

Evidence: the signed-in shell is responsive. No parent screen exists.

Recommended action: follow the student screen layout.

## C. Remaining work checklist (initial)

1. **Schema and permissions** — Priority: High. Depends on the current Alembic chain. Add students, parents, and `student_parents` without dropping existing tables. Grant roster permissions to staff roles. Acceptance: `alembic upgrade head` applies `0002` on an existing database, and a `STUDENT` login cannot read the register.
2. **Student API** — Priority: High. Depends on the schema. Acceptance: create, list, get, update, and archive persist in PostgreSQL; invalid bodies return field errors; missing rows return 404; anonymous calls return 401.
3. **Parent API and links** — Priority: High. Depends on the student API for the association. Acceptance: one parent can link to several students, one student can link to several parents, and a second identical link is rejected.
4. **Student screens** — Priority: High. Depends on the student API, `ProtectedRoute`, and `AppLayout`. Acceptance: staff can add, search, filter, open, edit, and archive a student, and a refresh shows the saved row.
5. **Parent screens** — Priority: High. Depends on the parent API. Acceptance: staff can add, edit, open, and link parents from both the student and parent screens.
6. **Navigation and dashboard count** — Priority: Medium. Depends on `students.read` and a count query. Acceptance: Students and Parents navigate for permitted users. Total Students shows the active count. Batches, today's classes, and pending fees stay unavailable.
7. **Verification** — Priority: High. Depends on PostgreSQL, the backend virtualenv, and the frontend toolchain. Acceptance: pytest, ruff, mypy, vitest, eslint, and the production build are run, and any gap is recorded.

## D. Risks and blockers (initial)

- Student and parent work cannot be stored in the frontend. The API and a migration are required. PostgreSQL must already be configured through `backend/.env`. This audit did not print that value.
- Hard-deleting a student would fight later attendance, fee, and receipt rows. Archive is the safe operation even though those tables do not exist yet.
- Giving every signed-in user the register would expose guardian phone numbers to self-registered `STUDENT` accounts. Roster permissions have to be separate from `features.read`.
- `TEACHER` currently has only `features.read`. If the new permissions are added only to `ADMIN`, a teacher account still cannot open the register, and the access screen assigns roles rather than individual permissions. Granting the roster permissions to `TEACHER` is a product choice that changes the Sprint 1 teacher baseline. Leaving them off `ADMIN` would block the administrator who runs the class.
- The dashboard must not show a fabricated student total if the count request is forbidden or fails.
- `docker-compose.yml` publishes Postgres on port 5432, while `README.md` tells developers to use port 5433. Pointing `DATABASE_URL` at the wrong port blocks migrations and tests.
- Cookie `Secure` is an environment flag and is off for local HTTP. Production still needs `COOKIE_SECURE=true` and a long `JWT_SECRET`.
- The API client cannot send `DELETE` until a helper is added. Unlink can use that method.
- There is no critical missing dependency that should stop the sprint. The existing app, migration chain, and permission checks are enough to build on.

## E. Implementation record

Sections A–D above are the inspection before any Sprint 2 code. This section is the record after implementation and verification.

### Final Sprint 2 status: Complete

Student and parent management is implemented on the existing FastAPI app and React shell. Batches, timetable, Google Meet, attendance, fees, and receipts were not built.

### Features already complete before this sprint

- Login, registration, password reset, cookie sessions, CSRF, and permission checks.
- Dashboard shell with four summary cards. At the start of the sprint every card was an unavailable placeholder.
- Signed-in layout, language switcher, and access management.
- Disabled navigation entries for Students and Parents.

### Features implemented during this sprint

| Feature | Status now |
| --- | --- |
| Student list, search, grade and status filters, sort, pagination | Complete |
| Add student, with optional new or existing parent | Complete |
| Student details, including linked guardians | Complete |
| Edit student, with version check | Complete |
| Archive student (no hard delete) | Complete |
| Student validation, loading, empty, success, and error states | Complete |
| Parent list, search, status filter, sort, pagination | Complete |
| Add, edit, and view parent | Complete |
| Link and unlink, including siblings and multiple guardians | Complete |
| Duplicate link rejected | Complete |
| Server persistence, auth, and authorization | Complete |
| Dashboard active-student count | Complete |
| Responsive roster screens | Complete in the component layout and navigation test. A signed-in visual pass of the roster pages was not done. |

Gender is not collected. Phone numbers are not unique. Student codes are generated as `STU-000001` and upward. Archived rows stay in the database, and foreign keys use `ON DELETE RESTRICT`.

### Still partial or missing

Nothing in the Sprint 2 scope is missing. These items stay out of scope:

- Batch, timetable, Google Meet, attendance, fee, and receipt modules. Their navigation entries stay disabled. Their dashboard cards stay unavailable.
- Hard delete of a student or parent. Archive is the supported action.
- A signed-in click-through in the browser. No staff password was available, and no account or class-register row was created in the development database for this check.

### Blockers and configuration

No blocker remains. The development database already had Sprint 1 applied. Revision `0002_students_parents` was applied to it with `alembic upgrade head`. Existing accounts were not deleted.

On this machine the virtualenv is `backend/venv`. `README.md` documents `backend/.venv`. Use whichever folder exists.

The API process that was already listening on port 8000 had been started before these routes existed and was not running with reload. It was stopped and started again so `http://127.0.0.1:8000` serves the register. The frontend was already available at `http://localhost:5173`.

After the migration, sign in again or refresh `/api/v1/auth/me` so the sidebar receives `students.*` and `parents.*`. Permission checks on the API read the database on each request.

### Files created

- `backend/alembic/versions/0002_students_parents.py`
- `backend/app/common/fields.py`
- `backend/app/students/` — models, schemas, service, router
- `backend/app/parents/` — models, schemas, service, router
- `backend/tests/test_students_parents.py`
- `frontend/src/students/` — types, API, validation, list, form, detail, tests
- `frontend/src/parents/` — types, API, validation, list, form, detail, tests
- `frontend/src/roster/format.ts`
- `frontend/src/components/common/ConfirmDialog.tsx`
- `frontend/src/i18n/locales/{en,hi,mr}/students.json`
- `frontend/src/i18n/locales/{en,hi,mr}/parents.json`
- `docs/sprint-2-audit.md`

### Files modified

- `backend/app/main.py`, `backend/app/models.py`, `backend/app/common/exceptions.py`, `backend/app/core/logging.py`, `backend/tests/conftest.py`
- `frontend/src/app/routes/AppRoutes.tsx`
- `frontend/src/services/api/client.ts` — `delete` helper
- `frontend/src/layouts/AppLayout/nav-items.ts`, `AppSidebar.tsx`, `AppLayout.test.tsx`
- `frontend/src/dashboard/metrics.ts`
- `frontend/src/i18n/index.ts` and the English, Hindi, and Marathi `common`, `validation`, and `access` strings
- `README.md`

### Database migration

From `backend/`, with the project virtualenv:

```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
```

`README.md` uses `.\.venv\Scripts\python.exe` for the same command. Revision `0002_students_parents` creates `students`, `parents`, `student_parents`, and `student_code_seq`, then grants the eight roster permissions to `ADMIN` and `TEACHER`. It does not drop or rewrite Sprint 1 tables. Downgrade removes only those new objects.

This was run against the configured development database. The test suite uses `onlinetution_test` and migrates that database itself.

### Tests and build results

| Check | Result |
| --- | --- |
| `pytest` | 35 passed, 4 existing deprecation warnings, 14.90s |
| `ruff check app tests` | All checks passed |
| `mypy app` | Success, 56 source files |
| `npm test` | 11 files, 37 tests passed |
| `npm run lint` | Passed |
| `npm run build` | `tsc --noEmit` and Vite succeeded. Vite warned that the JS chunk is 714.89 kB, above 500 kB. The build still exited 0. |

Backend coverage in `backend/tests/test_students_parents.py`:

- Anonymous register calls return 401.
- A `STUDENT` login cannot read or change the register.
- Create, view, edit, search, and archive a student.
- One parent linked to two students, two guardians linked to one student, duplicate link rejected.
- Archived records cannot be linked, and archive does not delete the row.
- A teacher can manage students. The summary counts only active students.
- Creating a student can also create and link a parent.

Frontend tests cover the student list, empty and error states, search, required name, save, server field error, missing student, parent phone validation, save, dashboard count and unavailable cards, and sidebar links for a permitted user.

### What was checked in the running app

- `GET /api/v1/students`, `GET /api/v1/parents`, `GET /api/v1/students/summary`, and `GET /api/v1/auth/me` return 401 without a session.
- OpenAPI at `/api/openapi.json` lists the student and parent operations.
- `http://localhost:5173/` loads the sign-in screen.
- Opening `/app/students` and `/app/parents` while signed out returns to `/login`.
- Submitting sign-in with empty fields shows "This field is required." on email and password.
- The sign-in card remains usable at a 390px-wide layout.
- The Vite dev server is serving the new student and parent route modules.

A signed-in walkthrough of add, edit, link, archive, and the dashboard count was not performed. Those paths are covered by the automated tests above. No development account was created or changed, and no class-register row was inserted into `onlinetution`.

### Manual test steps

1. From `backend/`, run `.\venv\Scripts\python.exe -m alembic upgrade head` if this database has not already applied `0002_students_parents`.
2. Start the API with `.\venv\Scripts\python.exe -m uvicorn app.main:app --reload` and the frontend with `npm run dev`.
3. Open `http://localhost:5173` and sign in as an administrator or teacher.
4. Open Students. Confirm the empty state, then add a student with a name. Refresh and confirm the row is still there.
5. Submit the form with an empty name and confirm the field message. Search by name and filter by class and status.
6. Open the student, edit a field, and save. Archive from the list and confirm the dialog. The row leaves the default list and remains under the archived filter.
7. Add a parent. Link that parent to two students, and link a second guardian to one of them. Repeat a link and confirm it is rejected.
8. Confirm the dashboard Total Students card matches the number of active students, and that batches, today's classes, and pending fees still say unavailable.
9. Sign in as a self-registered student and confirm Students and Parents are not in the sidebar and the API returns 403.

### Remaining tasks

None for Sprint 2. Later sprints own batches, timetable, Google Meet, attendance, fees, and receipts.
