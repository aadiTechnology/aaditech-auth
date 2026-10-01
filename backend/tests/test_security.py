"""Security-focused unit checks."""

import logging

from app.core.logging import JsonFormatter, RedactionFilter
from app.core.password_policy import (
    SPECIAL_PATTERN,
    current_password_policy,
    password_rule_failures,
)
from app.core.rate_limit import InMemoryRateLimiter
from app.core.security import hash_password
from app.main import app
from fastapi.testclient import TestClient


def test_password_hash_uses_argon2id():
    hashed = hash_password("ValidPass1!")
    assert hashed.startswith("$argon2id$")


def test_password_policy_matches_the_published_rules():
    policy = current_password_policy()
    assert policy.min_length >= 8
    assert policy.require_uppercase
    assert policy.require_lowercase
    assert policy.require_number
    assert policy.require_special
    assert SPECIAL_PATTERN == r"[^A-Za-z0-9]"
    assert password_rule_failures("ValidPass1!") == []
    assert password_rule_failures("validpass1!")[0].code == "MISSING_UPPERCASE"


def test_rate_limiter_blocks_after_the_limit():
    limiter = InMemoryRateLimiter()
    limiter.check("login:test", 2, 60)
    limiter.check("login:test", 2, 60)
    try:
        limiter.check("login:test", 2, 60)
        raised = False
    except Exception as exc:  # noqa: BLE001
        raised = True
        assert exc.status_code == 429
        assert exc.headers["Retry-After"]
    assert raised


def test_log_formatter_redacts_password_fields():
    record = logging.LogRecord("app", logging.INFO, __file__, 1, "authentication_failure", (), None)
    record.password = "ValidPass1!"
    record.token = "raw-token"
    assert RedactionFilter().filter(record)
    formatted = JsonFormatter().format(record)
    assert "ValidPass1!" not in formatted
    assert "raw-token" not in formatted
    assert "[REDACTED]" in formatted


def test_openapi_documents_auth_and_access_routes():
    client = TestClient(app)
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in (
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/refresh",
        "/api/v1/auth/me",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/users",
        "/api/v1/users/{user_id}/role",
        "/api/v1/users/{user_id}/status",
        "/api/v1/roles",
        "/api/v1/permissions",
    ):
        assert path in paths
        operation = next(iter(paths[path].values()))
        assert operation["summary"]
        assert operation["description"]
