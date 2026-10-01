# Online Tuition authentication foundation

This repository contains the authentication and role-based access foundation for Online Tuition. It does not include classes, attendance, fees, or other ERP features.

## Applications

- `backend/` — FastAPI, PostgreSQL, SQLAlchemy, Alembic
- `frontend/` — React, TypeScript, Material UI, i18next

## Prerequisites

- Python 3.12+
- Node.js 22+
- PostgreSQL listening on `localhost:5433`

## Start the database

Create a database named `onlinetution` on the local PostgreSQL server. Put the connection string in `backend/.env` as `DATABASE_URL`. The password is stored only in that file, which is gitignored. `@` in a password must be written as `%40` in the URL.

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.cli.create_admin --email admin@example.com --full-name "System Admin"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The admin command asks for the password without echoing it. Omit `--password` so the secret is not stored in shell history. The command creates only the first administrator. After that, role changes are made by an authenticated administrator.

API documentation is at `http://localhost:8000/api/docs`.

### Password reset mail in development

`EMAIL_BACKEND=file` writes reset messages to `backend/var/outbox/`. Those files contain reset links, are gitignored, and are not written to the application log. Open the latest file and use its link. Configure `SMTP_HOST` and set `EMAIL_BACKEND=smtp` when a real mailbox is available.

## Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

The app runs at `http://localhost:5173`. Open that host, not `127.0.0.1`, when `VITE_API_BASE_URL` uses `localhost`. Browsers treat those names as different sites, so the HttpOnly session cookies are not sent across them while `COOKIE_SAMESITE=lax`.

## Authentication

- Public registration always creates a `STUDENT` account. The server ignores any role sent by the client.
- Login sets an HttpOnly access cookie and a revocable HttpOnly refresh cookie. Tokens are not returned in JSON and are not stored in `localStorage`.
- Unsafe requests send `X-CSRF-Token`, matching the CSRF cookie from `GET /api/v1/auth/csrf`.
- Refresh tokens rotate. Reuse of a revoked refresh token revokes that user's sessions.
- Password reset tokens are random, stored only as a SHA-256 hash, expire, and cannot be reused. A successful reset increments the session version and revokes refresh tokens.
- Passwords are hashed with Argon2id.

Authorization is permission-based. `ADMIN`, `TEACHER`, and `STUDENT` are database roles. Administrators receive the initial permission set. Teachers and students receive only `features.read` until an administrator changes their role. A user cannot change their own role or status.

## Checks

Backend, from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m mypy app
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Frontend, from `frontend/`:

```powershell
npm test
npm run lint
npm run build
```

## Environment

Backend variables are documented in `backend/.env.example`. Frontend variables are `VITE_API_BASE_URL` and `VITE_DEFAULT_LANGUAGE`.

Do not commit `.env` files, passwords, JWT secrets, or database credentials.
