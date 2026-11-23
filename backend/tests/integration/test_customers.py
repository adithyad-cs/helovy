"""IT-CUS-01, IT-CUS-02 (docs/11 §2.2): E-09 to E-12."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.core.clock import FrozenClock
from tests.factories import ApiSession, create_business, create_customer, trusted


def _url(business_id: str, customer_id: str | None = None) -> str:
    base = f"/api/v1/businesses/{business_id}/customers"
    return f"{base}/{customer_id}" if customer_id else base


@pytest.fixture
def owner(client: TestClient) -> tuple[ApiSession, str]:
    session = trusted(client)
    return session, create_business(session)["id"]


def test_create_returns_201_with_etag_location_and_audit(
    owner: tuple[ApiSession, str], migrator_engine: Engine
) -> None:
    session, business_id = owner
    response = session.post(
        _url(business_id),
        json={
            "display_name": "Riverstone Consulting (Demo)",
            "contact_name": "A. Kumar",
            "email": "ap@riverstone.invalid",
            "address_line1": "4th Floor, Sample Towers",
            "city": "Pune",
            "state_code": "27",
            "postal_code": "411001",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert response.headers["etag"] == '"1"'
    assert response.headers["location"] == _url(business_id, body["id"])
    assert body["state_name"] == "Maharashtra"
    assert body["phone"] is None and body["gstin"] is None and body["country_code"] == "IN"
    with migrator_engine.connect() as connection:
        details = connection.execute(
            text("SELECT details FROM audit_events WHERE event_type = 'customer.created'")
        ).scalar_one()
    assert details == {
        "fields": ["address_line1", "city", "contact_name", "display_name", "email",
                   "postal_code", "state_code"]
    }  # fmt: skip


def test_only_display_name_is_required(owner: tuple[ApiSession, str]) -> None:
    session, business_id = owner
    assert (
        session.post(
            _url(business_id), json={"display_name": "Saffron Leaf Foods (Demo)"}
        ).status_code
        == 201
    )
    missing = session.post(_url(business_id), json={"city": "Chennai"})
    assert [(e["pointer"], e["code"]) for e in missing.json()["errors"]] == [
        ("/display_name", "required")
    ]


@pytest.mark.parametrize(
    ("fields", "pointer", "code"),
    [
        ({"gstin": "27ABCDE1234F1Z5", "state_code": "29"}, "/gstin", "state_mismatch"),
        ({"postal_code": "012345"}, "/postal_code", "invalid_format"),
        ({"state_code": "28"}, "/state_code", "invalid_choice"),
        ({"contact_name": "x" * 121}, "/contact_name", "too_long"),
        ({"email": "a@b"}, "/email", "invalid_format"),
    ],
)
def test_customer_validation(
    owner: tuple[ApiSession, str], fields: dict[str, str], pointer: str, code: str
) -> None:
    session, business_id = owner
    response = session.post(_url(business_id), json={"display_name": "X (Demo)", **fields})
    assert response.status_code == 422
    assert [(e["pointer"], e["code"]) for e in response.json()["errors"]] == [(pointer, code)]


def test_gstin_without_state_is_allowed(owner: tuple[ApiSession, str]) -> None:
    session, business_id = owner
    response = session.post(
        _url(business_id), json={"display_name": "X (Demo)", "gstin": "27ABCDE1234F1Z5"}
    )
    assert response.status_code == 201


def test_it_cus_01_list_order_prefix_search_and_pagination(
    owner: tuple[ApiSession, str], clock: FrozenClock
) -> None:
    session, business_id = owner
    names = ["Harbour Line Logistics (Demo)", "harbour view (Demo)", "Riverstone (Demo)",
             "Saffron Leaf Foods (Demo)", "100% Cotton_Co (Demo)"]  # fmt: skip
    for name in names:
        create_customer(session, business_id, display_name=name)
        clock.advance(timedelta(seconds=1))

    everything = session.get(_url(business_id)).json()
    assert [i["display_name"] for i in everything["items"]] == list(reversed(names))
    assert everything["next_cursor"] is None
    assert set(everything["items"][0]) == {"id", "display_name", "contact_name", "email", "city",
                                           "created_at"}  # fmt: skip

    found = session.get(_url(business_id), params={"q": "HARB"}).json()
    assert [i["display_name"] for i in found["items"]] == [
        "harbour view (Demo)",
        "Harbour Line Logistics (Demo)",
    ]
    assert session.get(_url(business_id), params={"q": "bour"}).json()["items"] == []  # prefix only
    wildcard = session.get(_url(business_id), params={"q": "100%"}).json()["items"]
    assert [i["display_name"] for i in wildcard] == ["100% Cotton_Co (Demo)"]
    assert session.get(_url(business_id), params={"q": "_"}).json()["items"] == []  # literal _

    first = session.get(_url(business_id), params={"limit": 2}).json()
    assert len(first["items"]) == 2 and first["next_cursor"]
    second = session.get(
        _url(business_id), params={"limit": 2, "cursor": first["next_cursor"]}
    ).json()
    third = session.get(
        _url(business_id), params={"limit": 2, "cursor": second["next_cursor"]}
    ).json()
    pages = [i["display_name"] for page in (first, second, third) for i in page["items"]]
    assert pages == list(reversed(names))
    assert third["next_cursor"] is None


def test_it_cus_01_tampered_cursor_is_422(owner: tuple[ApiSession, str]) -> None:
    session, business_id = owner
    for index in range(3):
        create_customer(session, business_id, display_name=f"C{index} (Demo)")
    cursor = session.get(_url(business_id), params={"limit": 1}).json()["next_cursor"]
    tampered = cursor[:-2] + ("AA" if cursor[-2:] != "AA" else "BB")
    for bad in (tampered, "not-a-cursor", "eyJ0IjoiMjAyNi0xMS0yNVQwNTo0MjoxMFoiLCJpZCI6IjRlNmEifQ"):
        response = session.get(_url(business_id), params={"cursor": bad})
        assert response.status_code == 422, bad
        assert response.json()["errors"][0]["pointer"] == "/cursor"


@pytest.mark.parametrize(("params", "pointer"), [({"limit": 0}, "/limit"), ({"limit": 51}, "/limit"),
                                                 ({"q": "x" * 101}, "/q")])  # fmt: skip
def test_list_parameter_validation(
    owner: tuple[ApiSession, str], params: dict[str, object], pointer: str
) -> None:
    session, business_id = owner
    response = session.get(_url(business_id), params=params)
    assert response.status_code == 422
    assert response.json()["errors"][0]["pointer"] == pointer


def test_it_cus_02_patch_with_etag_and_null_clearing(
    owner: tuple[ApiSession, str], migrator_engine: Engine
) -> None:
    session, business_id = owner
    customer = create_customer(session, business_id, city="Pune", email="ap@riverstone.invalid")
    url = _url(business_id, customer["id"])
    assert session.get(url).headers["etag"] == '"1"'

    response = session.patch(
        url, json={"city": "Mumbai", "email": None}, headers={"If-Match": '"1"'}
    )
    assert response.status_code == 200
    assert response.headers["etag"] == '"2"'
    assert response.json()["city"] == "Mumbai"
    assert response.json()["email"] is None

    not_null = session.patch(url, json={"display_name": None}, headers={"If-Match": '"2"'})
    assert not_null.status_code == 422
    assert not_null.json()["code"] == "validation_failed"
    assert [(e["pointer"], e["code"]) for e in not_null.json()["errors"]] == [
        ("/display_name", "not_null")
    ]
    assert session.patch(url, json={"city": "Pune"}, headers={"If-Match": '"1"'}).status_code == 412
    assert session.patch(url, json={"city": "Pune"}).status_code == 428
    with migrator_engine.connect() as connection:
        details = connection.execute(
            text("SELECT details FROM audit_events WHERE event_type = 'customer.updated'")
        ).scalar_one()
    assert details == {"fields": ["city", "email"]}


def test_customer_of_another_business_path_is_404(owner: tuple[ApiSession, str]) -> None:
    session, business_id = owner
    customer = create_customer(session, business_id)
    other_business = "4e6a8c0d-2f3b-4c5e-9a7d-9f1b3d5f7a9c"
    assert session.get(_url(other_business, customer["id"])).status_code == 404
    assert session.get(_url(business_id, "not-a-uuid")).status_code == 404
