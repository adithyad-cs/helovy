"""IT-HLT-01 (partial, M0): liveness and readiness against the real database and storage.

The template-hash part of IT-HLT-01 (``/readyz`` 503 on a mismatch with APP_ENV=demo)
arrives with the template registry in M4.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text

from app.core.config import Settings
from tests.integration.conftest import make_client

UNREACHABLE_DB = "postgresql+psycopg://ps5_app:unused@127.0.0.1:1/ps5_test"
UNREACHABLE_S3 = "http://127.0.0.1:1"


def test_healthz_returns_ok(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_does_not_need_database_or_storage(settings: Settings, no_spa: Path) -> None:
    broken = settings.model_copy(
        update={"database_url": SecretStr(UNREACHABLE_DB), "s3_endpoint_url": UNREACHABLE_S3}
    )
    for client in make_client(broken, no_spa):
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_readyz_is_ready_when_database_and_storage_are_up(client: TestClient) -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok", "storage": "ok"}}


def test_readyz_503_when_database_is_down(settings: Settings, no_spa: Path) -> None:
    broken = settings.model_copy(update={"database_url": SecretStr(UNREACHABLE_DB)})
    for client in make_client(broken, no_spa):
        response = client.get("/readyz")
        assert response.status_code == 503
        assert response.json() == {
            "status": "not_ready",
            "checks": {"database": "error", "storage": "ok"},
        }


def test_readyz_503_when_storage_is_down(settings: Settings, no_spa: Path) -> None:
    broken = settings.model_copy(update={"s3_endpoint_url": UNREACHABLE_S3})
    for client in make_client(broken, no_spa):
        response = client.get("/readyz")
        assert response.status_code == 503
        assert response.json() == {
            "status": "not_ready",
            "checks": {"database": "ok", "storage": "error"},
        }


def test_readyz_503_when_bucket_is_not_accessible(settings: Settings, no_spa: Path) -> None:
    # The test identity has no rights on the development bucket (docs/12 §8).
    broken = settings.model_copy(update={"s3_bucket": "ps5-documents-dev"})
    for client in make_client(broken, no_spa):
        response = client.get("/readyz")
        assert response.status_code == 503
        assert response.json()["checks"]["storage"] == "error"


def test_readyz_body_has_no_error_details(settings: Settings, no_spa: Path) -> None:
    broken = settings.model_copy(
        update={"database_url": SecretStr(UNREACHABLE_DB), "s3_endpoint_url": UNREACHABLE_S3}
    )
    for client in make_client(broken, no_spa):
        response = client.get("/readyz")
        assert response.status_code == 503
        assert set(response.json()) == {"status", "checks"}
        assert "127.0.0.1" not in response.text


def test_readiness_uses_the_restricted_app_role(client: TestClient) -> None:
    engine = client.app.state.db_engine  # type: ignore[attr-defined]
    with engine.connect() as connection:
        role = connection.execute(text("SELECT current_user")).scalar_one()
        database = connection.execute(text("SELECT current_database()")).scalar_one()
        superuser = connection.execute(
            text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        ).scalar_one()
    assert role == "ps5_app"
    assert database == "ps5_test"
    assert superuser is False
