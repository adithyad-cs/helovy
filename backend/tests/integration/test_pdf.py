"""IT-PDF-01 to IT-PDF-04 (docs/11 §2.8): private storage, integrity, failure and retry."""

from __future__ import annotations

import base64
import hashlib
import logging
from datetime import timedelta
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.core.clock import FrozenClock
from app.core.config import Settings
from app.modules.documents import artifacts
from app.modules.rendering.renderer import render_html
from app.modules.storage.client import create_s3_client
from tests.factories import (
    F01,
    F02,
    ApiSession,
    create_business,
    create_customer,
    create_draft,
    finalize,
    trusted,
)


@pytest.fixture
def owner(client: TestClient) -> tuple[ApiSession, str, str]:
    session = trusted(client)
    business = create_business(session)
    customer = create_customer(session, business["id"])
    return session, business["id"], customer["id"]


def _issue(owner: tuple[ApiSession, str, str]) -> dict[str, Any]:
    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id, lines=[F01, F02])
    assert finalize(session, draft).status_code == 200
    return session.get(f"/api/v1/documents/{draft['id']}").json()


def _row(engine: Engine, document_id: str) -> Any:
    with engine.connect() as c:
        return c.execute(
            text(
                "SELECT a.id AS artifact_id, a.status, a.attempts, a.last_error_code, f.bucket, f.object_key, "
                "f.sha256, f.size_bytes FROM document_artifacts a LEFT JOIN stored_files f ON f.id = a.stored_file_id "
                "WHERE a.document_id = :d"
            ),
            {"d": document_id},
        ).one()


def test_it_pdf_01_private_storage_and_identical_download(
    owner: tuple[ApiSession, str, str], migrator_engine: Engine, s3: Any, settings: Settings
) -> None:
    session, _, _ = owner
    document = _issue(owner)
    row = _row(migrator_engine, document["id"])
    org_id = session.account.org_id
    assert row.object_key == f"orgs/{org_id}/documents/{document['id']}/final-{row.artifact_id}.pdf"
    stored = s3.get_object(Bucket=row.bucket, Key=row.object_key)["Body"].read()
    assert hashlib.sha256(stored).hexdigest() == row.sha256 == document["pdf"]["sha256"]
    assert row.size_bytes == len(stored) == document["pdf"]["size_bytes"]
    assert stored.startswith(b"%PDF-")

    anonymous = httpx.get(f"{settings.s3_endpoint_url}/{row.bucket}/{row.object_key}", timeout=5)
    assert anonymous.status_code == 403  # private: no anonymous access

    response = session.get(f"/api/v1/documents/{document['id']}/pdf")
    assert response.status_code == 200
    assert response.content == stored
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="INV-26-27-00001.pdf"'
    assert (
        response.headers["content-digest"]
        == "sha-256=:" + base64.b64encode(hashlib.sha256(stored).digest()).decode() + ":"
    )
    assert response.headers["cache-control"] == "no-store"
    assert (
        session.get(f"/api/v1/documents/{document['id']}/pdf").content == stored
    )  # byte-identical again

    with migrator_engine.connect() as c:
        snapshot = c.execute(
            text("SELECT payload FROM document_snapshots WHERE document_id = :d"),
            {"d": document["id"]},
        ).scalar_one()
        downloads = c.execute(
            text("SELECT count(*) FROM audit_events WHERE event_type = 'document.pdf_downloaded'")
        ).scalar_one()
    assert downloads == 2
    html = render_html("classic@1", snapshot, preview=False)
    assert "SPECIMEN — demonstration document, not a tax invoice." in html and ">Invoice<" in html


def test_head_download_records_nothing(
    owner: tuple[ApiSession, str, str], migrator_engine: Engine
) -> None:
    session, _, _ = owner
    document = _issue(owner)
    head = session.client.head(f"/api/v1/documents/{document['id']}/pdf")
    assert head.status_code == 200 and head.content == b""
    assert head.headers["content-digest"].startswith("sha-256=:")
    with migrator_engine.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM audit_events WHERE event_type = 'document.pdf_downloaded'"
                )
            ).scalar_one()
            == 0
        )


