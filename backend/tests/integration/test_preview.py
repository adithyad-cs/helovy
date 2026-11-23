"""IT-DOC-04 (docs/11 §2.2): E-20 watermarked preview; readiness template check (E-02)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.core.clock import FrozenClock
from app.core.config import Settings
from app.core.ratelimit import RateLimiter
from app.modules.rendering import registry
from tests.factories import (
    F01,
    F02,
    ApiSession,
    create_business,
    create_customer,
    create_draft,
    mark_finalized_in_database,
    trusted,
)
from tests.services import make_client


@pytest.fixture
def owner(client: TestClient) -> tuple[ApiSession, str, str]:
    session = trusted(client)
    business = create_business(session)
    customer = create_customer(session, business["id"])
    return session, business["id"], customer["id"]


def _preview(document_id: str) -> str:
    return f"/api/v1/documents/{document_id}/preview.pdf"


def test_it_doc_04_preview_is_a_pdf_and_nothing_is_stored(
    owner: tuple[ApiSession, str, str], migrator_engine: Engine
) -> None:
    from sqlalchemy import text

    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id, lines=[F01, F02])
    with migrator_engine.connect() as connection:
        events_before = connection.execute(text("SELECT count(*) FROM audit_events")).scalar_one()
    response = session.get(_preview(draft["id"]))
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'inline; filename="draft-preview.pdf"'
    assert response.headers["cache-control"] == "no-store"
    assert response.content.startswith(b"%PDF-")
    with migrator_engine.connect() as connection:
        assert (
            connection.execute(text("SELECT count(*) FROM audit_events")).scalar_one()
            == events_before
        )
    # The draft is unchanged by previewing.
    assert session.get(f"/api/v1/documents/{draft['id']}").json()["version"] == 1


def test_it_doc_04_no_lines_is_422(owner: tuple[ApiSession, str, str]) -> None:
    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id)
    response = session.get(_preview(draft["id"]))
    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"
    assert [(e["pointer"], e["code"]) for e in response.json()["errors"]] == [
        ("/lines", "no_lines")
    ]


def test_it_doc_04_finalised_is_409(
    owner: tuple[ApiSession, str, str], migrator_engine: Engine
) -> None:
    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id, lines=[F01])
    mark_finalized_in_database(migrator_engine, draft["id"])
    response = session.get(_preview(draft["id"]))
    assert response.status_code == 409
    assert response.json()["code"] == "document_not_draft"


def test_preview_rate_limit_and_head(
    owner: tuple[ApiSession, str, str], client: TestClient, clock: FrozenClock
) -> None:
    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id, lines=[F01])
    client.app.state.rate_limits["preview"] = RateLimiter(2, timedelta(minutes=1))  # type: ignore[attr-defined]
    head = client.head(_preview(draft["id"]))  # HEAD counts toward the same limit (07 §1.14)
    assert head.status_code == 200 and head.content == b""
    assert head.headers["content-type"] == "application/pdf"
    assert session.get(_preview(draft["id"])).status_code == 200
    limited = session.get(_preview(draft["id"]))
    assert limited.status_code == 429
    assert limited.json()["code"] == "rate_limited"
    clock.advance(timedelta(seconds=61))
    assert session.get(_preview(draft["id"])).status_code == 200


def test_preview_renderer_timeout_is_503(
    owner: tuple[ApiSession, str, str], client: TestClient
) -> None:
    from app.modules.rendering.pool import RenderPool

    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id, lines=[F01])
    pool = client.app.state.render_pool  # type: ignore[attr-defined]
    client.app.state.render_pool = RenderPool(1, 0.05)  # type: ignore[attr-defined]
    try:
        response = session.get(_preview(draft["id"]))
    finally:
        client.app.state.render_pool.close()  # type: ignore[attr-defined]
        client.app.state.render_pool = pool  # type: ignore[attr-defined]
    assert response.status_code == 503
    assert response.json()["code"] == "dependency_unavailable"


@pytest.mark.parametrize(
    ("app_env", "status", "check"), [("development", 200, "warn"), ("demo", 503, "error")]
)
def test_readyz_template_mismatch(
    settings: Settings, no_spa: Path, test_bucket: str, monkeypatch: pytest.MonkeyPatch,
    app_env: str, status: int, check: str,
) -> None:  # fmt: skip
    entry = registry.get("classic@1")
    monkeypatch.setitem(
        registry.REGISTRY,
        "classic@1",
        registry.RegisteredTemplate("classic@1", entry.directory, "0" * 64),
    )
    for client in make_client(settings.model_copy(update={"app_env": app_env}), no_spa):
        response = client.get("/readyz")
        assert response.status_code == status
        assert response.json()["checks"]["templates"] == check
