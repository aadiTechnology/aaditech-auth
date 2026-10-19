# Sprint 1 audit — Authentication and dashboard foundation

This document records the inspection performed before Sprint 1 implementation, then the work completed afterward. The initial findings below describe the repository as it existed before the dashboard changes in this sprint.

Secret values from `.env` files are not included.

## A. Project overview (initial audit)

### Technologies

- Frontend: React 19, TypeScript, Vite 7, Material UI 7, Emotion, React Router 7, i18next (English, Marathi, Hindi), Vitest, Testing Library.
- Backend: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (psycopg), Pydantic Settings, PyJWT, Argon2id.
- Local database option: Docker Compose service `postgres` (Postgres 16) plus a documented local PostgreSQL on port 5433.

### Entry points

- Frontend bootstrap: `frontend/src/main.tsx`, `frontend/src/app/App.tsx`, `frontend/src/app/routes/AppRoutes.tsx`.
- Frontend session owner: `frontend/src/store/auth-context.tsx`.
- API client: `frontend/src/services/api/client.ts`.
- Backend application: `backend/app/main.py`.
- Auth HTTP API: `backend/app/auth/router.py`.
- Schema migration: `backend/alembic/versions/0001_auth_foundation.py`.

### Database and authentication architecture

PostgreSQL stores users, roles, permissions, refresh sessions, password-reset tokens, and audit events. Passwords are stored as Argon2id hashes on `users.password_hash`. Login does not return tokens in JSON. The API sets HttpOnly `access_token` and `refresh_token` cookies, plus an HttpOnly CSRF cookie. Unsafe requests must send `X-CSRF-Token`. Refresh tokens rotate, and reuse of a revoked refresh token revokes that user's sessions. Authorization is permission-based (`ADMIN`, `TEACHER`, `STUDENT`).

There is no students, batches, timetable, attendance, fees, or receipts schema.

### How to run locally

Prerequisites from `README.md`: Python 3.12+, Node.js 22+, PostgreSQL.

Backend, from `backend/`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.cli.create_admin --email admin@example.com --full-name "System Admin"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The admin command prompts for a password. API docs: `http://localhost:8000/api/docs`.

Frontend, from `frontend/`:

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

Open `http://localhost:5173` (not `127.0.0.1`) so session cookies match `COOKIE_SAMESITE=lax`.

Configuration names, without values: `DATABASE_URL`, `JWT_SECRET`, `COOKIE_SECURE`, `COOKIE_SAMESITE`, `CORS_ORIGINS`, `VITE_API_BASE_URL`, `VITE_DEFAULT_LANGUAGE`. Examples live in `backend/.env.example` and `frontend/.env.example`.

## B. Feature status (before this implementation)

### 1. Login UI — Complete

Evidence: `LoginPage` renders an email field, password field, remember-me option, submit button, forgot-password link, and register link inside `AuthLayout`. `PasswordField` toggles visibility.

Files: `frontend/src/auth/pages/LoginPage.tsx`, `frontend/src/auth/components/PasswordField.tsx`, `frontend/src/layouts/AuthLayout/AuthLayout.tsx`.

Gap: the card is functional and responsive, but the shell does not show the application name. That is a presentation gap, not a missing form.

Next action: keep the form and add the existing application name to the auth shell.

### 2. Login form validation — Complete

Evidence: empty email, invalid email, and empty password set field messages before any request. Covered by `shows a login validation error` in `frontend/src/auth/pages/AuthPages.test.tsx`. Server field errors are mapped in `frontend/src/auth/validation/errors.ts`.

Files: `frontend/src/auth/pages/LoginPage.tsx`, `frontend/src/auth/validation/password.ts`, `frontend/src/i18n/locales/en/validation.json`.

Next action: none for Sprint 1.

### 3. Authentication backend/API — Complete

