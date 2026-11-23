"""Test data factories and a signed-in API session helper (docs/11 §1, §5).

Passwords are random for every test run; no credential is fixed anywhere (docs/12 §3).
Accounts are created through the same service function as the ``create-demo-account`` CLI.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from app.modules.auth.service import create_account
from tests.services import CLIENT_ADDRESS

UNSAFE = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class Account:
    email: str
    password: str
    org_id: uuid.UUID
    user_id: uuid.UUID
    org_name: str
    display_name: str


def new_password() -> str:
    return secrets.token_urlsafe(18)


def create_test_account(
    app: FastAPI,
    *,
    email: str | None = None,
    display_name: str = "Test Owner",
    org_name: str = "Test Studio (Demo)",
) -> Account:
    password = new_password()
    email = email or f"owner-{secrets.token_hex(4)}@test.invalid"
    with app.state.db_sessions() as db:
        org_id, user_id = create_account(
            db,
            now=app.state.clock.now(),
            email=email,
            display_name=display_name,
            org_name=org_name,
            password=password,
        )
    return Account(email.lower(), password, org_id, user_id, org_name, display_name)


def origin_headers(app: FastAPI) -> dict[str, str]:
    return {"Origin": app.state.settings.app_origin}


def login(client: TestClient, account: Account) -> Response:
    return client.post(
        "/api/v1/auth/login",
        json={"email": account.email, "password": account.password},
        headers=origin_headers(client.app),  # type: ignore[arg-type]
    )


class ApiSession:
    """A signed-in TestClient that adds Origin and X-CSRF-Token to unsafe requests."""

    def __init__(self, client: TestClient, account: Account, body: dict[str, Any]) -> None:
        self.client = client
        self.account = account
        self.body = body
        self.csrf: str = body["csrf_token"]

    def request(self, method: str, url: str, **kwargs: Any) -> Response:
        headers = dict(kwargs.pop("headers", None) or {})
        if method.upper() in UNSAFE:
            headers.setdefault("Origin", self.client.app.state.settings.app_origin)  # type: ignore[attr-defined]
            headers.setdefault("X-CSRF-Token", self.csrf)
        return self.client.request(method, url, headers=headers, **kwargs)

    def get(self, url: str, **kwargs: Any) -> Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Response:
        return self.request("POST", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> Response:
        return self.request("DELETE", url, **kwargs)


def new_client(app: FastAPI) -> TestClient:
    """Another browser (its own cookie jar) against the same application."""
    return TestClient(app, base_url="https://testserver", client=CLIENT_ADDRESS)


def sign_in(client: TestClient, account: Account) -> ApiSession:
    response = login(client, account)
    assert response.status_code == 200, response.text
    return ApiSession(client, account, response.json())


def signed_in(app: FastAPI, **account_fields: Any) -> ApiSession:
    """A new account signed in from its own client."""
    account = create_test_account(app, **account_fields)
    return sign_in(new_client(app), account)


def trusted(client: TestClient) -> ApiSession:
    """Sign a new account in on ``client`` itself, so unsafe requests pass the CSRF check.

    Used where a test is about routing (405, 404) rather than CSRF: the Origin and CSRF
    check runs before routing (docs/07 §1.13), so those requests need a valid session.
    """
    return sign_in(client, create_test_account(client.app))  # type: ignore[arg-type]


BUSINESS = {
    "legal_name": "Lotus Lane Design Studio (Demo)",
    "address_line1": "12 Example Road",
    "address_line2": "Indiranagar",
    "city": "Bengaluru",
    "state_code": "29",
    "postal_code": "560038",
    "phone": "+91 80 0000 0000",
    "email": "accounts@demo.invalid",
}


def create_business(session: ApiSession, **overrides: Any) -> dict[str, Any]:
    response = session.post("/api/v1/businesses", json={**BUSINESS, **overrides})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def create_customer(session: ApiSession, business_id: str, **fields: Any) -> dict[str, Any]:
    payload = {"display_name": "Riverstone Consulting (Demo)", **fields}
    response = session.post(f"/api/v1/businesses/{business_id}/customers", json=payload)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


F01 = {
    "description": "Brand identity consultation",
    "quantity": "2.5",
    "unit": "hrs",
    "unit_price": "800.00",
    "discount_type": "percent",
    "discount_value": "10",
}
F02 = {"description": "Website support hours", "quantity": "3", "unit": "hrs",
       "unit_price": "333.33", "discount_type": "amount", "discount_value": "99.99"}  # fmt: skip


def create_draft(
    session: ApiSession, business_id: str, customer_id: str, **fields: Any
) -> dict[str, Any]:
    payload = {"customer_id": customer_id, **fields}
    response = session.post(f"/api/v1/businesses/{business_id}/documents", json=payload)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def mark_finalized_in_database(
    engine: Any, document_id: str, number: str = "INV/26-27/00099"
) -> None:
    """Test helper (migrator role): put a draft into the finalised state directly in SQL,
    to exercise guards before the finalisation service exists. Never used by the app."""
    from sqlalchemy import text

    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT org_id, business_id, created_by FROM documents WHERE id = :id"),
            {"id": document_id},
        ).one()
        series = connection.execute(
            text(
                "INSERT INTO number_series (org_id, business_id, financial_year) "
                "VALUES (:o, :b, '26-27') ON CONFLICT (business_id, doc_type, financial_year) "
                "DO UPDATE SET updated_at = now() RETURNING id"
            ),
            {"o": row.org_id, "b": row.business_id},
        ).scalar_one()
        connection.execute(
            text(
                "UPDATE documents SET status = 'finalized', number_series_id = :s, "
                "sequence_no = :n, document_number = :num, issue_date = DATE '2026-11-25', "
                "finalized_at = now(), finalized_by = :u, version = version + 1 WHERE id = :id"
            ),
            {
                "s": series,
                "n": int(number.rsplit("/", 1)[1]),
                "num": number,
                "u": row.created_by,
                "id": document_id,
            },
        )


def finalize(session: ApiSession, document: dict[str, Any], key: str | None = None) -> Response:
    headers = {
        "If-Match": f'"{document["version"]}"',
        "Idempotency-Key": key or secrets.token_urlsafe(12),
    }
    return session.post(f"/api/v1/documents/{document['id']}/finalize", headers=headers)
