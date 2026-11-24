"""Database URL normalisation for Render and other managed PostgreSQL (Render preparation).

Render gives ``postgresql://USER:PASSWORD@HOST:PORT/DATABASE`` (docs: postgresql-creating-
connecting); SQLAlchemy reads a bare ``postgresql://`` as psycopg2, which is not installed. The
settings rewrite only the scheme to ``postgresql+psycopg://`` and refuse every other driver.
Errors never contain the URL or its password.
"""

from __future__ import annotations

import secrets

import pytest
from sqlalchemy.engine import make_url

from app.core.config import (
    ConfigError,
    MigrationSettings,
    load_migration_url,
    load_settings,
    normalise_database_url,
)

PASSWORD = "p%40ss%2Fw0rd-" + secrets.token_urlsafe(12)  # percent-encoded '@' and '/'


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (
            f"postgresql://ps5_app:{PASSWORD}@dpg-abc123-a:5432/ps5",
            f"postgresql+psycopg://ps5_app:{PASSWORD}@dpg-abc123-a:5432/ps5",
        ),
        (
            f"postgres://ps5_app:{PASSWORD}@dpg-abc123-a/ps5",
            f"postgresql+psycopg://ps5_app:{PASSWORD}@dpg-abc123-a/ps5",
        ),
        (
            f"postgresql+psycopg://ps5_app:{PASSWORD}@localhost:5432/ps5_test",
            f"postgresql+psycopg://ps5_app:{PASSWORD}@localhost:5432/ps5_test",
        ),
        (
            f"POSTGRESQL://ps5_migrator:{PASSWORD}@host.example:5432/ps5_abcd?sslmode=require",
            f"postgresql+psycopg://ps5_migrator:{PASSWORD}@host.example:5432/ps5_abcd?sslmode=require",
        ),
        (
            f"Postgres://u:{PASSWORD}@h/ps5?sslmode=require&connect_timeout=5",
            f"postgresql+psycopg://u:{PASSWORD}@h/ps5?sslmode=require&connect_timeout=5",
        ),
        ("  postgresql://u:p@h/ps5  ", "postgresql+psycopg://u:p@h/ps5"),
    ],
)
def test_supported_forms_become_psycopg3(given: str, expected: str) -> None:
    assert normalise_database_url(given) == expected


def test_only_the_scheme_changes() -> None:
    url = make_url(
        normalise_database_url(f"postgresql://ps5_app:{PASSWORD}@dpg-x-a:6543/ps5?sslmode=require")
    )
    assert url.drivername == "postgresql+psycopg"
    assert url.username == "ps5_app"
    assert url.password == "p@ss/w0rd-" + PASSWORD.removeprefix("p%40ss%2Fw0rd-")
    assert (url.host, url.port, url.database) == ("dpg-x-a", 6543, "ps5")
    assert dict(url.query) == {"sslmode": "require"}


def test_normalising_twice_is_stable() -> None:
    once = normalise_database_url(f"postgres://u:{PASSWORD}@h:5432/ps5")
    assert normalise_database_url(once) == once


@pytest.mark.parametrize(
    "given",
    [
        f"postgresql+psycopg2://u:{PASSWORD}@h/ps5",
        f"postgresql+asyncpg://u:{PASSWORD}@h/ps5",
        f"postgresql+pg8000://u:{PASSWORD}@h/ps5",
        f"postgres+psycopg://u:{PASSWORD}@h/ps5",
        f"mysql://u:{PASSWORD}@h/ps5",
        f"sqlite:///ps5-{PASSWORD}.db",
        f"u:{PASSWORD}@h:5432/ps5",
        f"//u:{PASSWORD}@h/ps5",
        "postgresql://",
        "postgresql:///ps5",
        "postgresql://?host=/tmp",
        "",
    ],
)
def test_other_drivers_and_malformed_urls_are_refused_without_echo(given: str) -> None:
    with pytest.raises(ValueError) as caught:
        normalise_database_url(given)
    assert PASSWORD not in str(caught.value)
    assert "u:" not in str(caught.value)


def _app_env(monkeypatch: pytest.MonkeyPatch, database_url: str) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_ORIGIN", "https://hive-docs-staging.onrender.com")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://hive-docs-storage-ab12:8333")
    monkeypatch.setenv("S3_REGION", "us-east-1")
    monkeypatch.setenv("S3_BUCKET", "hive-docs-staging")
    monkeypatch.setenv("S3_ACCESS_KEY_ID", "key-" + secrets.token_hex(4))
    monkeypatch.setenv("S3_SECRET_ACCESS_KEY", secrets.token_urlsafe(24))
    # Render's generateValue gives a base64-encoded 256-bit value: accepted as 44 bytes.
    monkeypatch.setenv("CSRF_SECRET", "Zm9vYmFyYmF6cXV4cXV1eGZvb2JhcmJhenF1eHF1dXg/K0E=")


def test_settings_accept_a_render_connection_string(monkeypatch: pytest.MonkeyPatch) -> None:
    _app_env(monkeypatch, f"postgresql://ps5_app:{PASSWORD}@dpg-abc123-a/ps5")
    monkeypatch.setenv(
        "MIGRATION_DATABASE_URL", f"postgresql://ps5_migrator:{PASSWORD}@dpg-abc123-a/ps5"
    )
    settings = load_settings(_env_file=None)
    assert settings.database_url.get_secret_value().startswith("postgresql+psycopg://ps5_app:")
    assert settings.migration_database_url is not None
    assert settings.migration_database_url.get_secret_value().startswith(
        "postgresql+psycopg://ps5_migrator:"
    )
    assert PASSWORD not in repr(settings)


def test_settings_refuse_another_driver_without_leaking(monkeypatch: pytest.MonkeyPatch) -> None:
    _app_env(monkeypatch, f"postgresql+psycopg2://ps5_app:{PASSWORD}@dpg-abc123-a/ps5")
    with pytest.raises(ConfigError, match="DATABASE_URL") as caught:
        load_settings(_env_file=None)
    assert PASSWORD not in str(caught.value)


def test_alembic_receives_the_normalised_migration_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "MIGRATION_DATABASE_URL", f"postgres://ps5_migrator:{PASSWORD}@dpg-abc123-a:5432/ps5"
    )
    assert MigrationSettings(_env_file=None).migration_database_url.get_secret_value() == (
        f"postgresql+psycopg://ps5_migrator:{PASSWORD}@dpg-abc123-a:5432/ps5"
    )


def test_invalid_migration_url_names_the_variable_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIGRATION_DATABASE_URL", f"mysql://ps5_migrator:{PASSWORD}@h/ps5")
    monkeypatch.setattr(
        "app.core.config.MigrationSettings.model_config",
        {**MigrationSettings.model_config, "env_file": None},
    )
    with pytest.raises(ConfigError, match="MIGRATION_DATABASE_URL") as caught:
        load_migration_url()
    assert PASSWORD not in str(caught.value)
