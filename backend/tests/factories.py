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
