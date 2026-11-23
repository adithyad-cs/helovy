"""IT-DOC-01 to IT-DOC-03 (docs/11 §2.2): drafts (E-15, E-17, E-18, E-19), E-14, E-13."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.core.clock import FrozenClock
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

FIXTURES: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "invoice_fixture.json").read_text("utf-8")
)


@pytest.fixture
def owner(client: TestClient) -> tuple[ApiSession, str, str]:
    session = trusted(client)
    business = create_business(session)
    customer = create_customer(session, business["id"])
    return session, business["id"], customer["id"]


def _doc(document_id: str) -> str:
    return f"/api/v1/documents/{document_id}"


def test_it_doc_01_create_patch_get(owner: tuple[ApiSession, str, str]) -> None:
    session, business_id, customer_id = owner
    response = session.post(
        f"/api/v1/businesses/{business_id}/documents", json={"customer_id": customer_id}
    )
    assert response.status_code == 201
    draft = response.json()
    assert response.headers["etag"] == '"1"'
    assert response.headers["location"] == _doc(draft["id"])
    assert draft["status"] == "draft" and draft["template_id"] == "classic@1"
    assert draft["lines"] == [] and draft["number"] is None and draft["pdf"] is None
    assert draft["totals"] == {
        "gross_total": "0.00",
        "discount_total": "0.00",
        "grand_total": "0.00",
    }
    assert draft["customer"] == {"id": customer_id, "display_name": "Riverstone Consulting (Demo)"}

    saved = session.patch(
        _doc(draft["id"]),
        json={"lines": [F01, F02], "reference": "PO-4471", "due_date": "2026-12-10",
              "terms": "Payment within 15 days of the invoice date.\\nThank you."},
        headers={"If-Match": '"1"'},
    )  # fmt: skip
    assert saved.status_code == 200, saved.text
    assert saved.headers["etag"] == '"2"'
    body = saved.json()
    assert [
        (line["position"], line["gross"], line["discount"], line["line_total"])
        for line in body["lines"]
    ] == [
        (1, "2000.00", "200.00", "1800.00"),
        (2, "999.99", "99.99", "900.00"),
    ]
    assert body["lines"][0]["quantity"] == "2.500" and body["lines"][0]["discount_value"] == "10.00"
    assert body["totals"] == FIXTURES["documents"]["F-03"]["expected"]
    assert body["calc_version"] == "calc-1.0.0"
    assert body["version"] == 2 and body["due_date"] == "2026-12-10"

    fetched = session.get(_doc(draft["id"]))
    assert fetched.status_code == 200 and fetched.headers["etag"] == '"2"'
    assert fetched.json() == body  # persisted: identical after a reload

    # Full line replacement: the new set replaces both lines.
    replaced = session.patch(_doc(draft["id"]), json={"lines": [F02]}, headers={"If-Match": '"2"'})
    assert [line["position"] for line in replaced.json()["lines"]] == [1]
    assert replaced.json()["totals"]["grand_total"] == "900.00"
    assert replaced.json()["reference"] == "PO-4471"  # absent fields unchanged


def test_draft_stores_inputs_only(
    owner: tuple[ApiSession, str, str], migrator_engine: Engine
) -> None:
    session, business_id, customer_id = owner
    create_draft(session, business_id, customer_id, lines=[F01])
    with migrator_engine.connect() as connection:
        columns = set(connection.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name IN ('documents', 'document_lines')"
        )).scalars())  # fmt: skip
    assert not columns & {"gross", "discount", "line_total", "grand_total", "gross_total"}


def test_patch_preconditions(owner: tuple[ApiSession, str, str]) -> None:
    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id)
    assert session.patch(_doc(draft["id"]), json={"notes": "x"}).status_code == 428
    assert (
        session.patch(
            _doc(draft["id"]), json={"notes": "x"}, headers={"If-Match": '"7"'}
        ).status_code
        == 412
    )
    assert (
        session.patch(_doc(draft["id"]), json={"notes": None}, headers={"If-Match": '"1"'}).json()[
            "notes"
        ]
        is None
    )


@pytest.mark.parametrize(
    ("payload", "pointer", "code"),
    [
        ({"lines": [{**F01, "quantity": "0"}]}, "/lines/0/quantity", "out_of_range"),
        ({"lines": [{**F01, "quantity": "1.0005"}]}, "/lines/0/quantity", "too_many_decimals"),
        ({"lines": [{**F01, "quantity": 2.5}]}, "/lines/0/quantity", "must_be_string"),
        ({"lines": [F01, {**F02, "discount_value": "1000.01"}]}, "/lines/1/discount_value", "exceeds_gross"),
        ({"lines": [{**F01, "description": "  "}]}, "/lines/0/description", "required"),
        ({"lines": [{**F01, "description": "x" * 501}]}, "/lines/0/description", "too_long"),
        ({"lines": [{**F01, "discount_type": "bogus"}]}, "/lines/0/discount_type", "invalid_choice"),
        ({"lines": [{**F01, "discount_type": "none"}]}, "/lines/0/discount_value", "invalid_choice"),
        ({"lines": [{**F01, "discount_value": None}]}, "/lines/0/discount_value", "required"),
        ({"lines": [{**F01, "gross": "1"}]}, "/lines/0/gross", "unknown_field"),
        ({"lines": [F01] * 201}, "/lines", "too_many_lines"),
        ({"lines": [{**F01, "quantity": "1000000", "unit_price": "10000000.00", "discount_type": "none",
                     "discount_value": None}]}, "/lines", "total_too_large"),
        ({"due_date": "2026-02-30"}, "/due_date", "invalid_format"),
        ({"due_date": "2101-01-01"}, "/due_date", "out_of_range"),
        ({"reference": "x" * 101}, "/reference", "too_long"),
        ({"customer_id": None}, "/customer_id", "not_null"),
        ({"template_id": "minimal@1"}, "/template_id", "not_found"),
        ({"lines": None}, "/lines", "not_null"),
    ],
)  # fmt: skip
def test_draft_validation(
    owner: tuple[ApiSession, str, str], payload: dict[str, Any], pointer: str, code: str
) -> None:
    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id)
    response = session.patch(_doc(draft["id"]), json=payload, headers={"If-Match": '"1"'})
    assert response.status_code == 422, response.text
    errors = response.json()["errors"]
    assert (errors[0]["pointer"], errors[0]["code"]) == (pointer, code), errors
    assert session.get(_doc(draft["id"])).json()["version"] == 1  # nothing stored


def test_create_needs_a_customer_of_this_business(
    owner: tuple[ApiSession, str, str], client: TestClient
) -> None:
    session, business_id, _ = owner
    url = f"/api/v1/businesses/{business_id}/documents"
    missing = session.post(url, json={})
    assert (missing.json()["errors"][0]["pointer"], missing.json()["errors"][0]["code"]) == (
        "/customer_id",
        "required",
    )
    other = trusted_other_customer(client)
    foreign = session.post(url, json={"customer_id": other})
    assert (foreign.json()["errors"][0]["pointer"], foreign.json()["errors"][0]["code"]) == (
        "/customer_id",
        "not_found",
    )
    bad = session.post(url, json={"customer_id": "not-a-uuid"})
    assert bad.json()["errors"][0]["code"] == "not_found"


def trusted_other_customer(client: TestClient) -> str:
    from tests.factories import signed_in

    other = signed_in(client.app)  # type: ignore[arg-type]
    business = create_business(other)
    return str(create_customer(other, business["id"])["id"])


def test_inactive_template_is_refused(
    owner: tuple[ApiSession, str, str], migrator_engine: Engine
) -> None:
    session, business_id, customer_id = owner
    with migrator_engine.begin() as connection:
        connection.execute(text("UPDATE templates SET is_active = false WHERE id = 'classic@1'"))
    try:
        response = session.post(
            f"/api/v1/businesses/{business_id}/documents", json={"customer_id": customer_id}
        )
        assert response.status_code == 422
        assert response.json()["errors"][0]["code"] == "inactive"
    finally:
        with migrator_engine.begin() as connection:
            connection.execute(text("UPDATE templates SET is_active = true WHERE id = 'classic@1'"))


def test_it_doc_02_delete_draft_then_finalised_is_409(
    owner: tuple[ApiSession, str, str], migrator_engine: Engine
) -> None:
    session, business_id, customer_id = owner
    draft = create_draft(session, business_id, customer_id, lines=[F01])
    assert session.delete(_doc(draft["id"])).status_code == 428
    assert session.delete(_doc(draft["id"]), headers={"If-Match": '"9"'}).status_code == 412
    deleted = session.delete(_doc(draft["id"]), headers={"If-Match": '"1"'})
    assert deleted.status_code == 204
    assert session.get(_doc(draft["id"])).status_code == 404
    with migrator_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM document_lines")).scalar_one() == 0

    other = create_draft(session, business_id, customer_id, lines=[F01])
    mark_finalized_in_database(migrator_engine, other["id"])
    refused = session.delete(_doc(other["id"]), headers={"If-Match": '"2"'})
    assert refused.status_code == 409
    assert refused.json()["code"] == "document_not_draft"
    edit = session.patch(_doc(other["id"]), json={"notes": "x"}, headers={"If-Match": '"2"'})
    assert edit.status_code == 409 and edit.json()["code"] == "document_not_draft"


def test_it_doc_03_calculate(owner: tuple[ApiSession, str, str], clock: FrozenClock) -> None:
    session, business_id, _ = owner
    url = f"/api/v1/businesses/{business_id}/calculate"
    numeric = ("quantity", "unit_price", "discount_type", "discount_value")
    lines = [{k: v for k, v in line.items() if k in numeric} for line in (F01, F02)]
    response = session.post(url, json={"lines": lines})
    assert response.status_code == 200
    assert response.json() == {
        "calc_version": "calc-1.0.0",
        "lines": [
            {"position": 1, "gross": "2000.00", "discount": "200.00", "line_total": "1800.00"},
            {"position": 2, "gross": "999.99", "discount": "99.99", "line_total": "900.00"},
        ],
        "totals": {"gross_total": "2999.99", "discount_total": "299.99", "grand_total": "2700.00"},
    }
    for name, case in FIXTURES["lines"].items():
        single = session.post(url, json={"lines": [case["input"]]}).json()["lines"][0]
        assert {k: single[k] for k in ("gross", "discount", "line_total")} == case["expected"], name

    empty = session.post(url, json={"lines": []}).json()
    assert empty["lines"] == [] and empty["totals"]["grand_total"] == "0.00"
    number = session.post(url, json={"lines": [{**lines[0], "quantity": 2.5}]})
    assert number.status_code == 422
    assert number.json()["errors"][0] == {
        "pointer": "/lines/0/quantity",
        "code": "must_be_string",
        "message": 'Send this value as a string, for example "2.5".',
    }

    # 60 per minute per session. Counted so far: the F-01+F-02 call, one per fixture line and
    # the empty call (the 422 is refused by validation before it is counted).
    counted = 1 + len(FIXTURES["lines"]) + 1
    for _ in range(60 - counted):
        assert session.post(url, json={"lines": []}).status_code == 200
    limited = session.post(url, json={"lines": []})
    assert limited.status_code == 429
    assert limited.json()["code"] == "rate_limited"
    assert int(limited.headers["retry-after"]) >= 1
    clock.advance(timedelta(seconds=61))
    assert session.post(url, json={"lines": []}).status_code == 200


def test_it_doc_03_validation_counts_toward_nothing_but_needs_business(
    owner: tuple[ApiSession, str, str],
) -> None:
    session, _, _ = owner
    response = session.post(
        "/api/v1/businesses/4e6a8c0d-2f3b-4c5e-9a7d-9f1b3d5f7a9c/calculate", json={"lines": []}
    )
    assert response.status_code == 404


def test_e13_templates(owner: tuple[ApiSession, str, str]) -> None:
    session, _, _ = owner
    response = session.get("/api/v1/templates", params={"doc_type": "invoice"})
    assert response.status_code == 200
    assert response.json() == {
        "items": [{"id": "classic@1", "code": "classic", "version": 1, "name": "Classic",
                   "description": "A clean, traditional A4 invoice layout.", "tier": "free", "doc_type": "invoice"}]
    }  # fmt: skip
    assert session.get("/api/v1/templates").json()["items"][0]["id"] == "classic@1"
    wrong = session.get("/api/v1/templates", params={"doc_type": "receipt"})
    assert wrong.status_code == 422 and wrong.json()["errors"][0]["code"] == "invalid_choice"
