"""Configurable password policy. The API is the authority for these rules."""

import re
from dataclasses import dataclass

from app.core.config import get_settings

SPECIAL_PATTERN = r"[^A-Za-z0-9]"
_SPECIAL = re.compile(SPECIAL_PATTERN)


@dataclass(frozen=True)
class PasswordRuleFailure:
    code: str
    message: str


@dataclass(frozen=True)
class PasswordPolicy:
    min_length: int
    require_uppercase: bool
    require_lowercase: bool
    require_number: bool
    require_special: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "min_length": self.min_length,
            "require_uppercase": self.require_uppercase,
            "require_lowercase": self.require_lowercase,
            "require_number": self.require_number,
            "require_special": self.require_special,
            "special_pattern": SPECIAL_PATTERN,
        }


def current_password_policy() -> PasswordPolicy:
    settings = get_settings()
    return PasswordPolicy(
        min_length=settings.password_min_length,
        require_uppercase=settings.password_require_uppercase,
        require_lowercase=settings.password_require_lowercase,
        require_number=settings.password_require_number,
        require_special=settings.password_require_special,
    )


def password_rule_failures(password: str, policy: PasswordPolicy | None = None) -> list[PasswordRuleFailure]:
    active = policy or current_password_policy()
    failures: list[PasswordRuleFailure] = []
    if "\x00" in password:
        failures.append(
            PasswordRuleFailure("INVALID_CHARACTER", "Password contains an invalid character.")
        )
    if len(password) < active.min_length:
        failures.append(
            PasswordRuleFailure(
                "TOO_SHORT",
                f"Password must be at least {active.min_length} characters.",
            )
        )
    if len(password) > 128:
        failures.append(PasswordRuleFailure("TOO_LONG", "Password must be at most 128 characters."))
    if active.require_uppercase and not re.search(r"[A-Z]", password):
        failures.append(
            PasswordRuleFailure("MISSING_UPPERCASE", "Password must contain an uppercase letter.")
        )
    if active.require_lowercase and not re.search(r"[a-z]", password):
        failures.append(
            PasswordRuleFailure("MISSING_LOWERCASE", "Password must contain a lowercase letter.")
        )
    if active.require_number and not re.search(r"[0-9]", password):
        failures.append(PasswordRuleFailure("MISSING_NUMBER", "Password must contain a number."))
    if active.require_special and _SPECIAL.search(password) is None:
        failures.append(
            PasswordRuleFailure(
                "MISSING_SPECIAL",
                "Password must contain a special character.",
            )
        )
    return failures
