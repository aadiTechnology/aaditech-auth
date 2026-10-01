"""Structured logging that redacts credential fields."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "new_password",
        "confirm_password",
        "old_password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "csrf_token",
        "authorization",
        "cookie",
        "jwt",
        "jwt_secret",
        "smtp_password",
    }
)

_STANDARD_ATTRS = set(logging.makeLogRecord({}).__dict__.keys()) | {"message", "asctime"}


class RedactionFilter(logging.Filter):
    """Replace sensitive log record attributes before they are emitted."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, dict):
            record.args = {
                key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS else value
                for key, value in record.args.items()
            }
        for key in list(record.__dict__.keys()):
            if key.lower() in SENSITIVE_KEYS:
                setattr(record, key, "[REDACTED]")
        return True


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root = logging.getLogger()
    if any(getattr(handler, "_onlinetution", False) for handler in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactionFilter())
    handler._onlinetution = True  # type: ignore[attr-defined]
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def log_event(logger: logging.Logger, event: str, **fields: object) -> None:
    logger.info(event, extra={"event": event, **fields})