Evidence: `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `POST /api/v1/auth/refresh`, `GET /api/v1/auth/me`, registration, and password reset exist. Login rate limiting is wired. Tests in `backend/tests/test_login.py` cover success, invalid credentials, inactive accounts, logout, and refresh rotation.

Files: `backend/app/auth/router.py`, `backend/app/auth/service.py`, `backend/app/auth/dependencies.py`.

Next action: run the existing backend suite. Do not add a second auth system.

### 4. Secure password handling — Complete

Evidence: `hash_password` uses Argon2id. Login compares hashes and uses a dummy hash for unknown users. Tests assert the password and `password_hash` are not in the response or logs.

Files: `backend/app/core/security.py`, `backend/app/users/models.py`, `backend/tests/test_login.py`.

Next action: none.

### 5. Login success and failure handling — Complete

Evidence: success stores the profile and navigates to `/app`. `INVALID_CREDENTIALS` and network failures use translated messages from `common.errors`. Inactive accounts return `ACCOUNT_INACTIVE`.

Files: `frontend/src/store/auth-context.tsx`, `frontend/src/auth/validation/errors.ts`, `frontend/src/i18n/locales/en/common.json`.

Next action: none.

### 6. Logout functionality — Partial

Evidence: the API revokes the refresh token and clears cookies (`backend/app/auth/router.py`, `backend/tests/test_login.py`). The header button calls `logout()` and navigates to `/login` (`frontend/src/layouts/AppLayout/AppLayout.tsx`).

Gap: if `POST /api/v1/auth/logout` throws, `auth-context.tsx` does not clear local user state, and the layout does not navigate.

Next action: clear local auth state after a logout attempt, including when the request fails.

### 7. Protected dashboard routes — Complete

Evidence: `ProtectedRoute` shows a loading screen, then redirects unauthenticated users to `/login`. `GuestRoute` sends an authenticated user to `/app`. Permission routes send unauthorized users to `/app/access-denied`. Tests in `frontend/src/access/routes/RouteGuards.test.tsx` cover anonymous redirect and authenticated access. `GET /api/v1/auth/me` returns 401 without a session.

Files: `frontend/src/access/components/RouteGuards.tsx`, `frontend/src/app/routes/AppRoutes.tsx`, `backend/app/auth/dependencies.py`.

Next action: keep these guards. Do not replace them.

### 8. Session or token management — Complete

Evidence: access JWT in an HttpOnly cookie, revocable refresh cookie scoped to `/api/v1/auth`, CSRF double-submit, refresh-on-401 in the API client, and an unauthorized handler that marks the client unauthenticated.

Files: `backend/app/auth/cookies.py`, `backend/app/core/security.py`, `backend/app/core/csrf.py`, `frontend/src/services/api/client.ts`.

Gap: cookie `Secure` is an environment flag and is off for local HTTP, which is appropriate for development. Production must set `COOKIE_SECURE=true`.

Next action: none in code. Document the production cookie flag.

### 9. Main dashboard layout — Missing

Evidence: after login, `/app` renders `HomePage`, which is a welcome line, the user's name, and roles. There is no coaching dashboard.

Files: `frontend/src/access/pages/HomePage.tsx`, `frontend/src/layouts/AppLayout/AppLayout.tsx`.

Next action: replace the welcome-only landing page with a dashboard content area inside a sidebar shell.

### 10. Sidebar and navigation — Missing

Evidence: navigation is a horizontal row with Home and, when permitted, Access management. Students, Parents, Batches, Timetable, Google Meet, Attendance, Fees, and Receipts are absent. No coming-soon state exists.

Files: `frontend/src/layouts/AppLayout/AppLayout.tsx`, `frontend/src/i18n/locales/en/navigation.json`.

Next action: add a sidebar. Link Dashboard. Mark unimplemented modules as coming soon. Keep the existing access-management route behind `users.read`.

### 11. Navbar or header — Partial

Evidence: a Material UI app bar shows the application name, language select, and logout button. It does not show the current page title or an account menu.

Files: `frontend/src/layouts/AppLayout/AppLayout.tsx`.

Next action: move the application name into the sidebar and use the header for the page title, language, and account menu. Logout stays a real logout.

### 12. Dashboard summary cards — Missing

Evidence: no summary card component and no students, batches, classes, or fees endpoints. `backend/app/main.py` only mounts auth, users, roles, and permissions.

Next action: add reusable cards for Total Students, Total Batches, Today's Classes, and Pending Fees. Show "Not available yet". Do not invent counts.

### 13. Responsive layout — Partial

Evidence: auth pages use a full-width card up to 440px with page padding (`AuthLayout`). The signed-in toolbar wraps. There is no collapsing navigation.

Files: `frontend/src/layouts/AuthLayout/AuthLayout.tsx`, `frontend/src/theme/theme.ts`.

Next action: permanent sidebar from the `md` breakpoint up, and a menu button with a temporary drawer below that.

### 14. Loading, empty, and error states — Partial

Evidence: route guards and auth bootstrap use `LoadingScreen`. Forms use `ErrorAlert` and a submitting label. Access management has its own loading, empty, and error states. The future dashboard metrics have none.

Files: `frontend/src/components/common/LoadingScreen.tsx`, `frontend/src/components/common/ErrorAlert.tsx`, `frontend/src/access/pages/AccessManagementPage.tsx`.

Next action: support loading, empty, error, ready, and unavailable states on summary cards.

### 15. Basic tests and application build — Partial

Evidence: frontend scripts are `npm test`, `npm run lint`, `npm run build`, and `npm run typecheck`. Backend scripts are pytest, ruff, and mypy, documented in `README.md`. Auth and route-guard tests exist. No dashboard tests exist. This audit had not executed the suites yet.

Files: `frontend/package.json`, `backend/pyproject.toml`, `frontend/src/auth/pages/AuthPages.test.tsx`, `backend/tests/test_login.py`.

Next action: run the suites after implementation and record the actual results.

## C. Remaining work identified by the audit

1. **Dashboard shell** — Priority: High. Depends on the existing `ProtectedRoute` and `AppLayout`. Files: `frontend/src/layouts/AppLayout/AppLayout.tsx`, new sidebar module, navigation strings. Acceptance: signed-in users see a sidebar, header title, account menu, and main content. Anonymous users still land on the login page.
2. **Coming-soon navigation** — Priority: High. Depends on the sidebar. Files: navigation config and `en`/`hi`/`mr` locale files. Acceptance: Dashboard opens `/app`. The eight future modules are visible and disabled, with a coming-soon label, and do not navigate. Access management remains available only with `users.read`.
3. **Summary cards** — Priority: High. No backend dependency, because those APIs do not exist. Files: new dashboard module and `HomePage` or its route. Acceptance: four cards render "Not available yet" and never show a fabricated number. Loading, empty, and error presentations exist for later data sources.
4. **Logout resilience** — Priority: Medium. Depends on the current auth context. File: `frontend/src/store/auth-context.tsx`. Acceptance: a failed logout request still clears local authenticated state and the user is sent to `/login`.
5. **Auth shell label and focus** — Priority: Low. Files: `AuthLayout`, login remember-me control, theme. Acceptance: the login screen shows the application name, and the remember-me control has a visible focus style.
6. **Verification** — Priority: High. Depends on Node, Python, and PostgreSQL being available. Acceptance: existing tests, lint, typecheck, and production build are run, and gaps are documented when a service is unavailable.

## D. Risks and blockers (initial)

- Dashboard counts cannot be live. Students, batches, timetable, and fees are out of scope and have no API. Placeholders are required.
- Backend tests need PostgreSQL and `backend/.env` with `DATABASE_URL`. The test suite rewrites the database name to `onlinetution_test` and does not print the URL.
- Production deployments must set a long `JWT_SECRET` and `COOKIE_SECURE=true`. Local examples intentionally use development defaults.
- `docker-compose.yml` publishes Postgres on port 5432, while the README tells developers to use port 5433. Local setup can point at the wrong port if those are mixed up.
- Empty untracked files `frontend/If` and `frontend/You` are not part of the application.
- Password-reset email in development writes files under `backend/var/outbox/` when `EMAIL_BACKEND=file`. That does not block login.

## Features already completed before this implementation

Login UI, client and server validation, Argon2id passwords, cookie sessions, CSRF, refresh rotation, protected routes, permission checks, logout API, translated auth errors, and auth/authorization tests were already in the repository.

## Implementation update

The initial findings above were not rewritten. This section records what changed afterward.

### Completed during this implementation

- Auth shell shows the application name. Remember me uses the existing Material UI checkbox, with a visible focus ring.
- Logout still calls `POST /api/v1/auth/logout`. If that request fails, local auth state is cleared and the user is sent to the login page.
- Signed-in layout is a sidebar plus header. The sidebar shows Online Tuition and the module list. The header shows the page title, language selector, and an account menu whose Log out action performs the real logout.
- Dashboard opens `/app`. Students, Parents, Batches, Timetable, Google Meet, Attendance, Fees, and Receipts are visible, disabled, and labelled "Coming soon". They are not routes.
- Access management stays on `/app/admin/access` and still requires `users.read`.
- Below the `md` width (900px), the sidebar is a temporary drawer opened from the header menu button.
- The dashboard shows Total Students, Total Batches, Today's Classes, and Pending Fees. The current data source returns `unavailable` for each, so the UI says "Not available yet" and does not show a number. `SummaryCard` also renders loading, empty, error, and ready states for later sprints.
- English, Marathi, and Hindi strings were added for the new navigation and dashboard copy.

### Still partial

- Summary numbers are placeholders. Students, batches, timetable, and fees APIs do not exist. That is expected for Sprint 1.
- A signed-in walkthrough of the new dashboard was not done in the browser. No password was available, and no account was created or changed.

### Still missing

No Sprint 1 login or dashboard requirement is unimplemented. Later modules (students through receipts) are intentionally not built.

### Blockers and required configuration

- Real dashboard counts need the later module APIs.
- Production must set a long `JWT_SECRET` and `COOKIE_SECURE=true`. Local HTTP keeps secure cookies off.
- Backend tests need PostgreSQL and `DATABASE_URL` in `backend/.env`. The suite uses the database name `onlinetution_test`.
- `docker-compose.yml` publishes Postgres on port 5432. The README uses port 5433 for a local server. Point `DATABASE_URL` at the server that is actually running.

### Files created

- `docs/sprint-1-audit.md`
- `frontend/src/dashboard/metrics.ts`
- `frontend/src/dashboard/components/SummaryCard.tsx`
- `frontend/src/dashboard/components/SummaryCard.test.tsx`
- `frontend/src/dashboard/pages/DashboardPage.tsx`
- `frontend/src/dashboard/pages/DashboardPage.test.tsx`
- `frontend/src/layouts/AppLayout/nav-items.ts`
- `frontend/src/layouts/AppLayout/AppSidebar.tsx`
- `frontend/src/layouts/AppLayout/useDesktopLayout.ts`
- `frontend/src/layouts/AppLayout/AppLayout.test.tsx`
- `frontend/src/store/auth-context.test.tsx`
- `frontend/src/i18n/locales/en/dashboard.json`
- `frontend/src/i18n/locales/hi/dashboard.json`
- `frontend/src/i18n/locales/mr/dashboard.json`

### Files modified

- `frontend/src/layouts/AppLayout/AppLayout.tsx`
- `frontend/src/layouts/AuthLayout/AuthLayout.tsx`
- `frontend/src/app/routes/AppRoutes.tsx`
- `frontend/src/access/pages/HomePage.tsx` (now re-exports the dashboard page)
- `frontend/src/access/pages/AccessDeniedPage.tsx`
- `frontend/src/access/pages/AccessManagementPage.tsx`
- `frontend/src/components/common/LoadingScreen.tsx`
- `frontend/src/auth/pages/LoginPage.tsx`
- `frontend/src/store/auth-context.tsx`
- `frontend/src/theme/theme.ts`
- `frontend/src/i18n/index.ts`
- `frontend/src/i18n/locales/en/navigation.json`
- `frontend/src/i18n/locales/hi/navigation.json`
- `frontend/src/i18n/locales/mr/navigation.json`

### Tests and commands

Run from `frontend/` after the other commands had finished:

- `npm test` — 6 files, 22 tests, all passed.
- `npm run lint` — passed.
- `npm run build` (`tsc --noEmit` and Vite production build) — passed. Vite warned that the main bundle is larger than 500 kB. That warning was already likely from the Material UI bundle; no chunk splitting was added.

An earlier `npm test` run at the same time as lint, build, and backend tests timed out once in the existing registration test (`blocks registration when passwords do not match`, 5000ms limit). That test passed in 3254ms when the suite was run alone. It was not changed.

Run from `backend/` with the existing `venv`:

- `.\venv\Scripts\python.exe -m pytest` — 28 passed.
- `.\venv\Scripts\python.exe -m ruff check app tests` — passed.
- `.\venv\Scripts\python.exe -m mypy app` — passed.

Browser, against the frontend already running at `http://localhost:5173` and the API at `http://localhost:8000`:

