"""Request schemas for E-03 (docs/07 §4)."""

from __future__ import annotations

from pydantic import field_validator

from app.core.schemas import StrictModel, field_error
from app.modules.auth.security import normalise_email

EMAIL_MIN, EMAIL_MAX = 3, 254
PASSWORD_MAX = 1024


class LoginRequest(StrictModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        email = normalise_email(value)
        if not email:
            raise field_error("required", "Enter your email address.")
        if len(email) < EMAIL_MIN:
            raise field_error("too_short", f"Use at least {EMAIL_MIN} characters.")
        if len(email) > EMAIL_MAX:
            raise field_error("too_long", f"Use at most {EMAIL_MAX} characters.")
        return email

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        if not value:
            raise field_error("required", "Enter your password.")
        if len(value) > PASSWORD_MAX:
            raise field_error("too_long", f"Use at most {PASSWORD_MAX:,} characters.")
        return value
