"""Shared fixtures for tests that use real services: PostgreSQL ``ps5_test`` and SeaweedFS.

``.env.test`` (repository root) is loaded into the process environment before any settings
are built, and the suite refuses to run unless it targets the test database and the test
bucket. Test runs never touch ``ps5`` or the development bucket (docs/05 §12).

Database lifecycle (docs/11 §1, DB-01):

- once per run, every object the migrator owns in ``ps5_test`` is dropped and Alembic
  upgrades the empty database to head;
- before each test, every application table is emptied with TRUNCATE by the migrator role
  (the app role is never granted TRUNCATE; docs/06 §10), except the seeded template catalogue.

Imported by tests/integration/conftest.py and tests/db/conftest.py.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text

from alembic import command
from app.core.clock import FrozenClock
from app.core.config import REPO_ROOT, Settings, load_settings, normalise_database_url
from app.main import create_app
from app.modules.storage.client import create_s3_client, init_bucket

ENV_TEST = REPO_ROOT / ".env.test"
TEST_DATABASE = "/ps5_test"
TEST_BUCKET = "ps5-documents-test"
ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"
SPA_INDEX = "<!doctype html><html lang='en-IN'><title>test build</title></html>"
# Tables whose rows are seeded by migrations and must survive per-test truncation.
SEEDED_TABLES = frozenset({"alembic_version", "templates"})
# A fixed instant for the frozen clock: 25 Nov 2026 11:12:10 IST.
DEFAULT_NOW = datetime(2026, 11, 25, 5, 42, 10, tzinfo=UTC)
CLIENT_ADDRESS = ("203.0.113.10", 50000)  # TEST-NET-3: a valid IP for per-IP throttling


def build_test_spa(root: Path) -> Path:
    """A minimal stand-in for the Vite build (test fixture data); returns the static dir."""
    static = root / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text(SPA_INDEX)
    (static / "assets" / "index-abc123.js").write_text("console.log('ok')")
    (static / "favicon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    return static


def _load_env_test() -> None:
    if not ENV_TEST.is_file():
        pytest.exit("Missing .env.test: copy .env.test.example to .env.test (docs/05 §6.2)", 2)
    for raw in ENV_TEST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ[name.strip()] = value.strip().strip("'\"")
    database = urlsplit(os.environ.get("DATABASE_URL", "")).path
    migration = urlsplit(os.environ.get("MIGRATION_DATABASE_URL", "")).path
    if database != TEST_DATABASE or migration != TEST_DATABASE:
        pytest.exit("Refusing to run: .env.test must point at the ps5_test database", 2)
    if os.environ.get("S3_BUCKET") != TEST_BUCKET:
        pytest.exit(f"Refusing to run: .env.test must use the {TEST_BUCKET} bucket", 2)


_load_env_test()


def migration_url() -> str:
    url = normalise_database_url(os.environ["MIGRATION_DATABASE_URL"])
    if urlsplit(url).path != TEST_DATABASE:  # defence in depth: never another database
        raise RuntimeError("migration URL does not point at ps5_test")
    return url


def alembic_config() -> Config:
    config = Config(str(ALEMBIC_INI))
    config.attributes["database_url"] = migration_url()
    config.attributes["configure_logger"] = False
    return config


def reset_schema(engine: Engine) -> None:
    """Drop every table, view and function the migrator owns in ps5_test's public schema."""
    with engine.begin() as connection:
        tables = connection.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        ).scalars()
        for table in tables:
            connection.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
        functions = connection.execute(
            text(
                "SELECT p.oid::regprocedure::text FROM pg_proc p "
                "JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'public'"
            )
        ).scalars()
        for signature in functions:
            connection.execute(text(f"DROP FUNCTION IF EXISTS {signature} CASCADE"))


def upgrade_to_head() -> None:
    command.upgrade(alembic_config(), "head")


def truncate_all(engine: Engine) -> None:
    with engine.begin() as connection:
        tables = [
            name
            for name in connection.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            ).scalars()
            if name not in SEEDED_TABLES
        ]
        if tables:
            joined = ", ".join(f'"{name}"' for name in tables)
            connection.execute(text(f"TRUNCATE {joined} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def settings() -> Settings:
    return load_settings(_env_file=None)


@pytest.fixture(scope="session")
def migrator_engine() -> Iterator[Engine]:
    engine = create_engine(migration_url(), pool_size=2)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def migrated_database(migrator_engine: Engine) -> None:
    """DB-01 precondition: an empty ps5_test upgraded to head once per run."""
    reset_schema(migrator_engine)
    upgrade_to_head()


@pytest.fixture(autouse=True)
def clean_tables(migrated_database: None, migrator_engine: Engine) -> None:
    truncate_all(migrator_engine)


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock(DEFAULT_NOW)


@pytest.fixture(scope="session")
def s3(settings: Settings) -> Any:
    """The application's S3 client and credentials (the test identity)."""
    return create_s3_client(settings)


@pytest.fixture(scope="session")
def test_bucket(settings: Settings, s3: Any) -> str:
    """Ensure the test bucket exists, through the same code path as init-dev-storage."""
    init_bucket(s3, settings.s3_bucket, settings.s3_region)
    return settings.s3_bucket


@pytest.fixture
def no_spa(tmp_path: Path) -> Path:
    """An empty static directory: the app serves the API only."""
    return tmp_path / "no-spa"


def make_client(
    settings: Settings, static_dir: Path, clock: FrozenClock | None = None
) -> Iterator[TestClient]:
    app: FastAPI = create_app(settings, static_dir=static_dir, clock=clock)
    # https: the session cookie is Secure, and httpx only returns it over https.
    with TestClient(app, base_url="https://testserver", client=CLIENT_ADDRESS) as client:
        yield client


@pytest.fixture
def client(
    settings: Settings, no_spa: Path, test_bucket: str, clock: FrozenClock
) -> Iterator[TestClient]:
    yield from make_client(settings, no_spa, clock)
