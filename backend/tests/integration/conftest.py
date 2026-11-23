"""Integration fixtures: real PostgreSQL (``ps5_test``) and real SeaweedFS (test bucket).

``.env.test`` (repository root) is loaded into the process environment before any
settings are built, and the suite refuses to run unless it targets the test database
and the test bucket. Test runs never touch ``ps5`` or the development bucket (docs/05 §12).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import REPO_ROOT, Settings, load_settings
from app.main import create_app
from app.modules.storage.client import create_s3_client, init_bucket

ENV_TEST = REPO_ROOT / ".env.test"
TEST_DATABASE = "/ps5_test"
TEST_BUCKET = "ps5-documents-test"
SPA_INDEX = "<!doctype html><html lang='en-IN'><title>test build</title></html>"


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


@pytest.fixture(scope="session")
def settings() -> Settings:
    return load_settings(_env_file=None)


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


def make_client(settings: Settings, static_dir: Path) -> Iterator[TestClient]:
    app: FastAPI = create_app(settings, static_dir=static_dir)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client(settings: Settings, no_spa: Path, test_bucket: str) -> Iterator[TestClient]:
    yield from make_client(settings, no_spa)
