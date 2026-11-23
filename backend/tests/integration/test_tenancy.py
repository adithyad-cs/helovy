"""IT-TEN-01 to IT-TEN-03 (docs/11 §2.5) for the endpoints that exist so far.

Organization B's session calls every org-scoped endpoint with organization A's IDs and gets
404 ``not_found`` every time, with the same response shape as a truly missing ID. Documents
(E-14 to E-23) are added with M3 to M6. Also run before the demonstration (DC-19).
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from tests.factories import (
    F01,
    ApiSession,
    create_business,
    create_customer,
    create_draft,
    new_client,
    signed_in,
    trusted,
)

MISSING = str(uuid.uuid4())


@pytest.fixture
def two_orgs(client: TestClient) -> tuple[ApiSession, ApiSession, dict[str, str]]:
    org_a = trusted(client)
    business_a = create_business(org_a)
    customer_a = create_customer(org_a, business_a["id"])
    draft_a = create_draft(org_a, business_a["id"], customer_a["id"], lines=[F01])
    org_b = signed_in(client.app, org_name="Isolation Check Org")  # type: ignore[arg-type]
    create_business(org_b)  # B has its own business, so 404s cannot come from "no business"
    return (
        org_a,
        org_b,
        {
            "business": business_a["id"],
            "customer": customer_a["id"],
            "document": draft_a["id"],
        },
    )


def _comparable(body: dict[str, object]) -> dict[str, object]:
    return {k: v for k, v in body.items() if k not in ("instance", "request_id")}


def _requests(ids: dict[str, str]) -> list[tuple[str, str, dict[str, object]]]:
    business, customer, document = ids["business"], ids["customer"], ids["document"]
    return [
        ("GET", f"/api/v1/businesses/{business}", {}),
        ("PATCH", f"/api/v1/businesses/{business}", {"json": {"city": "X"}, "headers": {"If-Match": '"1"'}}),
        ("GET", f"/api/v1/businesses/{business}/customers", {}),
        ("POST", f"/api/v1/businesses/{business}/customers", {"json": {"display_name": "Intruder"}}),
        ("GET", f"/api/v1/businesses/{business}/customers/{customer}", {}),
        (
            "PATCH",
            f"/api/v1/businesses/{business}/customers/{customer}",
            {"json": {"city": "X"}, "headers": {"If-Match": '"1"'}},
        ),
        ("POST", f"/api/v1/businesses/{business}/calculate", {"json": {"lines": []}}),
        ("POST", f"/api/v1/businesses/{business}/documents", {"json": {"customer_id": customer}}),
        ("GET", f"/api/v1/documents/{document}", {}),
        ("PATCH", f"/api/v1/documents/{document}", {"json": {"notes": "x"}, "headers": {"If-Match": '"1"'}}),
        ("GET", f"/api/v1/documents/{document}/preview.pdf", {}),
        ("DELETE", f"/api/v1/documents/{document}", {"headers": {"If-Match": '"1"'}}),
    ]  # fmt: skip


def test_it_ten_01_foreign_ids_are_404_like_missing_ids(
    two_orgs: tuple[ApiSession, ApiSession, dict[str, str]],
) -> None:
    org_a, org_b, ids_a = two_orgs
    missing = {"business": MISSING, "customer": MISSING, "document": MISSING}
    for (method, url, kwargs), (_, missing_url, _) in zip(
        _requests(ids_a), _requests(missing), strict=True
    ):
        foreign = org_b.request(method, url, **kwargs)  # type: ignore[arg-type]
        absent = org_b.request(method, missing_url, **kwargs)  # type: ignore[arg-type]
        assert foreign.status_code == 404, (method, url, foreign.text)
        assert absent.status_code == 404
        assert foreign.json()["code"] == "not_found"
        assert _comparable(foreign.json()) | {"instance": None} == _comparable(absent.json()) | {
            "instance": None
        }
        assert set(foreign.headers) == set(absent.headers)
    # Organization A's records are unchanged.
    business = org_a.get(f"/api/v1/businesses/{ids_a['business']}").json()
    assert business["city"] == "Bengaluru" and business["version"] == 1
    document = org_a.get(f"/api/v1/documents/{ids_a['document']}").json()
    assert document["version"] == 1 and document["notes"] is None


def test_it_ten_01_business_owner_still_sees_own_records(
    two_orgs: tuple[ApiSession, ApiSession, dict[str, str]],
) -> None:
    org_a, _, ids_a = two_orgs
    for method, url, kwargs in _requests(ids_a):
        if method == "GET":
            assert org_a.request(method, url, **kwargs).status_code == 200  # type: ignore[arg-type]


def test_it_ten_02_customer_list_never_shows_other_orgs(client: TestClient) -> None:
    org_a = trusted(client)
    business_a = create_business(org_a)
    create_customer(org_a, business_a["id"], display_name="Org A Customer (Demo)")
    org_b = signed_in(client.app)  # type: ignore[arg-type]
    business_b = create_business(org_b)
    create_customer(org_b, business_b["id"], display_name="Org B Customer (Demo)")
    listed_b = org_b.get(f"/api/v1/businesses/{business_b['id']}/customers").json()["items"]
    assert [c["display_name"] for c in listed_b] == ["Org B Customer (Demo)"]
    assert (
        org_b.get(f"/api/v1/businesses/{business_b['id']}/customers", params={"q": "Org A"}).json()[
            "items"
        ]
        == []
    )


def test_it_ten_02_me_shows_only_the_sessions_business(client: TestClient) -> None:
    org_a = trusted(client)
    create_business(org_a)
    org_b = signed_in(client.app)  # type: ignore[arg-type]
    assert org_b.get("/api/v1/auth/me").json()["business"] is None


def test_it_ten_03_database_rejects_cross_tenant_customer(
    client: TestClient, migrator_engine: Engine
) -> None:
    org_a = trusted(client)
    business_a = create_business(org_a)
    org_b = signed_in(client.app)  # type: ignore[arg-type]
    with pytest.raises(IntegrityError) as raised, migrator_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO customers (org_id, business_id, display_name) VALUES (:o, :b, 'x')"),
            {"o": str(org_b.account.org_id), "b": business_a["id"]},
        )
    assert "customers_business_fk" in str(raised.value)


def test_second_browser_cannot_reuse_another_sessions_csrf_token(client: TestClient) -> None:
    org_a = trusted(client)
    business_a = create_business(org_a)
    intruder = new_client(client.app)  # type: ignore[arg-type]
    response = intruder.post(
        f"/api/v1/businesses/{business_a['id']}/customers",
        json={"display_name": "x"},
        headers={"Origin": client.app.state.settings.app_origin, "X-CSRF-Token": org_a.csrf},  # type: ignore[attr-defined]
    )
    assert response.status_code == 403
