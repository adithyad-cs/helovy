"""IT-AUTH-01 to IT-AUTH-06 (docs/11 §2.6), E-03 to E-05 (docs/07 §4) and the CLI account.

The frozen clock (tests/services.py) drives expiry and throttling windows.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from http.cookies import SimpleCookie

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.cli import main as cli_main
from app.core.clock import FrozenClock
from app.modules.auth.security import csrf_token, hash_session_token, login_subject_hash
from tests.factories import (
    ApiSession,
    create_test_account,
    login,
    new_client,
    new_password,
    origin_headers,
    sign_in,
)

LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"


def _events(engine: Engine, event_type: str) -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT org_id, actor_user_id, subject_type, subject_id, subject_hash, "
                "host(ip) AS ip, request_id, details FROM audit_events "
                "WHERE event_type = :t ORDER BY id"
            ),
            {"t": event_type},
        ).mappings()
        return [dict(row) for row in rows]


def _cookie_attributes(response_header: str) -> dict[str, str]:
    cookie: SimpleCookie = SimpleCookie()
    cookie.load(response_header)
    morsel = cookie["ps5_session"]
    return {key: str(value) for key, value in morsel.items() if value}


def _comparable(body: dict[str, object]) -> dict[str, object]:
    return {k: v for k, v in body.items() if k not in ("instance", "request_id")}


# --- IT-AUTH-01 ------------------------------------------------------------------------


def test_it_auth_01_successful_sign_in(client: TestClient, migrator_engine: Engine) -> None:
    account = create_test_account(client.app, org_name="Demo Studio", display_name="Demo Owner")  # type: ignore[arg-type]
    response = login(client, account)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"

    set_cookie = response.headers["set-cookie"]
    attributes = _cookie_attributes(set_cookie)
    assert attributes["httponly"] == "True"
    assert attributes["secure"] == "True"
    assert attributes["samesite"].lower() == "lax"
    assert attributes["path"] == "/"
    assert attributes["max-age"] == "604800"
    assert "domain" not in attributes  # host-only
    assert "expires" not in set_cookie.lower()

    body = response.json()
    assert body["user"] == {
        "id": str(account.user_id),
        "email": account.email,
        "display_name": "Demo Owner",
    }
    assert body["organization"] == {"id": str(account.org_id), "name": "Demo Studio"}
    assert body["role"] == "owner"
    assert body["business"] is None
    assert body["session_expires_at"] == "2026-12-02T05:42:10Z"  # frozen clock + 7 days
    assert isinstance(body["csrf_token"], str) and len(body["csrf_token"]) == 43

    token = SimpleCookie(set_cookie)["ps5_session"].value
    with migrator_engine.connect() as connection:
        stored = connection.execute(
            text("SELECT id, token_hash, org_id, user_id, host(ip) FROM sessions")
        ).one()
    assert bytes(stored.token_hash) == hash_session_token(token)  # only the hash is stored
    assert token.encode() not in bytes(stored.token_hash)
    settings = client.app.state.settings  # type: ignore[attr-defined]
    assert body["csrf_token"] == csrf_token(settings.csrf_key, stored.id)

    events = _events(migrator_engine, "auth.login_succeeded")
    assert len(events) == 1
    assert events[0]["org_id"] == account.org_id
    assert events[0]["actor_user_id"] == account.user_id
    assert events[0]["ip"] == "203.0.113.10"
    assert events[0]["request_id"] == response.headers["x-request-id"]
    assert events[0]["details"] == {}


def test_it_auth_01_sign_in_revokes_the_presented_session(
    client: TestClient, migrator_engine: Engine
) -> None:
    account = create_test_account(client.app)  # type: ignore[arg-type]
    first = sign_in(client, account)
    old_cookie = client.cookies.get("ps5_session")
    second = login(client, account)  # the old cookie is presented with this request
    assert second.status_code == 200
    assert client.cookies.get("ps5_session") != old_cookie
    with migrator_engine.connect() as connection:
        revoked = connection.execute(
            text("SELECT revoked_at IS NOT NULL FROM sessions WHERE token_hash = :h"),
            {"h": hash_session_token(str(old_cookie))},
        ).scalar_one()
    assert revoked
    stale = new_client(client.app)  # type: ignore[arg-type]
    stale.cookies.set("ps5_session", str(old_cookie), domain="testserver.local")
    assert stale.get(ME).status_code == 401
    assert first.csrf != second.json()["csrf_token"]


def test_me_returns_the_session_context_without_setting_a_cookie(client: TestClient) -> None:
    account = create_test_account(client.app)  # type: ignore[arg-type]
    session = sign_in(client, account)
    response = client.get(ME)
    assert response.status_code == 200
    assert "set-cookie" not in response.headers
    assert response.json() == session.body
    head = client.head(ME)
    assert head.status_code == 200
    assert head.content == b""


def test_me_without_a_session_is_401(client: TestClient) -> None:
    response = client.get(ME)
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"
    client.cookies.set("ps5_session", "not-a-real-token", domain="testserver.local")
    assert client.get(ME).json()["code"] == "unauthenticated"


def test_last_seen_is_refreshed_at_most_once_a_minute(
    client: TestClient, clock: FrozenClock, migrator_engine: Engine
) -> None:
    sign_in(client, create_test_account(client.app))  # type: ignore[arg-type]

    def last_seen() -> object:
        with migrator_engine.connect() as connection:
            return connection.execute(text("SELECT last_seen_at FROM sessions")).scalar_one()

    start = last_seen()
    clock.advance(timedelta(seconds=30))
    client.get(ME)
    assert last_seen() == start
    clock.advance(timedelta(seconds=31))
    client.get(ME)
    assert last_seen() == clock.now()


# --- IT-AUTH-02 ------------------------------------------------------------------------


def test_it_auth_02_failures_are_identical_and_audited(
    client: TestClient, migrator_engine: Engine
) -> None:
    app = client.app
    account = create_test_account(app)  # type: ignore[arg-type]
    inactive = create_test_account(app)  # type: ignore[arg-type]
    with migrator_engine.begin() as connection:
        connection.execute(
            text("UPDATE users SET is_active = false WHERE id = :id"), {"id": inactive.user_id}
        )
    headers = origin_headers(app)  # type: ignore[arg-type]
    wrong_password = client.post(
        LOGIN, json={"email": account.email, "password": new_password()}, headers=headers
    )
    unknown_email = client.post(
        LOGIN, json={"email": "nobody@test.invalid", "password": new_password()}, headers=headers
    )
    inactive_user = login(client, inactive)  # correct password, inactive account

    for response in (wrong_password, unknown_email, inactive_user):
        assert response.status_code == 401
        assert "set-cookie" not in response.headers
    bodies = [_comparable(r.json()) for r in (wrong_password, unknown_email, inactive_user)]
    assert bodies[0] == bodies[1] == bodies[2]
    assert bodies[0]["code"] == "invalid_credentials"
    assert bodies[0]["detail"] == "Email or password is incorrect."

    events = _events(migrator_engine, "auth.login_failed")
    assert [event["details"] for event in events] == [
        {"reason": "invalid_credentials"},
        {"reason": "invalid_credentials"},
        {"reason": "inactive"},
    ]
    key = app.state.settings.csrf_key  # type: ignore[attr-defined]
    assert events[0]["subject_hash"] == login_subject_hash(key, account.email)
    assert events[1]["subject_hash"] == login_subject_hash(key, "nobody@test.invalid")
    for event in events:
        assert event["org_id"] is None
        assert event["actor_user_id"] is None
        assert event["ip"] == "203.0.113.10"
    with migrator_engine.connect() as connection:
        details = connection.execute(text("SELECT details::text FROM audit_events")).scalars()
        assert all(account.email not in value for value in details)  # never the email itself


# --- IT-AUTH-03 ------------------------------------------------------------------------


def _fail(client: TestClient, email: str) -> int:
    response = client.post(
        LOGIN,
        json={"email": email, "password": new_password()},
        headers=origin_headers(client.app),  # type: ignore[arg-type]
    )
    return response.status_code


def test_it_auth_03_sixth_attempt_for_one_email_is_throttled(
    client: TestClient, clock: FrozenClock, migrator_engine: Engine
) -> None:
    account = create_test_account(client.app)  # type: ignore[arg-type]
    for _ in range(5):
        assert _fail(client, account.email) == 401
        clock.advance(timedelta(seconds=10))
    throttled = login(client, account)  # even the correct password is refused now
    assert throttled.status_code == 429
    assert throttled.json()["code"] == "rate_limited"
    # The first failure (50 s ago) leaves the 15-minute window in 850 s.
    assert throttled.headers["retry-after"] == "850"
    reasons = [e["details"] for e in _events(migrator_engine, "auth.login_failed")]
    assert reasons[-1] == {"reason": "throttled"}

    # Refused attempts are recorded but do not extend the lock-out.
    clock.advance(timedelta(seconds=849))
    assert login(client, account).status_code == 429
    clock.advance(timedelta(seconds=1))
    assert login(client, account).status_code == 200


def test_it_auth_03_one_ip_is_throttled_across_different_emails(client: TestClient) -> None:
    for index in range(5):
        assert _fail(client, f"guess-{index}@test.invalid") == 401
    assert _fail(client, "another@test.invalid") == 429
    # A different client IP is not affected by this IP's failures.
    other = TestClient(client.app, base_url="https://testserver", client=("198.51.100.7", 1))
    assert _fail(other, "another@test.invalid") == 401


def test_it_auth_03_failures_older_than_15_minutes_stop_counting(
    client: TestClient, clock: FrozenClock
) -> None:
    account = create_test_account(client.app)  # type: ignore[arg-type]
    for _ in range(5):
        assert _fail(client, account.email) == 401
    clock.advance(timedelta(minutes=15))
    assert login(client, account).status_code == 200


# --- IT-AUTH-04 ------------------------------------------------------------------------


def test_it_auth_04_sign_out_then_reuse_is_401(client: TestClient, migrator_engine: Engine) -> None:
    account = create_test_account(client.app)  # type: ignore[arg-type]
    session = sign_in(client, account)
    cookie = client.cookies.get("ps5_session")
    response = session.post(LOGOUT)
    assert response.status_code == 204
    assert response.content == b""
    attributes = _cookie_attributes(response.headers["set-cookie"])
    assert attributes["max-age"] == "0"
    assert _events(migrator_engine, "auth.logout")[0]["actor_user_id"] == account.user_id
    with migrator_engine.connect() as connection:
        assert connection.execute(text("SELECT revoked_at IS NOT NULL FROM sessions")).scalar_one()

    reuse = new_client(client.app)  # type: ignore[arg-type]
    reuse.cookies.set("ps5_session", str(cookie), domain="testserver.local")
    assert reuse.get(ME).status_code == 401
    again = ApiSession(reuse, account, session.body).post(LOGOUT)
    assert again.status_code == 401  # the same, now revoked, cookie (docs/07 E-04)
    assert again.json()["code"] == "unauthenticated"


# --- IT-AUTH-05 ------------------------------------------------------------------------


def test_it_auth_05_idle_for_more_than_24_hours_is_401(
    client: TestClient, clock: FrozenClock
) -> None:
    sign_in(client, create_test_account(client.app))  # type: ignore[arg-type]
    clock.advance(timedelta(hours=23, minutes=59, seconds=59))
    assert client.get(ME).status_code == 200  # activity refreshes last_seen_at
    clock.advance(timedelta(hours=24))
    assert client.get(ME).status_code == 401


def test_it_auth_05_older_than_7_days_is_401_even_if_active(
    client: TestClient, clock: FrozenClock
) -> None:
    sign_in(client, create_test_account(client.app))  # type: ignore[arg-type]
    for _ in range(7):
        clock.advance(timedelta(hours=23))
        assert client.get(ME).status_code == 200  # 7 x 23 h = 161 h, still active
    clock.advance(timedelta(hours=7))  # 168 h: the absolute expiry
    assert client.get(ME).status_code == 401


def test_inactive_user_session_is_rejected(client: TestClient, migrator_engine: Engine) -> None:
    account = create_test_account(client.app)  # type: ignore[arg-type]
    sign_in(client, account)
    with migrator_engine.begin() as connection:
        connection.execute(
            text("UPDATE users SET is_active = false WHERE id = :id"), {"id": account.user_id}
        )
    assert client.get(ME).status_code == 401


# --- IT-AUTH-06 ------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
@pytest.mark.parametrize(
    "case", ["no_token", "wrong_token", "other_session_token", "wrong_origin", "no_origin"]
)
def test_it_auth_06_unsafe_requests_need_token_and_origin(
    client: TestClient, method: str, case: str
) -> None:
    app = client.app
    session = sign_in(client, create_test_account(app))  # type: ignore[arg-type]
    other = sign_in(new_client(app), create_test_account(app))  # type: ignore[arg-type]
    origin = app.state.settings.app_origin  # type: ignore[attr-defined]
    headers = {
        "no_token": {"Origin": origin},
        "wrong_token": {"Origin": origin, "X-CSRF-Token": "A" * 43},
        "other_session_token": {"Origin": origin, "X-CSRF-Token": other.csrf},
        "wrong_origin": {"Origin": "https://evil.example.invalid", "X-CSRF-Token": session.csrf},
        "no_origin": {"X-CSRF-Token": session.csrf},
    }[case]
    # Checked before routing: logout (POST), and PATCH/DELETE on /me (which would be 405).
    path = LOGOUT if method == "POST" else ME
    response = client.request(method, path, headers=headers)
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"
    assert client.get(ME).status_code == 200  # nothing happened: still signed in


def test_it_auth_06_unsafe_request_without_a_session_is_403(client: TestClient) -> None:
    origin = origin_headers(client.app)  # type: ignore[arg-type]
    response = client.post(LOGOUT, headers={**origin, "X-CSRF-Token": "A" * 43})
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"


@pytest.mark.parametrize("origin", [None, "https://evil.example.invalid", "http://localhost:8001"])
def test_it_auth_06_sign_in_checks_origin_only(client: TestClient, origin: str | None) -> None:
    account = create_test_account(client.app)  # type: ignore[arg-type]
    headers = {"Origin": origin} if origin else {}
    response = client.post(
        LOGIN, json={"email": account.email, "password": account.password}, headers=headers
    )
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"
    assert "set-cookie" not in response.headers
    assert login(client, account).status_code == 200  # no token needed, only the Origin


def test_safe_methods_need_no_csrf_token(client: TestClient) -> None:
    sign_in(client, create_test_account(client.app))  # type: ignore[arg-type]
    assert client.get(ME, headers={"Origin": "https://evil.example.invalid"}).status_code == 200
    assert client.head(ME).status_code == 200


# --- E-03 validation and IT-GEN-01 conventions on a body endpoint ------------------------


def test_sign_in_rejects_unknown_fields(client: TestClient) -> None:
    response = client.post(
        LOGIN,
        json={"email": "a@b.invalid", "password": "x", "org_id": str(uuid.uuid4())},
        headers=origin_headers(client.app),  # type: ignore[arg-type]
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_failed"
    assert body["errors"] == [
        {"pointer": "/org_id", "code": "unknown_field", "message": "Extra inputs are not permitted"}
    ]


@pytest.mark.parametrize(
    ("payload", "pointer", "code"),
    [
        ({"email": "ab", "password": "x"}, "/email", "too_short"),
        ({"email": "a" * 250 + "@b.in", "password": "x"}, "/email", "too_long"),
        ({"email": "   ", "password": "x"}, "/email", "required"),
        ({"email": "a@b.invalid", "password": ""}, "/password", "required"),
        ({"email": "a@b.invalid", "password": "x" * 1025}, "/password", "too_long"),
        ({"email": 12345, "password": "x"}, "/email", "must_be_string"),
        ({"password": "x"}, "/email", "required"),
    ],
)
def test_sign_in_validation(
    client: TestClient, payload: dict[str, object], pointer: str, code: str
) -> None:
    response = client.post(LOGIN, json=payload, headers=origin_headers(client.app))  # type: ignore[arg-type]
    assert response.status_code == 422
    errors = response.json()["errors"]
    assert {"pointer": pointer, "code": code} == {k: errors[0][k] for k in ("pointer", "code")}


@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        (b"email=a&password=b", "application/x-www-form-urlencoded"),
        (b'{"email": "a@b.invalid", "password": "x"}', "text/plain"),
        (b'{"email": "a@b.invalid", "password": "x"}', None),
        (b'{"email": ', "application/json"),
    ],
)
def test_non_json_body_is_400_malformed_request(
    client: TestClient, content: bytes, content_type: str | None
) -> None:
    headers = origin_headers(client.app)  # type: ignore[arg-type]
    if content_type:
        headers["Content-Type"] = content_type
    response = client.post(LOGIN, content=content, headers=headers)
    assert response.status_code == 400
    assert response.json()["code"] == "malformed_request"


def test_email_is_trimmed_and_lower_cased(client: TestClient) -> None:
    account = create_test_account(client.app, email="Owner.Case@Test.Invalid")  # type: ignore[arg-type]
    response = client.post(
        LOGIN,
        json={"email": "  OWNER.case@test.INVALID ", "password": account.password},
        headers=origin_headers(client.app),  # type: ignore[arg-type]
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "owner.case@test.invalid"


# --- CLI create-demo-account (docs/05 §8) ----------------------------------------------


def test_cli_creates_one_account_and_refuses_duplicates(
    migrator_engine: Engine, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    password = new_password()
    monkeypatch.setenv("DEMO_ACCOUNT_PASSWORD", password)
    args = ["create-demo-account", "--email", "Owner@Demo.Invalid", "--name", "Demo Owner"]
    assert cli_main([*args, "--org", "Demo Studio"]) == 0
    output = capsys.readouterr()
    assert password not in output.out + output.err
    with migrator_engine.connect() as connection:
        user = connection.execute(text("SELECT email, password_hash FROM users")).one()
        assert user.email == "owner@demo.invalid"
        assert user.password_hash.startswith("$argon2id$")
        assert connection.execute(text("SELECT role FROM memberships")).scalar_one() == "owner"
        assert connection.execute(text("SELECT name FROM organizations")).scalar_one() == (
            "Demo Studio"
        )
    created = _events(migrator_engine, "account.created")
    assert len(created) == 1 and created[0]["details"] == {"via": "cli"}

    assert cli_main([*args, "--org", "Second Org"]) == 2  # existing email
    assert "already exists" in capsys.readouterr().err
    with migrator_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM organizations")).scalar_one() == 1


@pytest.mark.parametrize("password", ["short", "x" * 11, "x" * 1025])
def test_cli_refuses_weak_or_overlong_passwords(
    migrator_engine: Engine, monkeypatch: pytest.MonkeyPatch, password: str
) -> None:
    monkeypatch.setenv("DEMO_ACCOUNT_PASSWORD", password)
    code = cli_main(
        ["create-demo-account", "--email", "a@demo.invalid", "--name", "A", "--org", "O"]
    )
    assert code == 2
    with migrator_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM users")).scalar_one() == 0


def test_cli_account_can_sign_in(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    password = new_password()
    monkeypatch.setenv("DEMO_ACCOUNT_PASSWORD", password)
    assert (
        cli_main(
            ["create-demo-account", "--email", "owner@demo.invalid", "--name", "Demo Owner",
             "--org", "Demo Studio"]
        )
        == 0
    )  # fmt: skip
    response = client.post(
        LOGIN,
        json={"email": "owner@demo.invalid", "password": password},
        headers=origin_headers(client.app),  # type: ignore[arg-type]
    )
    assert response.status_code == 200
    assert response.json()["organization"]["name"] == "Demo Studio"