- Login screen renders with the application name, email, password show/hide, remember me, and sign-in button.
- Empty submit shows "This field is required." on email and password.
- Submit shows "Please wait" and disables the fields.
- An unknown account shows "Invalid email or password." The API logged `authentication_failure` / `invalid_credentials`.
- Opening `/app` while signed out returns to `/login`.
- Remember me can be checked. Show password switches to Hide password.
- The login card remains usable at a 390px-wide viewport.

Not verified in the browser: successful login, the signed-in sidebar, coming-soon items, account-menu logout, or the summary cards. Those paths are covered by the frontend unit tests with a mocked session, and login/logout success is covered by `backend/tests/test_login.py`.

### Manual testing

1. Start PostgreSQL, apply migrations, and start the API from `backend/` with `.\venv\Scripts\python.exe -m uvicorn app.main:app --reload`.
2. From `frontend/`, run `npm run dev` and open `http://localhost:5173`.
3. Submit the login form empty, then with a bad email format, then with an unknown email. Confirm the field and credential messages.
4. Sign in with an existing account. Confirm `/app` shows the sidebar, the four "Not available yet" cards, and no numeric counts.
5. Confirm Students through Receipts cannot be opened. Open Access management only with an administrator.
6. Narrow the window below 900px, open and close the menu, then use Account menu → Log out. Confirm `/app` sends you back to sign in.
7. Repeat the login screen in Marathi and Hindi.

### Sprint 1 completion status

**Complete** for the Sprint 1 authentication and dashboard foundation.

Live student, batch, class, and fee counts are intentionally unavailable until those modules exist. The signed-in dashboard was not opened in the browser during this session.
