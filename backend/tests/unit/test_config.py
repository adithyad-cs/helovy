"""Settings fail fast on missing or invalid values (NFR-12; docs/05 §9; IT-HLT-01 basis).

Secret values must never appear in configuration error messages.
"""

from __future__ import annotations

import secrets

import pytest

from app.core.config import ConfigError, Settings, load_settings

REQUIRED = (
    "APP_ENV",
    "APP_ORIGIN",
    "DATABASE_URL",
    "S3_ENDPOINT_URL",
    "S3_REGION",
    "S3_BUCKET",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "CSRF_SECRET",
)
OPTIONAL = (
    "MIGRATION_DATABASE_URL",
    "S3_ADDRESSING_STYLE",
    "RENDER_WORKERS",
    "RENDER_TIMEOUT_S",
    "CLIENT_IP_HEADER",
    "LOG_LEVEL",
)


def _valid_env() -> dict[str, str]:
    return {
        "APP_ENV": "development",
        "APP_ORIGIN": "http://localhost:8000",
        "DATABASE_URL": "postgresql+psycopg://ps5_app:" + secrets.token_urlsafe(16) + "@db/ps5",
        "S3_ENDPOINT_URL": "http://storage:8333",
        "S3_REGION": "us-east-1",
        "S3_BUCKET": "ps5-documents-dev",
        "S3_ACCESS_KEY_ID": "key-" + secrets.token_hex(4),
        "S3_SECRET_ACCESS_KEY": secrets.token_urlsafe(24),
        "CSRF_SECRET": secrets.token_hex(32),
    }


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """A clean, valid environment; the repository .env file is never read in these tests."""
    for name in REQUIRED + OPTIONAL:
        monkeypatch.delenv(name, raising=False)
    values = _valid_env()
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return values


def _load() -> Settings:
    return load_settings(_env_file=None)


def test_valid_configuration_loads(env: dict[str, str]) -> None:
    settings = _load()
    assert settings.app_env == "development"
    assert settings.s3_addressing_style == "path"
    assert settings.render_workers == 2
    assert settings.render_timeout_s == 20
    assert settings.client_ip_header is None
    assert settings.csrf_key == bytes.fromhex(env["CSRF_SECRET"])
    assert len(settings.csrf_key) == 32
    assert settings.docs_enabled is True
    assert settings.is_https is False


@pytest.mark.parametrize("name", REQUIRED)
def test_missing_required_variable_fails_fast(
    env: dict[str, str], monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.delenv(name)
    with pytest.raises(ConfigError, match=f"{name} is required"):
        _load()


@pytest.mark.parametrize("name", REQUIRED)
def test_empty_required_variable_counts_as_missing(
    env: dict[str, str], monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setenv(name, "")
    with pytest.raises(ConfigError, match=f"{name} is required"):
        _load()


@pytest.mark.parametrize(
    "secret",
    [
        secrets.token_hex(31),  # 62 hex characters decode to 31 bytes
        "x" * 31,  # 31 bytes of text
    ],
    ids=["hex-31-bytes", "text-31-bytes"],  # stable IDs; the random value never appears
)
def test_short_csrf_secret_is_rejected_without_leaking_it(
    env: dict[str, str], monkeypatch: pytest.MonkeyPatch, secret: str
) -> None:
    monkeypatch.setenv("CSRF_SECRET", secret)
    with pytest.raises(ConfigError) as caught:
        _load()
    message = str(caught.value)
    assert "CSRF_SECRET" in message
    assert "at least 32 bytes" in message
    assert secret not in message
    assert caught.value.__cause__ is None  # the original error, with inputs, is not chained


def test_text_csrf_secret_of_32_bytes_is_accepted(
    env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CSRF_SECRET", "y" * 32)
    assert _load().csrf_key == b"y" * 32


@pytest.mark.parametrize(
    "origin",
    [
        "localhost:8000",
        "http://localhost:8000/",
        "http://localhost:8000/app",
        "http://localhost:8000?x=1",
        "ftp://localhost",
        "http://user:pass@localhost:8000",
        "http://localhost:99999",
        "http://",
    ],
)
def test_invalid_app_origin_fails_fast(
    env: dict[str, str], monkeypatch: pytest.MonkeyPatch, origin: str
) -> None:
    monkeypatch.setenv("APP_ORIGIN", origin)
    with pytest.raises(ConfigError, match="APP_ORIGIN"):
        _load()


def test_https_origin_enables_hsts(env: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ORIGIN", "https://hive-docs.example.invalid")
    assert _load().is_https is True


@pytest.mark.parametrize("app_env", ["demo", "production"])
def test_docs_ui_only_in_development(
    env: dict[str, str], monkeypatch: pytest.MonkeyPatch, app_env: str
) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    assert _load().docs_enabled is False


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("APP_ENV", "staging"),
        ("S3_ADDRESSING_STYLE", "auto"),
        ("S3_BUCKET", "Not_A_Bucket"),
        ("S3_ENDPOINT_URL", "storage:8333"),
        ("RENDER_WORKERS", "0"),
        ("LOG_LEVEL", "LOUD"),
    ],
)
def test_invalid_values_fail_fast(
    env: dict[str, str], monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigError, match=name):
        _load()


def test_wrong_database_url_scheme_does_not_leak_password(
    env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    password = secrets.token_urlsafe(16)
    monkeypatch.setenv("DATABASE_URL", f"postgresql://ps5_app:{password}@db/ps5")
    with pytest.raises(ConfigError, match="DATABASE_URL") as caught:
        _load()
    assert password not in str(caught.value)


def test_empty_optional_variable_is_unset(
    env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLIENT_IP_HEADER", "")
    assert _load().client_ip_header is None


def test_secrets_are_masked_in_repr(env: dict[str, str]) -> None:
    text = repr(_load())
    for name in ("DATABASE_URL", "S3_SECRET_ACCESS_KEY", "CSRF_SECRET", "S3_ACCESS_KEY_ID"):
        assert env[name] not in text
