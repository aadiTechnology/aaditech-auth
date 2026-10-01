"""Test environment must be configured before the application is imported."""

import os
import time
from urllib.parse import urlsplit, urlunsplit


def _database_url(database_name: str) -> str:
    """Use the local credentials from .env and select the named database."""
    database_url = ""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    with open(env_path, encoding="utf-8") as env_file:
        for line in env_file:
            if line.startswith("DATABASE_URL="):
                database_url = line.split("=", 1)[1].strip()
                break
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing from backend/.env")
    parts = urlsplit(database_url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{database_name}", "", ""))


os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = _database_url("onlinetution_test")
os.environ["JWT_SECRET"] = "test-jwt-secret-must-be-at-least-32"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["COOKIE_SECURE"] = "false"
os.environ["COOKIE_SAMESITE"] = "lax"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["EMAIL_BACKEND"] = "memory"
os.environ["FRONTEND_BASE_URL"] = "http://localhost:5173"
os.environ["PASSWORD_RESET_TOKEN_EXPIRY_MINUTES"] = "30"

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text

get_settings.cache_clear()


def _ensure_test_database() -> None:
    last_error: Exception | None = None
    for _ in range(30):
        try:
            admin_url = _database_url("postgres").replace("postgresql+psycopg://", "postgresql://", 1)
            with psycopg.connect(admin_url, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'onlinetution_test'")
                    if cur.fetchone() is None:
                        cur.execute("CREATE DATABASE onlinetution_test")
            return
        except Exception as exc:  # noqa: BLE001 - retry while PostgreSQL starts
            last_error = exc
            time.sleep(1)
    raise RuntimeError("PostgreSQL is not available for tests") from last_error


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    if not os.environ["DATABASE_URL"].endswith("/onlinetution_test"):
        raise RuntimeError("Refusing to run tests against a non-test database")
    _ensure_test_database()
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
def clean_database() -> None:
    get_settings().rate_limit_enabled = False
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE audit_logs, password_reset_tokens, refresh_tokens, "
                "user_roles, users CASCADE"
            )
        )
    engine.dispose()
    from app.core.rate_limit import limiter
    from app.email.sender import get_memory_sender

    limiter.reset()
    get_memory_sender().clear()
    yield
    get_memory_sender().clear()


@pytest.fixture
async def client():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