def test_it_pdf_02_tamper_detection(
    owner: tuple[ApiSession, str, str],
    migrator_engine: Engine,
    s3: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session, _, _ = owner
    document = _issue(owner)
    row = _row(migrator_engine, document["id"])
    s3.put_object(
        Bucket=row.bucket,
        Key=row.object_key,
        Body=b"%PDF-1.7 tampered",
        ContentType="application/pdf",
    )
    with caplog.at_level(logging.ERROR, logger="app.documents"):
        response = session.get(f"/api/v1/documents/{document['id']}/pdf")
    assert response.status_code == 500
    assert response.json()["code"] == "integrity_check_failed"
    assert b"tampered" not in response.content
    assert any(r.levelno == logging.ERROR and "integrity" in r.getMessage() for r in caplog.records)


def test_download_rules(owner: tuple[ApiSession, str, str]) -> None:
    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id, lines=[F01])
    response = session.get(f"/api/v1/documents/{draft['id']}/pdf")
    assert response.status_code == 409 and response.json()["code"] == "document_not_finalized"
    retry = session.post(f"/api/v1/documents/{draft['id']}/pdf/render")
    assert retry.status_code == 409 and retry.json()["code"] == "document_not_finalized"


def test_it_pdf_03_storage_failure_then_retry(
    owner: tuple[ApiSession, str, str],
    client: TestClient,
    settings: Settings,
    migrator_engine: Engine,
    clock: FrozenClock,
) -> None:
    session, business_id, customer_id = owner
    healthy = client.app.state.s3  # type: ignore[attr-defined]
    client.app.state.s3 = create_s3_client(
        settings.model_copy(update={"s3_endpoint_url": "http://127.0.0.1:9"})
    )  # type: ignore[attr-defined]
    draft = create_draft(session, business_id, customer_id, lines=[F01])
    try:
        issued = finalize(session, draft).json()
    finally:
        client.app.state.s3 = healthy  # type: ignore[attr-defined]
    failed = session.get(f"/api/v1/documents/{draft['id']}").json()
    assert failed["pdf"]["status"] == "failed"
    assert failed["pdf"]["last_error_code"] == "storage_error"
    assert failed["pdf"]["retry_available"] is True
    with migrator_engine.connect() as c:
        event = c.execute(
            text("SELECT details FROM audit_events WHERE event_type = 'document.pdf_render_failed'")
        ).scalar_one()
    assert event["error_code"] == "storage_error" and event["attempt"] == 1
    pending = session.get(f"/api/v1/documents/{draft['id']}/pdf")
    assert (
        pending.status_code == 409
        and pending.json()["code"] == "pdf_not_ready"
        and pending.json()["pdf_status"] == "failed"
    )

    retried = session.post(f"/api/v1/documents/{draft['id']}/pdf/render")
    assert retried.status_code == 202
    assert retried.json()["pdf"]["status"] == "pending" and retried.json()["pdf"]["attempts"] == 2
    ready = session.get(f"/api/v1/documents/{draft['id']}").json()
    assert ready["pdf"]["status"] == "ready" and ready["pdf"]["attempts"] == 2
    assert ready["number"] == issued["number"]  # never renumbered
    assert session.get(f"/api/v1/documents/{draft['id']}/pdf").status_code == 200


def test_it_pdf_04_retry_rules(
    owner: tuple[ApiSession, str, str], monkeypatch: pytest.MonkeyPatch, clock: FrozenClock
) -> None:
    session, business_id, customer_id = owner
    ready = _issue(owner)
    url = f"/api/v1/documents/{ready['id']}/pdf/render"
    already = session.post(url)
    assert already.status_code == 200 and already.json()["pdf"]["status"] == "ready"

    monkeypatch.setattr(
        artifacts, "start_first_render", lambda state, artifact_id: None
    )  # leave it pending
    draft = create_draft(session, business_id, customer_id, lines=[F01])
    assert finalize(session, draft).status_code == 200
    url = f"/api/v1/documents/{draft['id']}/pdf/render"
    in_progress = session.post(url)
    assert in_progress.status_code == 409 and in_progress.json()["code"] == "pdf_render_in_progress"
    clock.advance(timedelta(seconds=121))
    assert session.get(f"/api/v1/documents/{draft['id']}").json()["pdf"]["retry_available"] is True
    claimed = session.post(url)
    assert claimed.status_code == 202
    limited = session.post(url)
    assert limited.status_code == 429 and limited.json()["code"] == "rate_limited"
    assert session.get(f"/api/v1/documents/{draft['id']}").json()["pdf"]["status"] == "ready"
