"""Authentication request and response schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

SUPPORTED_LANGUAGES = ("en", "mr", "hi")


def normalize_email(value: str) -> str:
    return value.strip().lower()


class RegisterRequest(BaseModel):
    """Public registration. Any role field sent by the client is ignored."""

    model_config = ConfigDict(extra="ignore")

    full_name: str = Field(min_length=1, max_length=200, description="Person's full name.")
    email: EmailStr = Field(description="Email address. Stored lowercase and trimmed.")
    password: str = Field(min_length=1, max_length=128, description="Password checked against the server policy.")
    confirm_password: str = Field(min_length=1, max_length=128)
    preferred_language: Literal["en", "mr", "hi"] = "en"

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        return cleaned

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_email(value)
        return value


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_email(value)
        return value


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_email(value)
        return value


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    token: str = Field(min_length=20, max_length=512)
    new_password: str = Field(min_length=1, max_length=128)
    confirm_password: str = Field(min_length=1, max_length=128)


class RegisteredUser(BaseModel):
    id: str
    full_name: str
    email: str
    preferred_language: str
    roles: list[str]


class UserProfile(BaseModel):
    id: str
    full_name: str
    email: str
    preferred_language: str
    is_active: bool
    email_verified: bool
    roles: list[str]
    permissions: list[str]
