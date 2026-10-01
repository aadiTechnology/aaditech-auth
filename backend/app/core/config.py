"""Application settings loaded from the environment."""

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_JWT_SECRETS = frozenset(
    {
        "change-me",
        "change-me-to-a-long-random-string-at-least-32-chars",
    }
)


class Settings(BaseSettings):
    """Runtime configuration. Secrets are never given production defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str
    jwt_secret: str = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=90)
    remember_me_expire_days: int = Field(default=30, ge=1, le=365)
    password_reset_token_expiry_minutes: int = Field(default=30, ge=5, le=1440)
    cors_origins: str
    frontend_base_url: str = "http://localhost:5173"
    cookie_secure: bool | None = None
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    password_min_length: int = Field(default=8, ge=8, le=128)
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_number: bool = True
    password_require_special: bool = True

    rate_limit_enabled: bool = True
    login_rate_limit: int = Field(default=10, ge=1)
    login_rate_window_seconds: int = Field(default=900, ge=1)
    forgot_password_rate_limit: int = Field(default=5, ge=1)
    forgot_password_rate_window_seconds: int = Field(default=900, ge=1)
    register_rate_limit: int = Field(default=5, ge=1)
    register_rate_window_seconds: int = Field(default=3600, ge=1)
    reset_password_rate_limit: int = Field(default=10, ge=1)
    reset_password_rate_window_seconds: int = Field(default=900, ge=1)

    email_backend: Literal["file", "smtp", "memory"] | None = None
    email_outbox_dir: str = "var/outbox"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@localhost"
    smtp_use_tls: bool = True

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        parts = [part.strip().rstrip("/") for part in value.split(",") if part.strip()]
        if not parts:
            raise ValueError("CORS_ORIGINS must list at least one origin")
        if any(part == "*" for part in parts):
            raise ValueError("CORS_ORIGINS must not contain a wildcard")
        return ",".join(parts)

    @field_validator("frontend_base_url")
    @classmethod
    def strip_frontend_url(cls, value: str) -> str:
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_security_settings(self) -> Self:
        if self.email_backend is None:
            if self.app_env == "production":
                self.email_backend = "smtp"
            elif self.app_env == "test":
                self.email_backend = "memory"
            else:
                self.email_backend = "file"
        secure = self.app_env == "production" if self.cookie_secure is None else self.cookie_secure
        if self.cookie_samesite == "none" and not secure:
            raise ValueError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true")
        if self.app_env == "production" and self.jwt_secret in INSECURE_JWT_SECRETS:
            raise ValueError("JWT_SECRET must be replaced before running in production")
        if self.app_env == "production" and self.email_backend == "smtp" and not self.smtp_host:
            raise ValueError("SMTP_HOST is required when EMAIL_BACKEND=smtp")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin for origin in self.cors_origins.split(",") if origin]

    @property
    def use_secure_cookies(self) -> bool:
        if self.cookie_secure is None:
            return self.app_env == "production"
        return self.cookie_secure


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
