"""The SPA is served by the same deployment (docs/04 §2, ADR-02; M0.5).

A minimal stand-in build (test fixture) checks the routing rules; the real Vite build is
checked in the Docker image.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from tests.integration.conftest import make_client

INDEX = "<!doctype html><html lang='en-IN'><title>test build</title></html>"


@pytest.fixture
def spa_client(settings: Settings, tmp_path: Path, test_bucket: str) -> Iterator[TestClient]:
    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text(INDEX)
    (static / "assets" / "index-abc123.js").write_text("console.log('ok')")
    (static / "favicon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    (tmp_path / "outside.txt").write_text("must never be served")
    yield from make_client(settings, static)


@pytest.mark.parametrize("path", ["/", "/login", "/app", "/app/customers", "/app/invoices/123"])
def test_spa_routes_serve_index(spa_client: TestClient, path: str) -> None:
    response = spa_client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text == INDEX
    assert response.headers["cache-control"] == "no-store"
    assert "content-security-policy" in response.headers


def test_hashed_assets_are_long_cached(spa_client: TestClient) -> None:
    response = spa_client.get("/assets/index-abc123.js")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_asset_requests_are_logged_with_a_route_template(
    spa_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="app.access"):
        spa_client.get("/assets/index-abc123.js")
    routes = [getattr(r, "route", None) for r in caplog.records if r.name == "app.access"]
    assert routes == ["/assets/{file}"]


def test_missing_asset_is_a_problem_404(spa_client: TestClient) -> None:
    response = spa_client.get("/assets/missing.js")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert response.headers["cache-control"] == "no-store"


def test_root_files_are_served(spa_client: TestClient) -> None:
    response = spa_client.get("/favicon.svg")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")


@pytest.mark.parametrize("path", ["/unknown", "/docs-like-path", "/index.html"])
def test_other_paths_render_the_spa_not_found_page_with_404(
    spa_client: TestClient, path: str
) -> None:
    response = spa_client.get(path)
    assert response.status_code == 404
    assert response.text == INDEX


def test_unknown_api_path_stays_problem_json(spa_client: TestClient) -> None:
    response = spa_client.get("/api/v1/nope")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.parametrize("path", ["/", "/login", "/app", "/app/customers", "/favicon.svg"])
@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
def test_unsupported_method_on_spa_page_is_405_with_allow_get(
    spa_client: TestClient, method: str, path: str
) -> None:
    # The function name predates HEAD support; GET resources list GET and HEAD (docs/07 §1.14).
    response = spa_client.request(method, path)
    assert response.status_code == 405
    assert response.headers["allow"] == "GET, HEAD"
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "method_not_allowed"


def test_unsupported_method_on_asset_is_405_with_allow_get_head(spa_client: TestClient) -> None:
    response = spa_client.post("/assets/index-abc123.js")
    assert response.status_code == 405
    assert response.headers["allow"] == "GET, HEAD"
    assert response.json()["code"] == "method_not_allowed"


@pytest.mark.parametrize("path", ["/unknown", "/api/v1/nope", "/docs-like-path"])
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_unknown_path_is_404_not_405_for_other_methods(
    spa_client: TestClient, method: str, path: str
) -> None:
    # No catch-all route: a path that matches no route stays 404 for every method.
    response = spa_client.request(method, path)
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "not_found"
    assert "allow" not in response.headers


def test_health_endpoints_are_not_shadowed(spa_client: TestClient) -> None:
    assert spa_client.get("/healthz").json() == {"status": "ok"}


@pytest.mark.parametrize(
    "path", ["/..%2foutside.txt", "/%2e%2e/outside.txt", "/assets/../../outside.txt"]
)
def test_path_traversal_is_not_served(spa_client: TestClient, path: str) -> None:
    response = spa_client.get(path)
    assert "must never be served" not in response.text


def test_docs_path_is_404_outside_development_even_with_spa(
    settings: Settings, tmp_path: Path, test_bucket: str
) -> None:
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text(INDEX)
    for client in make_client(settings.model_copy(update={"app_env": "demo"}), static):
        assert client.get("/docs").status_code == 404  # docs/12 §17 manual check
