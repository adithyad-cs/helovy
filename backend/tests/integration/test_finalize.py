"""IT-FIN-01 to IT-FIN-07 (docs/11 §2.7): atomic finalisation exactly as docs/09 §8."""

from __future__ import annotations

import threading
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.core.errors import AppError
from app.modules.documents import finalize as finalize_module
from app.modules.documents.snapshot import canonical_sha256
from app.modules.tenancy.dependencies import Tenant
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

F06 = {
    "description": "Free",
    "quantity": "1",
    "unit_price": "100.00",
    "discount_type": "percent",
    "discount_value": "100",
}


@pytest.fixture
def owner(client: TestClient) -> tuple[ApiSession, str, str]:
    session = trusted(client)
    business = create_business(session)
    customer = create_customer(session, business["id"])
    return session, business["id"], customer["id"]


def _one(engine: Engine, sql: str, **params: Any) -> Any:
    with engine.connect() as connection:
        return connection.execute(text(sql), params).scalar_one()


def test_it_fin_01_happy_path(owner: tuple[ApiSession, str, str], migrator_engine: Engine) -> None:
    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id, lines=[F01, F02], due_date="2026-12-10")
    response = finalize(session, draft)
    assert response.status_code == 200, response.text
    body = response.json()
    assert response.headers["etag"] == '"2"'
    assert "idempotent-replayed" not in response.headers
    assert body["status"] == "finalized"
    assert body["number"] == "INV/26-27/00001"
    assert body["issue_date"] == "2026-11-25"  # the frozen clock's date in Asia/Kolkata
    assert body["finalized_at"] == "2026-11-25T05:42:10Z"
    assert body["totals"] == {
        "gross_total": "2999.99",
        "discount_total": "299.99",
        "grand_total": "2700.00",
    }
    assert body["version"] == 2
    assert body["pdf"]["status"] == "pending"  # as committed; the render runs after the response
    assert body["seller"]["legal_name"] == "Lotus Lane Design Studio (Demo)"

    snapshot = _one(
        migrator_engine,
        "SELECT payload FROM document_snapshots WHERE document_id = :d",
        d=draft["id"],
    )
    stored_hash = _one(
        migrator_engine,
        "SELECT canonical_sha256 FROM document_snapshots WHERE document_id = :d",
        d=draft["id"],
    )
    assert canonical_sha256(snapshot) == stored_hash == body["snapshot_sha256"]
    assert snapshot["totals"]["grand_total"] == "2700.00"
    assert (
        snapshot["labels"]["specimen_text"]
        == "SPECIMEN — demonstration document, not a tax invoice."
    )
    details = _one(
        migrator_engine, "SELECT details FROM audit_events WHERE event_type = 'document.finalized'"
    )
    assert details == {"number": "INV/26-27/00001", "snapshot_sha256": stored_hash}

    # The background render ran in the test: the artifact went from pending to ready.
    after = session.get(f"/api/v1/documents/{draft['id']}").json()
    assert after["pdf"]["status"] == "ready" and after["pdf"]["attempts"] == 1
    assert after["number"] == body["number"] and after["version"] == 2
    assert after["lines"] == body["lines"]
    rendered = _one(
        migrator_engine,
        "SELECT details FROM audit_events WHERE event_type = 'document.pdf_rendered'",
    )
    assert rendered["attempt"] == 1 and rendered["sha256"] == after["pdf"]["sha256"]


def test_it_fin_02_preconditions(owner: tuple[ApiSession, str, str]) -> None:
    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id, lines=[F01])
    url = f"/api/v1/documents/{draft['id']}/finalize"
    missing_key = session.post(url, headers={"If-Match": '"1"'})
    assert (
        missing_key.status_code == 400 and missing_key.json()["code"] == "idempotency_key_missing"
    )
    bad_key = session.post(url, headers={"If-Match": '"1"', "Idempotency-Key": "short"})
    assert bad_key.status_code == 400 and bad_key.json()["code"] == "malformed_request"
    no_match = session.post(url, headers={"Idempotency-Key": "abcdefgh12345"})
    assert no_match.status_code == 428
    stale = session.post(url, headers={"Idempotency-Key": "abcdefgh12345", "If-Match": '"7"'})
    assert stale.status_code == 412 and stale.json()["code"] == "version_mismatch"
    assert session.get(f"/api/v1/documents/{draft['id']}").json()["status"] == "draft"


