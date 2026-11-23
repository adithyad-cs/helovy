"""HEAD support for every GET resource (docs/07 §1.14; RFC 9110 §9.1, §9.3.2; IT-GEN-01).

A HEAD response has the status and the header fields of the corresponding GET response and
no body. The endpoint runs once, sees ``request.method == "HEAD"``, and ``Allow`` lists HEAD
wherever it lists GET. Unknown resources keep their 404 behaviour.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import APIRouter, FastAPI, Request
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import SecretStr
from starlette.routing import Route

from app.core.config import Settings
from app.core.routing import HeadAwareRoute
from tests.integration.conftest import SPA_INDEX, build_test_spa, make_client

# Values that legitimately differ between two requests: each response has its own request ID.
VOLATILE_HEADERS = {"x-request-id", "date"}
UNREACHABLE_DB = "postgresql+psycopg://ps5_app:unused@127.0.0.1:1/ps5_test"


def comparable_headers(response: httpx.Response) -> dict[str, str]:
    return {k.lower(): v for k, v in response.headers.items() if k.lower() not in VOLATILE_HEADERS}


def assert_head_matches_get(client: TestClient, path: str) -> tuple[httpx.Response, httpx.Response]:
    get = client.get(path)
    head = client.head(path)
    assert head.status_code == get.status_code
    assert head.content == b""
    assert comparable_headers(head) == comparable_headers(get)
    assert "x-request-id" in head.headers
    if "content-length" in get.headers:
        assert head.headers["content-length"] == str(len(get.content))
    return get, head


@pytest.fixture
def spa_client(settings: Settings, tmp_path: Path, test_bucket: str) -> Iterator[TestClient]:
    yield from make_client(settings, build_test_spa(tmp_path))


# --- Health endpoints (E-01, E-02) ---------------------------------------------------------


@pytest.mark.parametrize("path", ["/healthz", "/readyz"])
def test_head_matches_get_on_health_endpoints(client: TestClient, path: str) -> None:
    get, _ = assert_head_matches_get(client, path)
    assert get.status_code == 200
    assert get.headers["content-type"] == "application/json"


def test_head_matches_get_when_a_dependency_is_down(settings: Settings, no_spa: Path) -> None:
    broken = settings.model_copy(update={"database_url": SecretStr(UNREACHABLE_DB)})
    for client in make_client(broken, no_spa):
        get, _ = assert_head_matches_get(client, "/readyz")
        assert get.status_code == 503
        healthz, _ = assert_head_matches_get(client, "/healthz")
        assert healthz.status_code == 200


# --- Pages, root files and static assets ---------------------------------------------------


@pytest.mark.parametrize(
    "path", ["/", "/login", "/app", "/app/customers", "/favicon.svg", "/assets/index-abc123.js"]
)
def test_head_matches_get_on_pages_files_and_assets(spa_client: TestClient, path: str) -> None:
    get, head = assert_head_matches_get(spa_client, path)
    assert get.status_code == 200
    assert head.headers["etag"] == get.headers["etag"]
    assert head.headers["last-modified"] == get.headers["last-modified"]


def test_head_on_assets_keeps_the_long_cache_header(spa_client: TestClient) -> None:
    head = spa_client.head("/assets/index-abc123.js")
    assert head.headers["cache-control"] == "public, max-age=31536000, immutable"


@pytest.mark.parametrize(
    ("path", "content_type"),
    [
        ("/unknown", "text/html; charset=utf-8"),
        ("/docs-like-path", "text/html; charset=utf-8"),
        ("/api/v1/nope", "application/problem+json"),
        ("/assets/missing.js", "application/problem+json"),
    ],
)
def test_head_on_unknown_resources_keeps_the_404(
    spa_client: TestClient, path: str, content_type: str
) -> None:
    get, head = assert_head_matches_get(spa_client, path)
    assert get.status_code == 404
    assert head.headers["content-type"] == content_type
    assert "allow" not in head.headers


def test_head_on_unknown_page_without_spa_build_is_404(client: TestClient) -> None:
    get, _ = assert_head_matches_get(client, "/unknown")
    assert get.status_code == 404
    assert get.json()["code"] == "not_found"


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
def test_head_matches_get_on_development_docs(client: TestClient, path: str) -> None:
    get, _ = assert_head_matches_get(client, path)
    assert get.status_code == 200


# --- Allow ---------------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/healthz", "/readyz"])
def test_allow_on_get_resources_lists_get_and_head(client: TestClient, path: str) -> None:
    response = client.options(path)
    assert response.status_code == 405
    assert response.headers["allow"] == "GET, HEAD"
    assert response.json()["code"] == "method_not_allowed"


def test_allow_union_inside_an_included_router(settings: Settings, no_spa: Path) -> None:
    # Module routers from M1 onwards are included routers; E-07/E-08 share one path.
    router = APIRouter(route_class=HeadAwareRoute)

    @router.get("/api/v1/test-included/{item_id}")
    def read_item(item_id: str) -> dict[str, str]:
        return {"id": item_id}

    @router.patch("/api/v1/test-included/{item_id}")
    def update_item(item_id: str) -> dict[str, str]:
        return {"id": item_id}

    for client in make_client(settings, no_spa):
        client.app.include_router(router)  # type: ignore[attr-defined]
        assert_head_matches_get(client, "/api/v1/test-included/a1")
        response = client.delete("/api/v1/test-included/a1")
        assert response.status_code == 405
        assert response.headers["allow"] == "GET, HEAD, PATCH"


def test_head_is_not_offered_where_get_is_not_served(settings: Settings, no_spa: Path) -> None:
    def create_item() -> dict[str, str]:
        return {"created": "yes"}

    for client in make_client(settings, no_spa):
        client.app.add_api_route("/api/v1/test-post-only", create_item, methods=["POST"])  # type: ignore[attr-defined]
        response = client.head("/api/v1/test-post-only")
        assert response.status_code == 405
        assert response.headers["allow"] == "POST"
        assert response.content == b""


# --- Single execution, no side effects -----------------------------------------------------


def test_head_runs_the_endpoint_once_and_the_endpoint_sees_head(
    settings: Settings, no_spa: Path
) -> None:
    calls: list[str] = []

    def counted(request: Request) -> dict[str, int]:
        calls.append(request.method)
        return {"calls": len(calls)}

    for client in make_client(settings, no_spa):
        client.app.add_api_route("/api/v1/test-counted", counted, methods=["GET"])  # type: ignore[attr-defined]
        head = client.head("/api/v1/test-counted")
        assert head.status_code == 200
        assert head.content == b""
        assert calls == ["HEAD"]  # once, and HEAD is visible to the endpoint
        client.get("/api/v1/test-counted")
        assert calls == ["HEAD", "GET"]


def test_head_error_response_has_problem_headers_and_no_body(
    settings: Settings, no_spa: Path
) -> None:
    def explode() -> None:
        raise RuntimeError("secret internal detail")

    for client in make_client(settings, no_spa):
        client.app.add_api_route("/api/v1/test-explode", explode, methods=["GET"])  # type: ignore[attr-defined]
        response = client.head("/api/v1/test-explode")
        assert response.status_code == 500
        assert response.headers["content-type"] == "application/problem+json"
        assert int(response.headers["content-length"]) > 0
        assert response.content == b""


def test_access_log_records_head(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="app.access"):
        client.head("/healthz")
    lines = [r for r in caplog.records if r.name == "app.access"]
    assert [(getattr(r, "method", None), getattr(r, "route", None)) for r in lines] == [
        ("HEAD", "/healthz")
    ]


# --- Guard: every GET route of the application answers HEAD --------------------------------


def _get_routes(routes: list[Any]) -> Iterator[Route]:
    for route in routes:
        original = getattr(route, "original_router", None)  # FastAPI's included routers
        if original is not None:
            yield from _get_routes(original.routes)
        elif isinstance(route, Route) and "GET" in (route.methods or ()):
            yield route


def test_every_get_route_answers_head(settings: Settings, tmp_path: Path, test_bucket: str) -> None:
    # Walks the real application (SPA mounted, development docs on), so GET routes added in
    # later milestones are covered automatically.
    for client in make_client(settings, build_test_spa(tmp_path)):
        app: FastAPI = client.app  # type: ignore[assignment]
        routes = list(_get_routes(app.router.routes))
        paths = {route.path for route in routes}
        assert {"/healthz", "/readyz", "/", "/login", "/app", "/app/{rest:path}"} <= paths
        assert {"/favicon.svg", "/docs", "/openapi.json"} <= paths
        for route in routes:
            if isinstance(route, APIRoute):
                assert isinstance(route, HeadAwareRoute), f"{route.path} does not answer HEAD"
            concrete = re.sub(r"\{[^}]+:path\}", "x/y", route.path)
            concrete = re.sub(r"\{[^}]+\}", "x", concrete)
            _, head = assert_head_matches_get(client, concrete)
            assert head.status_code != 405, route.path
        index = client.head("/")
        assert index.headers["content-length"] == str(len(SPA_INDEX))
