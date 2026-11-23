"""DB-05, DB-06, DB-09 (docs/11 §2.4); UT-SNAP-02 (JSONB round trip); V-14 generated columns."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.modules.documents.snapshot import canonical_sha256
from tests.db.test_documents_schema import _finalize, _seed
from tests.unit.test_rendering import sample_payload

RESTRICT_VIOLATION = "23001"


def _sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None)


def _issue(engine: Engine) -> dict[str, uuid.UUID]:
    ids = _seed(engine)
    _finalize(engine, ids)
    payload = sample_payload(final=True)
    with engine.begin() as c:
        ids["snapshot"] = c.execute(
            text(
                "INSERT INTO document_snapshots (org_id, document_id, calc_version, template_id, payload, canonical_sha256) "
                "VALUES (:o, :d, 'calc-1.0.0', 'classic@1', CAST(:p AS jsonb), :h) RETURNING id"
            ),
            {
                "o": ids["org_a"],
                "d": ids["draft"],
                "p": json.dumps(payload),
                "h": canonical_sha256(payload),
            },
        ).scalar_one()
        ids["file"] = c.execute(
            text(
                "INSERT INTO stored_files (org_id, bucket, object_key, size_bytes, sha256) "
                "VALUES (:o, 'b', :k, 10, :s) RETURNING id"
            ),
            {
                "o": ids["org_a"],
                "k": f"orgs/{ids['org_a']}/documents/{ids['draft']}/final-x.pdf",
                "s": "a" * 64,
            },
        ).scalar_one()
        ids["artifact"] = c.execute(
            text(
                "INSERT INTO document_artifacts (org_id, document_id, template_id) VALUES (:o, :d, 'classic@1') RETURNING id"
            ),
            {"o": ids["org_a"], "d": ids["draft"]},
        ).scalar_one()
    return ids


def test_v14_generated_columns_and_ut_snap_02_round_trip(migrator_engine: Engine) -> None:
    ids = _issue(migrator_engine)
    with migrator_engine.connect() as c:
        row = c.execute(
            text(
                "SELECT payload, canonical_sha256, buyer_name, grand_total FROM document_snapshots WHERE id = :i"
            ),
            {"i": ids["snapshot"]},
        ).one()
    assert row.buyer_name == "Riverstone Consulting (Demo)"
    assert str(row.grand_total) == "3600.00"
    assert canonical_sha256(row.payload) == row.canonical_sha256  # JSONB keeps the content exactly


@pytest.mark.parametrize("statement", ["UPDATE document_snapshots SET calc_version = 'calc-1.0.1'",
                                       "DELETE FROM document_snapshots"])  # fmt: skip
def test_db_05_snapshots_are_immutable(migrator_engine: Engine, statement: str) -> None:
    _issue(migrator_engine)
    with pytest.raises(DBAPIError) as raised, migrator_engine.begin() as c:
        c.execute(text(statement))
    assert _sqlstate(raised.value) == RESTRICT_VIOLATION


def test_db_06_artifact_guard(migrator_engine: Engine) -> None:
    ids = _issue(migrator_engine)
    with pytest.raises(DBAPIError) as raised, migrator_engine.begin() as c:
        c.execute(text("DELETE FROM document_artifacts WHERE id = :a"), {"a": ids["artifact"]})
    assert _sqlstate(raised.value) == RESTRICT_VIOLATION
    with pytest.raises(DBAPIError) as raised, migrator_engine.begin() as c:
        c.execute(text("UPDATE document_artifacts SET template_id = 'classic@1', kind = 'final_pdf', document_id = :d WHERE id = :a"),
                  {"a": ids["artifact"], "d": uuid.uuid4()})  # fmt: skip
    assert _sqlstate(raised.value) == RESTRICT_VIOLATION
    with migrator_engine.begin() as c:  # pending → ready with its file is allowed
        c.execute(
            text(
                "UPDATE document_artifacts SET status = 'ready', stored_file_id = :f, rendered_at = now(), "
                "template_sha256 = repeat('b', 64), renderer_version = 'weasyprint 70.0' WHERE id = :a"
            ),
            {"f": ids["file"], "a": ids["artifact"]},
        )
    with pytest.raises(DBAPIError) as raised, migrator_engine.begin() as c:
        c.execute(
            text("UPDATE document_artifacts SET attempts = 5 WHERE id = :a"), {"a": ids["artifact"]}
        )
    assert _sqlstate(raised.value) == RESTRICT_VIOLATION


def test_ready_artifact_needs_its_file(migrator_engine: Engine) -> None:
    ids = _issue(migrator_engine)
    with pytest.raises(IntegrityError) as raised, migrator_engine.begin() as c:
        c.execute(
            text("UPDATE document_artifacts SET status = 'ready' WHERE id = :a"),
            {"a": ids["artifact"]},
        )
    assert "document_artifacts_ready_ck" in str(raised.value)


def test_stored_file_key_must_be_under_its_organization(migrator_engine: Engine) -> None:
    ids = _seed(migrator_engine)
    with pytest.raises(IntegrityError) as raised, migrator_engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO stored_files (org_id, bucket, object_key, size_bytes, sha256) VALUES (:o, 'b', :k, 1, :s)"
            ),
            {"o": ids["org_a"], "k": f"orgs/{ids['org_b']}/documents/x/final-y.pdf", "s": "a" * 64},
        )
    assert "stored_files_object_key_ck" in str(raised.value)


def test_db_09_uniqueness(migrator_engine: Engine) -> None:
    ids = _seed(migrator_engine)
    series = _finalize(migrator_engine, ids)
    with migrator_engine.begin() as c:
        second = c.execute(
            text(
                "INSERT INTO documents (org_id, business_id, customer_id, created_by) VALUES (:o, :b, :c, :u) RETURNING id"
            ),
            {"o": ids["org_a"], "b": ids["business_a"], "c": ids["customer_a"], "u": ids["user_a"]},
        ).scalar_one()
    finalise = (
        "UPDATE documents SET status = 'finalized', number_series_id = :s, sequence_no = :n, document_number = :num, "
        "issue_date = DATE '2026-11-25', finalized_at = now(), finalized_by = :u WHERE id = :d"
    )
    with pytest.raises(IntegrityError) as raised, migrator_engine.begin() as c:
        c.execute(
            text(finalise),
            {"s": series, "n": 2, "num": "INV/26-27/00001", "u": ids["user_a"], "d": second},
        )
    assert "documents_number_uq" in str(raised.value)
    with pytest.raises(IntegrityError) as raised, migrator_engine.begin() as c:
        c.execute(
            text(finalise),
            {"s": series, "n": 1, "num": "INV/26-27/00002", "u": ids["user_a"], "d": second},
        )
    assert "documents_series_seq_uq" in str(raised.value)