def test_it_fin_03_idempotent_replay_and_mismatch(
    owner: tuple[ApiSession, str, str], migrator_engine: Engine
) -> None:
    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id, lines=[F01])
    first = finalize(session, draft, key="same-key-123456")
    replay = finalize(session, draft, key="same-key-123456")  # same If-Match "1": same fingerprint
    assert first.status_code == replay.status_code == 200
    assert replay.headers["idempotent-replayed"] == "true"
    assert replay.json() == first.json()  # the stored body, not recomputed
    assert (
        _one(migrator_engine, "SELECT count(*) FROM documents WHERE document_number IS NOT NULL")
        == 1
    )
    other = create_draft(session, business_id, customer_id, lines=[F02])
    mismatch = finalize(session, other, key="same-key-123456")
    assert mismatch.status_code == 422 and mismatch.json()["code"] == "idempotency_key_mismatch"
    assert session.get(f"/api/v1/documents/{other['id']}").json()["status"] == "draft"


def _tenant(session: ApiSession) -> Tenant:
    return Tenant(
        org_id=session.account.org_id,
        user_id=session.account.user_id,
        role="owner",
        session_id=uuid.uuid4(),
    )


def _run_concurrently(app: Any, calls: list[tuple[str, str, int]], tenant: Tenant) -> list[Any]:
    """Each call in its own thread with its own session and connection (IT-FIN-04)."""
    results: list[Any] = [None] * len(calls)
    barrier = threading.Barrier(len(calls))

    def work(index: int, document_id: str, key: str, version: int) -> None:
        with app.state.db_sessions() as db:
            barrier.wait()
            try:
                results[index] = finalize_module.finalize(
                    db, tenant, app.state.clock, uuid.UUID(document_id),
                    idem_key=key, if_match=f'"{version}"', expected_version=version,
                )  # fmt: skip
            except AppError as error:
                results[index] = error.code

    threads = [threading.Thread(target=work, args=(i, *call)) for i, call in enumerate(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    return results


def test_it_fin_04_concurrent_finalisations(
    owner: tuple[ApiSession, str, str], client: TestClient
) -> None:
    session, business_id, customer_id = owner
    tenant = _tenant(session)
    drafts = [create_draft(session, business_id, customer_id, lines=[F01]) for _ in range(10)]
    results = _run_concurrently(
        client.app, [(d["id"], f"key-ten-{i:04d}", 1) for i, d in enumerate(drafts)], tenant
    )
    numbers = sorted(result.body["number"] for result in results)
    assert numbers == [f"INV/26-27/{n:05d}" for n in range(1, 11)]  # unique, consecutive, no gaps

    one = create_draft(session, business_id, customer_id, lines=[F01])
    pair = _run_concurrently(
        client.app, [(one["id"], "key-pair-aaaa", 1), (one["id"], "key-pair-bbbb", 1)], tenant
    )
    outcomes = sorted("ok" if not isinstance(r, str) else r for r in pair)
    assert outcomes == ["document_not_draft", "ok"]

    two = create_draft(session, business_id, customer_id, lines=[F01])
    same = _run_concurrently(
        client.app, [(two["id"], "key-same-cccc", 1), (two["id"], "key-same-cccc", 1)], tenant
    )
    kinds = sorted(
        "replayed"
        if not isinstance(r, str) and r.replayed
        else ("ok" if not isinstance(r, str) else r)
        for r in same
    )
    assert kinds in (["ok", "replayed"], ["idempotency_in_progress", "ok"])
    assert sorted(set(r.body["number"] for r in same if not isinstance(r, str))) == [
        "INV/26-27/00012"
    ]


@pytest.mark.parametrize(
    "case", ["no_lines", "zero_total", "total_too_large", "due_date_before_issue_date", "inactive"]
)
def test_it_fin_05_blocked(
    owner: tuple[ApiSession, str, str], migrator_engine: Engine, case: str
) -> None:
    session, business_id, customer_id = owner
    lines = {"no_lines": [], "zero_total": [F06]}.get(case, [F01])
    due = "2026-11-24" if case == "due_date_before_issue_date" else None
    draft = create_draft(session, business_id, customer_id, lines=lines, due_date=due)
    if case == "total_too_large":
        with migrator_engine.begin() as c:
            c.execute(text("UPDATE document_lines SET quantity = 1000000, unit_price = 10000000.00, "
                           "discount_type = 'none', discount_value = NULL WHERE document_id = :d"), {"d": draft["id"]})  # fmt: skip
    if case == "inactive":
        with migrator_engine.begin() as c:
            c.execute(text("UPDATE templates SET is_active = false"))
    try:
        response = finalize(session, draft)
    finally:
        with migrator_engine.begin() as c:
            c.execute(text("UPDATE templates SET is_active = true"))
    assert response.status_code == 422
    assert response.json()["code"] == "finalization_blocked"
    assert case in [e["code"] for e in response.json()["errors"]]
    assert _one(migrator_engine, "SELECT count(*) FROM number_series") == 0  # no number consumed
    assert _one(migrator_engine, "SELECT count(*) FROM idempotency_keys") == 0  # rolled back too


def test_it_fin_06_rollback_consumes_no_number(
    owner: tuple[ApiSession, str, str], monkeypatch: pytest.MonkeyPatch, migrator_engine: Engine
) -> None:
    session, business_id, customer_id = owner
    first = create_draft(session, business_id, customer_id, lines=[F01])

    def explode(payload: Any) -> str:
        raise RuntimeError("injected failure after step 7")

    monkeypatch.setattr(finalize_module, "snapshot_hash", explode)
    failed = finalize(session, first)
    assert failed.status_code == 500 and failed.json()["code"] == "internal_error"
    assert session.get(f"/api/v1/documents/{first['id']}").json()["status"] == "draft"
    assert _one(migrator_engine, "SELECT count(*) FROM document_snapshots") == 0
    monkeypatch.undo()
    ok = finalize(session, first)
    assert ok.status_code == 200
    assert ok.json()["number"] == "INV/26-27/00001"


def test_it_fin_07_exhaustion(owner: tuple[ApiSession, str, str], migrator_engine: Engine) -> None:
    session, business_id, customer_id = owner
    warmup = create_draft(session, business_id, customer_id, lines=[F01])
    assert finalize(session, warmup).status_code == 200
    with migrator_engine.begin() as c:
        c.execute(text("UPDATE number_series SET next_seq = 1000000"))
    draft = create_draft(session, business_id, customer_id, lines=[F01])
    response = finalize(session, draft)
    assert response.status_code == 409
    assert response.json()["code"] == "number_series_exhausted"
    after = session.get(f"/api/v1/documents/{draft['id']}").json()
    assert after["status"] == "draft" and after["version"] == 1
    assert _one(migrator_engine, "SELECT next_seq FROM number_series") == 1000000


def test_finalised_document_is_read_only(owner: tuple[ApiSession, str, str]) -> None:
    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id, lines=[F01])
    issued = finalize(session, draft).json()
    url = f"/api/v1/documents/{draft['id']}"
    assert (
        session.patch(url, json={"notes": "x"}, headers={"If-Match": '"2"'}).json()["code"]
        == "document_not_draft"
    )
    assert session.delete(url, headers={"If-Match": '"2"'}).json()["code"] == "document_not_draft"
    again = finalize(session, {**draft, "version": 2})
    assert again.status_code == 409 and again.json()["code"] == "document_not_draft"
    assert session.get(url).json()["number"] == issued["number"]


def test_snapshot_keeps_issued_details_after_edits(owner: tuple[ApiSession, str, str]) -> None:
    # DC-15 at the API level: later profile and customer edits do not change the issued document.
    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id, lines=[F01])
    issued = finalize(session, draft).json()
    session.patch(
        f"/api/v1/businesses/{business_id}",
        json={"phone": "+91 99 9999 9999"},
        headers={"If-Match": '"1"'},
    )
    session.patch(f"/api/v1/businesses/{business_id}/customers/{customer_id}", json={"display_name": "Renamed (Demo)"},
                  headers={"If-Match": '"1"'})  # fmt: skip
    after = session.get(f"/api/v1/documents/{draft['id']}").json()
    assert after["seller"] == issued["seller"] and after["buyer"] == issued["buyer"]
    assert after["customer"]["display_name"] == "Riverstone Consulting (Demo)"
