"""IT-DOC-05 (docs/11 §2.2): E-16 history list."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.clock import FrozenClock
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
def setup(client: TestClient, clock: FrozenClock) -> tuple[ApiSession, str, dict[str, str]]:
    session = trusted(client)
    business = create_business(session)["id"]
    river = create_customer(session, business, display_name="Riverstone Consulting (Demo)")["id"]
    harbour = create_customer(session, business, display_name="Harbour Line Logistics (Demo)")["id"]
    ids: dict[str, str] = {}
    issued = create_draft(session, business, river, lines=[F01, F02])
    assert finalize(session, issued).status_code == 200
    ids["issued"] = issued["id"]
    clock.advance(timedelta(seconds=1))
    ids["draft_harbour"] = create_draft(session, business, harbour, lines=[F01])["id"]
    clock.advance(timedelta(seconds=1))
    ids["draft_river"] = create_draft(session, business, river)["id"]
    # Rename the customer after issue: the finalised row keeps the issued name.
    session.patch(f"/api/v1/businesses/{business}/customers/{river}", json={"display_name": "Saffron Leaf Foods (Demo)"},
                  headers={"If-Match": '"1"'})  # fmt: skip
    return session, business, ids


def _list(session: ApiSession, business: str, **params: object) -> dict[str, object]:
    response = session.get(f"/api/v1/businesses/{business}/documents", params=params)
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


def test_it_doc_05_items_and_order(setup: tuple[ApiSession, str, dict[str, str]]) -> None:
    session, business, ids = setup
    items = _list(session, business)["items"]
    assert [item["id"] for item in items] == [
        ids["draft_river"],
        ids["draft_harbour"],
        ids["issued"],
    ]  # type: ignore[index]
    issued = items[2]  # type: ignore[index]
    assert issued == {
        "id": ids["issued"], "status": "finalized", "number": "INV/26-27/00001",
        "customer_name": "Riverstone Consulting (Demo)", "issue_date": "2026-11-25", "grand_total": "2700.00",
        "pdf_status": "ready", "created_at": issued["created_at"], "updated_at": issued["updated_at"],
    }  # fmt: skip
    draft = items[0]  # type: ignore[index]
    assert draft["status"] == "draft"
    assert draft["number"] is None and draft["issue_date"] is None
    assert draft["grand_total"] is None and draft["pdf_status"] is None
    assert draft["customer_name"] == "Saffron Leaf Foods (Demo)"  # current name for drafts


def test_it_doc_05_status_filter(setup: tuple[ApiSession, str, dict[str, str]]) -> None:
    session, business, ids = setup
    assert [i["id"] for i in _list(session, business, status="finalized")["items"]] == [
        ids["issued"]
    ]  # type: ignore[index]
    assert len(_list(session, business, status="draft")["items"]) == 2  # type: ignore[arg-type]
    wrong = session.get(f"/api/v1/businesses/{business}/documents", params={"status": "cancelled"})
    assert wrong.status_code == 422 and wrong.json()["errors"][0]["pointer"] == "/status"


@pytest.mark.parametrize(
    ("q", "expected"),
    [("INV/26", ["issued"]), ("inv/26-27/0000", ["issued"]), ("river", ["issued"]), ("harb", ["draft_harbour"]),
     ("saffron", ["draft_river"]), ("Consulting", []), ("%", [])],
)  # fmt: skip
def test_it_doc_05_prefix_search(
    setup: tuple[ApiSession, str, dict[str, str]], q: str, expected: list[str]
) -> None:
    session, business, ids = setup
    found = [i["id"] for i in _list(session, business, q=q)["items"]]  # type: ignore[index]
    assert sorted(found) == sorted(ids[name] for name in expected)


def test_it_doc_05_pagination_and_limits(setup: tuple[ApiSession, str, dict[str, str]]) -> None:
    session, business, ids = setup
    first = _list(session, business, limit=2)
    assert len(first["items"]) == 2 and first["next_cursor"]  # type: ignore[arg-type]
    second = _list(session, business, limit=2, cursor=first["next_cursor"])
    assert [i["id"] for i in second["items"]] == [ids["issued"]] and second["next_cursor"] is None  # type: ignore[index]
    for params, pointer in (
        ({"limit": 0}, "/limit"),
        ({"q": "x" * 51}, "/q"),
        ({"cursor": "bad"}, "/cursor"),
    ):
        response = session.get(f"/api/v1/businesses/{business}/documents", params=params)
        assert response.status_code == 422 and response.json()["errors"][0]["pointer"] == pointer
    # A customers cursor is foreign to the documents list.
    customers = session.get(f"/api/v1/businesses/{business}/customers", params={"limit": 1}).json()
    foreign = session.get(
        f"/api/v1/businesses/{business}/documents", params={"cursor": customers["next_cursor"]}
    )
    assert foreign.status_code == 422
