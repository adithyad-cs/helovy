"""IT-BIZ-01 to IT-BIZ-03 (docs/11 §2.2): E-06, E-07, E-08 and the business summary in E-05."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from tests.factories import BUSINESS, create_business, trusted

BUSINESSES = "/api/v1/businesses"


def _events(engine: Engine, event_type: str) -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT subject_id, details FROM audit_events WHERE event_type = :t ORDER BY id"),
            {"t": event_type},
        ).mappings()
        return [dict(row) for row in rows]


def test_it_biz_01_create_once_then_409(client: TestClient, migrator_engine: Engine) -> None:
    session = trusted(client)
    response = session.post(BUSINESSES, json=BUSINESS)
    assert response.status_code == 201
    body = response.json()
    assert response.headers["etag"] == '"1"'
    assert response.headers["location"] == f"{BUSINESSES}/{body['id']}"
    assert body == {
        **BUSINESS,
        "id": body["id"],
        "trade_name": None,
        "state_name": "Karnataka",
        "country_code": "IN",
        "gstin": None,
        "version": 1,
        "created_at": "2026-11-25T05:42:10Z",
        "updated_at": "2026-11-25T05:42:10Z",
    }
    created = _events(migrator_engine, "business.created")
    assert len(created) == 1
    assert created[0]["details"] == {
        "fields": sorted(BUSINESS)  # field names only, never values
    }

    second = session.post(BUSINESSES, json={**BUSINESS, "legal_name": "Another (Demo)"})
    assert second.status_code == 409
    assert second.json()["code"] == "business_already_exists"

    me = client.get("/api/v1/auth/me").json()
    assert me["business"] == {"id": body["id"], "legal_name": BUSINESS["legal_name"]}


def test_it_biz_01_read_with_etag_and_head(client: TestClient) -> None:
    session = trusted(client)
    business = create_business(session)
    response = session.get(f"{BUSINESSES}/{business['id']}")
    assert response.status_code == 200
    assert response.headers["etag"] == '"1"'
    assert response.json() == business
    head = client.head(f"{BUSINESSES}/{business['id']}")
    assert head.status_code == 200
    assert head.headers["etag"] == '"1"'
    assert head.content == b""


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("postal_code", "012345", "invalid_format"),
        ("postal_code", "56003", "invalid_format"),
        ("state_code", "25", "invalid_choice"),
        ("state_code", "99", "invalid_choice"),
        ("gstin", "29ABCDE1234F1Z", "invalid_format"),
        ("gstin", "29ABCDE1234F0Z5", "invalid_format"),
        ("phone", "12345", "invalid_format"),
        ("phone", "+91 80 abc", "invalid_format"),
        ("email", "not-an-email", "invalid_format"),
        ("legal_name", "", "required"),
        ("legal_name", None, "not_null"),
        ("legal_name", "x" * 201, "too_long"),
        ("city", "x" * 101, "too_long"),
        ("legal_name", "Bad\u0000name", "invalid_format"),
        ("legal_name", "Two\nlines", "invalid_format"),
        ("country_code", "US", "invalid_choice"),
        ("legal_name", 42, "must_be_string"),
    ],
)
def test_it_biz_02_validation_pointers(
    client: TestClient, field: str, value: object, code: str
) -> None:
    session = trusted(client)
    response = session.post(BUSINESSES, json={**BUSINESS, field: value})
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "validation_failed"
    assert [(e["pointer"], e["code"]) for e in body["errors"]] == [(f"/{field}", code)]


@pytest.mark.parametrize(
    "missing", ["legal_name", "address_line1", "city", "state_code", "postal_code"]
)
def test_it_biz_02_required_fields(client: TestClient, missing: str) -> None:
    payload = {k: v for k, v in BUSINESS.items() if k != missing}
    response = trusted(client).post(BUSINESSES, json=payload)
    assert response.status_code == 422
    assert [(e["pointer"], e["code"]) for e in response.json()["errors"]] == [
        (f"/{missing}", "required")
    ]


def test_it_biz_02_gstin_state_mismatch_and_normalisation(client: TestClient) -> None:
    session = trusted(client)
    mismatch = session.post(BUSINESSES, json={**BUSINESS, "gstin": "27ABCDE1234F1Z5"})
    assert mismatch.status_code == 422
    assert [(e["pointer"], e["code"]) for e in mismatch.json()["errors"]] == [
        ("/gstin", "state_mismatch")
    ]
    ok = session.post(
        BUSINESSES,
        json={
            **BUSINESS,
            "gstin": " 29abcde1234f1z5 ",
            "trade_name": "  Lotus Lane  ",
            "phone": "",
        },
    )
    assert ok.status_code == 201
    body = ok.json()
    assert body["gstin"] == "29ABCDE1234F1Z5"
    assert body["trade_name"] == "Lotus Lane"
    assert body["phone"] is None  # empty optional text becomes null


def test_it_biz_02_unknown_field_and_org_id_are_rejected(client: TestClient) -> None:
    response = trusted(client).post(BUSINESSES, json={**BUSINESS, "org_id": "x", "version": 3})
    assert response.status_code == 422
    assert sorted((e["pointer"], e["code"]) for e in response.json()["errors"]) == [
        ("/org_id", "unknown_field"),
        ("/version", "unknown_field"),
    ]


def test_it_biz_03_patch_concurrency(client: TestClient, migrator_engine: Engine) -> None:
    session = trusted(client)
    business = create_business(session)
    url = f"{BUSINESSES}/{business['id']}"

    missing = session.patch(url, json={"phone": "+91 80 1111 2222"})
    assert missing.status_code == 428
    assert missing.json()["code"] == "precondition_required"

    malformed = session.patch(url, json={"phone": "+91 80 1111 2222"}, headers={"If-Match": "1"})
    assert malformed.status_code == 400

    ok = session.patch(url, json={"phone": "+91 80 1111 2222"}, headers={"If-Match": '"1"'})
    assert ok.status_code == 200
    assert ok.headers["etag"] == '"2"'
    assert ok.json()["phone"] == "+91 80 1111 2222"
    assert ok.json()["version"] == 2

    stale = session.patch(url, json={"city": "Mysuru"}, headers={"If-Match": '"1"'})
    assert stale.status_code == 412
    assert stale.json()["code"] == "version_mismatch"
    assert session.get(url).json()["city"] == "Bengaluru"  # nothing stored

    updated = _events(migrator_engine, "business.updated")
    assert [e["details"] for e in updated] == [{"fields": ["phone"]}]


def test_patch_semantics_null_clears_and_required_cannot_be_null(client: TestClient) -> None:
    session = trusted(client)
    business = create_business(session, trade_name="Lotus Lane")
    url = f"{BUSINESSES}/{business['id']}"
    cleared = session.patch(url, json={"trade_name": None}, headers={"If-Match": '"1"'})
    assert cleared.status_code == 200
    assert cleared.json()["trade_name"] is None
    assert cleared.json()["address_line2"] == "Indiranagar"  # absent fields are unchanged

    not_null = session.patch(url, json={"legal_name": None}, headers={"If-Match": '"2"'})
    assert not_null.status_code == 422
    assert [(e["pointer"], e["code"]) for e in not_null.json()["errors"]] == [
        ("/legal_name", "not_null")
    ]

    # The GSTIN is checked against the stored state when only one of them changes.
    mismatch = session.patch(url, json={"gstin": "27ABCDE1234F1Z5"}, headers={"If-Match": '"2"'})
    assert mismatch.json()["errors"][0]["code"] == "state_mismatch"

    unchanged = session.patch(url, json={"city": "Bengaluru"}, headers={"If-Match": '"2"'})
    assert unchanged.status_code == 200
    assert unchanged.headers["etag"] == '"2"'  # nothing changed: same version


def test_malformed_business_id_is_404(client: TestClient) -> None:
    session = trusted(client)
    for bad in ("not-a-uuid", "2C4E6A8B-0D1F-4A3C-9E5B-7D9F1B3D5E7A", "123"):
        response = session.get(f"{BUSINESSES}/{bad}")
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"


def test_business_endpoints_need_a_session(client: TestClient) -> None:
    assert client.get(f"{BUSINESSES}/2c4e6a8b-0d1f-4a3c-9e5b-7d9f1b3d5e7a").status_code == 401
