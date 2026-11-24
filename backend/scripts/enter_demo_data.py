"""Enter the demonstration data set (docs/11 §5) through the public API.

Optional helper for M8.2 on the presenter machine; the same data can be typed in the browser
instead. It signs in as the demonstration account and then uses exactly the endpoints, validation,
CSRF and Origin checks and server calculation that the browser uses:

- the business profile "Lotus Lane Design Studio (Demo)" (E-06), GSTIN empty;
- the customers "Riverstone Consulting (Demo)" and "Saffron Leaf Foods (Demo)" (E-10);
- one invoice for Riverstone with fixture lines F-01 and F-02 (total ₹2,700.00), finalised
  (E-15, E-19) and waited on until its PDF is ready;
- one draft invoice for Saffron Leaf (E-15).

"Harbour Line Logistics (Demo)" is not entered: the demonstration creates it live (11 §7).

It never creates accounts (use ``python -m app.cli create-demo-account``), never connects to the
database or the object store, and stops before writing anything if the organization already has
invoices. The password comes from DEMO_ACCOUNT_PASSWORD or a hidden prompt and is never printed.

Usage, with the server running and BASE_URL equal to APP_ORIGIN:

    uv run python scripts/enter_demo_data.py --base-url http://localhost:8000

``--email`` selects another account created with ``create-demo-account`` (default
owner@demo.invalid), for example a rehearsal account for the DC checks.

This is tooling, not product code: it is excluded from the image by .dockerignore.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_EMAIL = "owner@demo.invalid"
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
RIVERSTONE = {
    "display_name": "Riverstone Consulting (Demo)",
    "city": "Pune",
    "state_code": "27",
    "postal_code": "411001",
}
SAFFRON = {
    "display_name": "Saffron Leaf Foods (Demo)",
    "city": "Chennai",
    "state_code": "33",
    "postal_code": "600001",
}
# docs/09 §15 fixtures F-01 and F-02: ₹1,800.00 + ₹900.00 = ₹2,700.00.
F01 = {"description": "Brand identity consultation", "quantity": "2.5", "unit": "hrs",
       "unit_price": "800.00", "discount_type": "percent", "discount_value": "10"}  # fmt: skip
F02 = {"description": "Website support hours", "quantity": "3", "unit": "hrs",
       "unit_price": "333.33", "discount_type": "amount", "discount_value": "99.99"}  # fmt: skip
DRAFT_LINE = {"description": "Menu card design", "quantity": "1", "unit": "job",
              "unit_price": "4500.00", "discount_type": "none", "discount_value": None}  # fmt: skip


class ApiFailure(Exception):
    pass


class Api:
    def __init__(self, base_url: str) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise ApiFailure("--base-url must start with http:// or https://")
        self.base = base_url.rstrip("/")
        self.cookie = ""
        self.csrf = ""

    def call(
        self, method: str, path: str, body: Any = None, headers: dict[str, str] | None = None
    ) -> tuple[int, dict[str, str], Any]:
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base + path, data=data, method=method)  # noqa: S310
        request.add_header("Origin", self.base)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if self.cookie:
            request.add_header("Cookie", self.cookie)
        if self.csrf and method not in ("GET", "HEAD"):
            request.add_header("X-CSRF-Token", self.csrf)
        for name, value in (headers or {}).items():
            request.add_header(name, value)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 (scheme checked)
                raw = response.read()
                return response.status, dict(response.headers), json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            raw = error.read()
            problem = json.loads(raw) if raw else {}
            raise ApiFailure(
                f"{method} {path} -> {error.code} {problem.get('code', '')} "
                f"(request id {problem.get('request_id', 'n/a')})"
            ) from None
        except urllib.error.URLError as error:
            raise ApiFailure(f"cannot reach {self.base}: {error.reason}") from None

    def sign_in(self, email: str, password: str) -> None:
        body = {"email": email, "password": password}
        data = json.dumps(body).encode()
        request = urllib.request.Request(  # noqa: S310 (scheme checked)
            self.base + "/api/v1/auth/login", data=data, method="POST"
        )
        request.add_header("Origin", self.base)
        request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                session = json.loads(response.read())
                cookies = response.headers.get_all("Set-Cookie") or []
        except urllib.error.HTTPError as error:
            raw = error.read()
            code = json.loads(raw).get("code", "") if raw else ""
            raise ApiFailure(
                f"sign-in refused ({error.code} {code}). Each failure counts toward the "
                "15-minute throttle (5 failures): check the password before trying again."
            ) from None
        except urllib.error.URLError as error:
            raise ApiFailure(f"cannot reach {self.base}: {error.reason}") from None
        token = next((c.split(";", 1)[0] for c in cookies if c.startswith("ps5_session=")), "")
        if not token:
            raise ApiFailure("sign-in returned no session cookie")
        self.cookie = token
        self.csrf = session["csrf_token"]


def enter(api: Api) -> None:
    _, _, me = api.call("GET", "/api/v1/auth/me")
    business = me.get("business")
    if business is None:
        _, _, created = api.call("POST", "/api/v1/businesses", BUSINESS)
        business_id = created["id"]
        print("Business profile created: Lotus Lane Design Studio (Demo)")
    else:
        business_id = business["id"]
        print("Business profile already present: left unchanged")

    _, _, documents = api.call("GET", f"/api/v1/businesses/{business_id}/documents?limit=1")
    if documents["items"]:
        raise ApiFailure(
            "this organization already has invoices; nothing else was entered. "
            "The data set is meant for a fresh demonstration account."
        )

    _, _, listing = api.call("GET", f"/api/v1/businesses/{business_id}/customers?limit=50")
    existing = {c["display_name"]: c["id"] for c in listing["items"]}
    ids: dict[str, str] = {}
    for customer in (RIVERSTONE, SAFFRON):
        name = customer["display_name"]
        if name in existing:
            ids[name] = existing[name]
            print(f"Customer already present: {name}")
            continue
        _, _, created = api.call("POST", f"/api/v1/businesses/{business_id}/customers", customer)
        ids[name] = created["id"]
        print(f"Customer created: {name}")

    _, headers, draft = api.call(
        "POST",
        f"/api/v1/businesses/{business_id}/documents",
        {"customer_id": ids[RIVERSTONE["display_name"]], "lines": [F01, F02]},
    )
    total = draft["totals"]["grand_total"]
    if total != "2700.00":
        raise ApiFailure(f"unexpected total {total} (expected 2700.00); not finalised")
    etag = {k.lower(): v for k, v in headers.items()}["etag"]
    _, _, final = api.call(
        "POST",
        f"/api/v1/documents/{draft['id']}/finalize",
        headers={"If-Match": etag, "Idempotency-Key": secrets.token_urlsafe(16)},
    )
    print(f"Invoice finalised: {final['number']} for Riverstone, total ₹2,700.00")
    pdf = final.get("pdf") or {}
    deadline = time.monotonic() + 90
    while pdf.get("status") == "pending" and time.monotonic() < deadline:
        time.sleep(1)
        _, _, current = api.call("GET", f"/api/v1/documents/{draft['id']}")
        pdf = current["pdf"]
    if pdf.get("status") != "ready":
        raise ApiFailure(
            f"the PDF of {final['number']} is {pdf.get('status')} "
            f"({pdf.get('last_error_code')}); open the invoice in the browser and press Retry PDF"
        )
    print(f"PDF ready: SHA-256 {pdf['sha256']}")

    api.call(
        "POST",
        f"/api/v1/businesses/{business_id}/documents",
        {"customer_id": ids[SAFFRON["display_name"]], "lines": [DRAFT_LINE]},
    )
    print("Draft created for Saffron Leaf Foods (Demo)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="the server origin (= APP_ORIGIN)"
    )
    parser.add_argument(
        "--email",
        default=DEFAULT_EMAIL,
        help="the account to fill (an account created by create-demo-account)",
    )
    args = parser.parse_args()
    prompt = f"Password for {args.email}: "
    password = os.environ.get("DEMO_ACCOUNT_PASSWORD") or getpass.getpass(prompt)
    try:
        api = Api(args.base_url)
        api.sign_in(args.email, password)
        try:
            enter(api)
        finally:
            api.call("POST", "/api/v1/auth/logout")
    except ApiFailure as failure:
        print(f"enter_demo_data: {failure}", file=sys.stderr)
        return 1
    print("Demonstration data set entered.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
