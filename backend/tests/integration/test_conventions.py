"""IT-GEN-01 (partial, M0) and the security headers of docs/12 §4.3.

Covered now: problem+json shape, X-Request-ID echo, Cache-Control: no-store, body over
256 KiB → 413, unsupported method → 405 with Allow (docs/07 §1.13), security headers,
unhandled errors → 500 without internals, docs UI only in development. The unknown-field
and non-JSON-body checks need body endpoints (M1).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import PROBLEM_TYPE_BASE, AppError
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


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@pytest.mark.parametrize("path", ["/healthz", "/readyz"])
def test_unsupported_method_on_existing_route_is_405_with_allow(
    client: TestClient, method: str, path: str
) -> None:
    # docs/07 §1.13; RFC 9110 §15.5.6. Never answered as 404. GET resources also list
    # HEAD (docs/07 §1.14).
    response = client.request(method, path)
    assert response.status_code == 405
    assert response.headers["allow"] == "GET, HEAD"
    assert response.headers["content-type"] == "application/problem+json"
    _assert_problem(response.json(), "method_not_allowed", 405, path)
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert response.headers["cache-control"] == "no-store"
    for name, value in SECURITY_HEADERS:
        assert response.headers[name] == value


def test_allow_lists_every_method_of_a_path_served_by_several_routes(
    settings: Settings, no_spa: Path
) -> None:
    # Like E-07 (GET) and E-08 (PATCH) from M2: one path, two routes. Starlette alone would
    # report only the first route's methods.
    def read_item(item_id: str) -> dict[str, str]:
        return {"id": item_id}

    def update_item(item_id: str) -> dict[str, str]:
        return {"id": item_id}

    for client in make_client(settings, no_spa):
        app = client.app
        app.add_api_route("/api/v1/test-multi/{item_id}", read_item, methods=["GET"])  # type: ignore[attr-defined]
        app.add_api_route("/api/v1/test-multi/{item_id}", update_item, methods=["PATCH"])  # type: ignore[attr-defined]
        assert client.get("/api/v1/test-multi/a1").status_code == 200
        response = client.delete("/api/v1/test-multi/a1")
        assert response.status_code == 405
        assert response.headers["allow"] == "GET, HEAD, PATCH"
        assert response.json()["code"] == "method_not_allowed"


def test_405_depends_on_the_route_only_and_404_is_preserved(
    settings: Settings, no_spa: Path
) -> None:
    # A supported method on a missing (or another organization's) record stays 404; an
    # unsupported method gets the same 405 for every ID, so it reveals nothing about records.
    def get_record(record_id: str) -> dict[str, str]:
        raise AppError("not_found")

    for client in make_client(settings, no_spa):
        client.app.add_api_route("/api/v1/test-records/{record_id}", get_record, methods=["GET"])  # type: ignore[attr-defined]
        missing = client.get("/api/v1/test-records/does-not-exist")
        assert missing.status_code == 404
        assert missing.json()["code"] == "not_found"
        assert "allow" not in missing.headers

        first = client.put("/api/v1/test-records/does-not-exist")
        second = client.put("/api/v1/test-records/4e6a8c0d-2f3b-4c5e-9a7d-9f1b3d5f7a9c")
        assert first.status_code == second.status_code == 405
        assert first.headers["allow"] == second.headers["allow"] == "GET, HEAD"

        def comparable(body: dict[str, object]) -> dict[str, object]:
            return {k: v for k, v in body.items() if k not in ("instance", "request_id")}

        assert comparable(first.json()) == comparable(second.json())


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
def test_path_matching_no_route_is_404_for_every_method(client: TestClient, method: str) -> None:
    response = client.request(method, "/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert "allow" not in response.headers


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
