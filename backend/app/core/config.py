"""Application settings, read only from environment variables (docs/05 §9).

The server refuses to start when a required variable is missing, when ``CSRF_SECRET``
is shorter than 32 bytes, or when ``APP_ORIGIN`` is not a valid origin. Validation
errors never include the offending values, so secrets cannot leak into logs.

For tools run on the host, a repository-root ``.env`` file is read as a fallback;
real environment variables always take precedence. The Docker image contains no
``.env`` file (docs/05 §7.1), so containers use their environment only.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
CSRF_SECRET_MIN_BYTES = 32

AppEnv = Literal["development", "demo", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_BUCKET_NAME = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
_HEX = re.compile(r"^(?:[0-9a-fA-F]{2})+$")


class ConfigError(RuntimeError):
    """Raised when the environment does not hold a valid configuration."""


class Settings(BaseSettings):
    """Every setting the server reads. Field names map to upper-case variable names."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        hide_input_in_errors=True,
        frozen=True,
    )

    app_env: AppEnv
    app_origin: str
    database_url: SecretStr
    migration_database_url: SecretStr | None = None
    s3_endpoint_url: str
    s3_region: str = Field(min_length=1)
    s3_bucket: str
    s3_access_key_id: SecretStr
    s3_secret_access_key: SecretStr
    s3_addressing_style: Literal["path", "virtual"] = "path"
    csrf_secret: SecretStr
    render_workers: int = Field(default=2, ge=1)
    render_timeout_s: int = Field(default=20, ge=1)
    client_ip_header: str | None = None
    log_level: LogLevel = "INFO"

    @field_validator("app_origin")
    @classmethod
    def _valid_origin(cls, value: str) -> str:
        parts = urlsplit(value)
        if (
            parts.scheme not in ("http", "https")
            or not parts.hostname
            or parts.path
            or parts.query
            or parts.fragment
            or parts.username is not None
            or parts.password is not None
        ):
            raise ValueError("must be an origin such as http://localhost:8000 (no path or slash)")
        try:
            _ = parts.port
        except ValueError as exc:
            raise ValueError("has an invalid port") from exc
        return value

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def _postgres_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and not value.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("must start with postgresql+psycopg://")
        return value

    @field_validator("s3_endpoint_url")
    @classmethod
    def _endpoint_url(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError("must be an http(s) URL")
        return value

    @field_validator("s3_bucket")
    @classmethod
    def _bucket_name(cls, value: str) -> str:
        if not _BUCKET_NAME.match(value):
            raise ValueError("is not a valid bucket name")
        return value

    @field_validator("csrf_secret")
    @classmethod
    def _csrf_secret_length(cls, value: SecretStr) -> SecretStr:
        if len(_secret_key_bytes(value.get_secret_value())) < CSRF_SECRET_MIN_BYTES:
            raise ValueError(f"must be at least {CSRF_SECRET_MIN_BYTES} bytes")
        return value

    @property
    def csrf_key(self) -> bytes:
        """The HMAC key bytes. A hex value is decoded, so 64 hex characters give 32 bytes."""
        return _secret_key_bytes(self.csrf_secret.get_secret_value())

    @property
    def is_https(self) -> bool:
        return urlsplit(self.app_origin).scheme == "https"

    @property
    def docs_enabled(self) -> bool:
        """The API docs UI exists only in development (docs/05 §9, docs/12 §2.1)."""
        return self.app_env == "development"


class MigrationSettings(BaseSettings):
    """Only what Alembic needs: the owner role's URL (docs/05 §9, docs/06 §14 rule 3)."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        hide_input_in_errors=True,
        frozen=True,
    )

    migration_database_url: SecretStr

    @field_validator("migration_database_url")
    @classmethod
    def _postgres_url(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("must start with postgresql+psycopg://")
        return value


def load_migration_url() -> str:
    """MIGRATION_DATABASE_URL, or ConfigError naming the variable (never its value)."""
    try:
        return MigrationSettings().migration_database_url.get_secret_value()
    except ValidationError:
        raise ConfigError(
            "Invalid configuration: MIGRATION_DATABASE_URL is required and must start with "
            "postgresql+psycopg://"
        ) from None


def _secret_key_bytes(secret: str) -> bytes:
    return bytes.fromhex(secret) if _HEX.match(secret) else secret.encode("utf-8")


def load_settings(**overrides: object) -> Settings:
    """Build settings or raise ConfigError listing the variable names, never their values."""
    try:
        return Settings(**overrides)  # type: ignore[arg-type]
    except ValidationError as exc:
        problems = []
        for error in exc.errors(include_input=False, include_url=False, include_context=False):
            name = "_".join(str(part) for part in error["loc"]).upper() or "CONFIGURATION"
            message = "is required" if error["type"] == "missing" else error["msg"]
            problems.append(f"{name} {message}")
        raise ConfigError("Invalid configuration: " + "; ".join(problems)) from None
