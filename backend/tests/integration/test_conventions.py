"""IT-GEN-01 (partial, M0) and the security headers of docs/12 §4.3.

Covered now: problem+json shape, X-Request-ID echo, Cache-Control: no-store, body over
256 KiB → 413, security headers, unhandled errors → 500 without internals, docs UI only
in development. The unknown-field and non-JSON-body checks need body endpoints (M1).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import PROBLEM_TYPE_BASE
from app.core.middleware import MAX_BODY_BYTES, SECURITY_HEADERS
from tests.integration.conftest import make_client

GENERATED_ID = re.compile(r"^req_[A-Za-z0-9_-]{16}$")


def _assert_problem(response_json: dict[str, object], code: str, status: int, path: str) -> None:
    assert response_json == {
        "type": PROBLEM_TYPE_BASE + code,
        "title": response_json["title"],
        "status": status,
        "detail": response_json["detail"],
        "instance": path,
        "code": code,
        "request_id": response_json["request_id"],
    }


def test_unknown_api_path_is_a_problem_json_404(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    _assert_problem(body, "not_found", 404, "/api/v1/does-not-exist")
    assert body["request_id"] == response.headers["x-request-id"]


def test_method_not_allowed_is_answered_as_not_found(client: TestClient) -> None:
    # The documents define no 405 code; see PROGRESS.md decisions.
    response = client.post("/healthz")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


@pytest.mark.parametrize("request_id", ["abcDEF_123-xyz", "a" * 64, "12345678"])
def test_valid_request_id_is_echoed(client: TestClient, request_id: str) -> None:
    response = client.get("/healthz", headers={"X-Request-ID": request_id})
    assert response.headers["x-request-id"] == request_id


@pytest.mark.parametrize(
    "request_id", [b"short", b"has space!", b"a" * 65, "näme12345".encode("latin-1")]
)
def test_invalid_request_id_is_replaced(client: TestClient, request_id: bytes) -> None:
    response = client.get("/healthz", headers={"X-Request-ID": request_id})
    assert response.headers["x-request-id"].encode("latin-1") != request_id
    assert GENERATED_ID.match(response.headers["x-request-id"])


def test_request_id_is_generated_when_absent(client: TestClient) -> None:
    first = client.get("/healthz").headers["x-request-id"]
    second = client.get("/healthz").headers["x-request-id"]
    assert GENERATED_ID.match(first)
    assert first != second


@pytest.mark.parametrize("path", ["/healthz", "/readyz", "/api/v1/does-not-exist"])
def test_responses_are_not_cached(client: TestClient, path: str) -> None:
    assert client.get(path).headers["cache-control"] == "no-store"


@pytest.mark.parametrize("path", ["/healthz", "/api/v1/does-not-exist"])
def test_security_headers_on_every_response(client: TestClient, path: str) -> None:
    response = client.get(path)
    for name, value in SECURITY_HEADERS:
        assert response.headers[name] == value
    assert "strict-transport-security" not in response.headers  # http origin: never HSTS


def test_hsts_only_for_https_origin(settings: Settings, no_spa: Path) -> None:
    https = settings.model_copy(update={"app_origin": "https://hive-docs.example.invalid"})
    for client in make_client(https, no_spa):
        assert client.get("/healthz").headers["strict-transport-security"] == "max-age=31536000"


def test_body_over_256_kib_is_rejected_before_routing(client: TestClient) -> None:
    response = client.post("/api/v1/anything", content=b"x" * (MAX_BODY_BYTES + 1))
    assert response.status_code == 413
    assert response.headers["content-type"] == "application/problem+json"
    _assert_problem(response.json(), "payload_too_large", 413, "/api/v1/anything")


def test_unhandled_error_is_a_generic_500_with_headers(
    settings: Settings, no_spa: Path, caplog: pytest.LogCaptureFixture
) -> None:
    for client in make_client(settings, no_spa):

        def explode() -> None:
            raise RuntimeError("secret internal detail")

        client.app.add_api_route("/api/v1/test-explode", explode)  # type: ignore[attr-defined]
        with caplog.at_level(logging.ERROR, logger="app.errors"):
            response = client.get("/api/v1/test-explode")
        assert response.status_code == 500
        assert response.headers["content-type"] == "application/problem+json"
        _assert_problem(response.json(), "internal_error", 500, "/api/v1/test-explode")
        assert "secret internal detail" not in response.text
        assert "Traceback" not in response.text
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["cache-control"] == "no-store"
        logged = [r for r in caplog.records if r.name == "app.errors"]
        assert logged and logged[0].exc_info is not None  # the traceback stays server-side


def test_access_log_uses_route_template_not_raw_path(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="app.access"):
        client.get("/healthz?q=private-search-term")
        client.get("/api/v1/unknown?email=someone@example.invalid")
    lines = [r for r in caplog.records if r.name == "app.access"]
    assert [getattr(r, "route", None) for r in lines] == ["/healthz", "unmatched"]
    assert [getattr(r, "status", None) for r in lines] == [200, 404]
    text = " ".join(str(r.__dict__) for r in lines)
    assert "private-search-term" not in text
    assert "someone@example.invalid" not in text


def test_docs_ui_available_in_development(client: TestClient) -> None:
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


@pytest.mark.parametrize("app_env", ["demo", "production"])
def test_docs_ui_absent_outside_development(settings: Settings, no_spa: Path, app_env: str) -> None:
    for client in make_client(settings.model_copy(update={"app_env": app_env}), no_spa):
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
