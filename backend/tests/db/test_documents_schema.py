"""DB-02 (constraints), DB-03 (trg_documents_guard), DB-04 (trg_document_lines_guard)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

RESTRICT_VIOLATION = "23001"


def _seed(engine: Engine) -> dict[str, uuid.UUID]:
    """Two organizations, each with a business and a customer, and a draft for org A."""
    ids: dict[str, uuid.UUID] = {}
    with engine.begin() as c:
        for tag in ("a", "b"):
            org = c.execute(
                text("INSERT INTO organizations (name) VALUES (:n) RETURNING id"), {"n": tag}
            ).scalar_one()
            user = c.execute(
                text(
                    "INSERT INTO users (email, password_hash, display_name) VALUES (:e, '$argon2id$x', 'U') RETURNING id"
                ),
                {"e": f"{tag}-{uuid.uuid4().hex[:6]}@test.invalid"},
            ).scalar_one()
            c.execute(
                text("INSERT INTO memberships (org_id, user_id) VALUES (:o, :u)"),
                {"o": org, "u": user},
            )
            business = c.execute(
                text(
                    "INSERT INTO businesses (org_id, legal_name, address_line1, city, state_code, postal_code) "
                    "VALUES (:o, 'B', 'L1', 'C', '29', '560001') RETURNING id"
                ),
                {"o": org},
            ).scalar_one()
            customer = c.execute(
                text(
                    "INSERT INTO customers (org_id, business_id, display_name) VALUES (:o, :b, 'C') RETURNING id"
                ),
                {"o": org, "b": business},
            ).scalar_one()
            ids.update(
                {
                    f"org_{tag}": org,
                    f"user_{tag}": user,
                    f"business_{tag}": business,
                    f"customer_{tag}": customer,
                }
            )
        ids["draft"] = c.execute(
            text(
                "INSERT INTO documents (org_id, business_id, customer_id, created_by) "
                "VALUES (:o, :b, :c, :u) RETURNING id"
            ),
            {"o": ids["org_a"], "b": ids["business_a"], "c": ids["customer_a"], "u": ids["user_a"]},
        ).scalar_one()
    return ids


def _finalize(engine: Engine, ids: dict[str, uuid.UUID]) -> uuid.UUID:
    with engine.begin() as c:
        series = c.execute(
            text(
                "INSERT INTO number_series (org_id, business_id, financial_year) VALUES (:o, :b, '26-27') RETURNING id"
            ),
            {"o": ids["org_a"], "b": ids["business_a"]},
        ).scalar_one()
        c.execute(
            text(
                "INSERT INTO document_lines (org_id, document_id, position, description, quantity, unit_price) "
                "VALUES (:o, :d, 1, 'Line', 1, 100)"
            ),
            {"o": ids["org_a"], "d": ids["draft"]},
        )
        # The draft → finalized transition is allowed (DB-03).
        c.execute(
            text(
                "UPDATE documents SET status = 'finalized', number_series_id = :s, sequence_no = 1, "
                "document_number = 'INV/26-27/00001', issue_date = DATE '2026-11-25', "
                "finalized_at = now(), finalized_by = :u, version = version + 1 WHERE id = :d"
            ),
            {"s": series, "u": ids["user_a"], "d": ids["draft"]},
        )
    return series


def _sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None)


def test_db_02_document_cannot_use_another_business_customer(migrator_engine: Engine) -> None:
    ids = _seed(migrator_engine)
    with pytest.raises(IntegrityError) as raised, migrator_engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO documents (org_id, business_id, customer_id, created_by) VALUES (:o, :b, :c, :u)"
            ),
            {"o": ids["org_a"], "b": ids["business_a"], "c": ids["customer_b"], "u": ids["user_a"]},
        )
    assert "documents_customer_fk" in str(raised.value)


def test_db_02_document_cannot_mix_organizations(migrator_engine: Engine) -> None:
    ids = _seed(migrator_engine)
    with pytest.raises(IntegrityError) as raised, migrator_engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO documents (org_id, business_id, customer_id, created_by) VALUES (:o, :b, :c, :u)"
            ),
            {"o": ids["org_b"], "b": ids["business_a"], "c": ids["customer_a"], "u": ids["user_b"]},
        )
    assert "documents_business_fk" in str(raised.value)


@pytest.mark.parametrize(
    ("kind", "value", "ok"),
    [("amount", "1000.00", True), ("amount", "1000.01", False), ("percent", "100.01", False),
     ("none", "1.00", False), ("none", None, True),
     # As documented (06 §3.10), the check lets NULL through for percent and amount, because
     # NULL > 0 is unknown and CHECK accepts unknown; the API rejects it (field code required).
     # Recorded in PROGRESS.md known issues; changing the constraint needs approval (15 §7).
     ("percent", None, True)],
)  # fmt: skip
def test_db_02_discount_check(
    migrator_engine: Engine, kind: str, value: str | None, ok: bool
) -> None:
    ids = _seed(migrator_engine)
    statement = text(
        "INSERT INTO document_lines (org_id, document_id, position, description, quantity, unit_price, "
        "discount_type, discount_value) VALUES (:o, :d, 1, 'L', 1, 1000.00, :t, CAST(:v AS numeric))"
    )
    params = {"o": ids["org_a"], "d": ids["draft"], "t": kind, "v": value}
    if ok:
        with migrator_engine.begin() as c:
            c.execute(statement, params)
    else:
        with pytest.raises(IntegrityError) as raised, migrator_engine.begin() as c:
            c.execute(statement, params)
        assert "document_lines_discount_ck" in str(raised.value)


def test_db_02_amount_discount_check_rounds_half_up(migrator_engine: Engine) -> None:
    # round(1.005 x 1.00, 2) = 1.01 in PostgreSQL (half away from zero), like calc's ROUND_HALF_UP.
    ids = _seed(migrator_engine)
    with migrator_engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO document_lines (org_id, document_id, position, description, quantity, unit_price, "
                "discount_type, discount_value) VALUES (:o, :d, 1, 'L', 1.005, 1.00, 'amount', 1.01)"
            ),
            {"o": ids["org_a"], "d": ids["draft"]},
        )


def test_db_02_state_check_rejects_finalised_without_number(migrator_engine: Engine) -> None:
    ids = _seed(migrator_engine)
    with pytest.raises(IntegrityError) as raised, migrator_engine.begin() as c:
        c.execute(
            text("UPDATE documents SET status = 'finalized' WHERE id = :d"), {"d": ids["draft"]}
        )
    assert "documents_state_ck" in str(raised.value)


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE documents SET notes = 'x' WHERE id = :d",
        "UPDATE documents SET status = 'draft', number_series_id = NULL, sequence_no = NULL, "
        "document_number = NULL, issue_date = NULL, finalized_at = NULL, finalized_by = NULL WHERE id = :d",
        "DELETE FROM documents WHERE id = :d",
    ],
)
def test_db_03_finalised_document_is_immutable(migrator_engine: Engine, statement: str) -> None:
    ids = _seed(migrator_engine)
    _finalize(migrator_engine, ids)
    with pytest.raises(DBAPIError) as raised, migrator_engine.begin() as c:
        c.execute(text(statement), {"d": ids["draft"]})
    assert _sqlstate(raised.value) == RESTRICT_VIOLATION


def test_db_03_draft_cannot_change_organization_or_type(migrator_engine: Engine) -> None:
    ids = _seed(migrator_engine)
    with pytest.raises(DBAPIError) as raised, migrator_engine.begin() as c:
        c.execute(
            text("UPDATE documents SET business_id = :b WHERE id = :d"),
            {"b": ids["business_b"], "d": ids["draft"]},
        )
    assert _sqlstate(raised.value) in (RESTRICT_VIOLATION, "23503")
    with migrator_engine.begin() as c:  # an ordinary draft edit is allowed
        c.execute(text("UPDATE documents SET notes = 'ok' WHERE id = :d"), {"d": ids["draft"]})


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO document_lines (org_id, document_id, position, description, quantity, unit_price) "
        "VALUES (:o, :d, 2, 'L', 1, 1)",
        "UPDATE document_lines SET description = 'changed' WHERE document_id = :d",
        "DELETE FROM document_lines WHERE document_id = :d",
    ],
)
def test_db_04_lines_of_finalised_document_are_immutable(
    migrator_engine: Engine, statement: str
) -> None:
    ids = _seed(migrator_engine)
    _finalize(migrator_engine, ids)
    with pytest.raises(DBAPIError) as raised, migrator_engine.begin() as c:
        c.execute(text(statement), {"o": ids["org_a"], "d": ids["draft"]})
    assert _sqlstate(raised.value) == RESTRICT_VIOLATION


def test_deleting_a_draft_cascades_to_its_lines(migrator_engine: Engine) -> None:
    ids = _seed(migrator_engine)
    with migrator_engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO document_lines (org_id, document_id, position, description, quantity, unit_price) "
                "VALUES (:o, :d, 1, 'L', 1, 1)"
            ),
            {"o": ids["org_a"], "d": ids["draft"]},
        )
        c.execute(text("DELETE FROM documents WHERE id = :d"), {"d": ids["draft"]})
        assert c.execute(text("SELECT count(*) FROM document_lines")).scalar_one() == 0


def test_templates_seed_row(migrator_engine: Engine) -> None:
    with migrator_engine.connect() as c:
        row = c.execute(text("SELECT * FROM templates")).mappings().one()
    assert (
        row["id"],
        row["code"],
        row["version"],
        row["doc_type"],
        row["name"],
        row["tier"],
        row["is_active"],
    ) == ("classic@1", "classic", 1, "invoice", "Classic", "free", True)
