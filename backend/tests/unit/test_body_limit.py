"""Request body limit of 256 KiB → 413 payload_too_large (docs/07 §1.1; part of IT-GEN-01).

M0 has no endpoint that reads a body, so a test-only application exercises the middleware
through both paths: a declared Content-Length, and a chunked body counted while it is read.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import Body, FastAPI, Request
from fastapi.testclient import TestClient

from app.core.errors import register_error_handlers
from app.core.middleware import MAX_BODY_BYTES, BodySizeLimitMiddleware, RequestContextMiddleware


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(RequestContextMiddleware, hsts=False)
    register_error_handlers(app)

    @app.post("/raw")
    async def raw(request: Request) -> dict[str, int]:
        return {"size": len(await request.body())}

    @app.post("/json")
    def parsed(payload: dict[str, Any] = Body(...)) -> dict[str, int]:  # noqa: B008
        return {"keys": len(payload)}

    return TestClient(app)


def _chunks(total: int, size: int = 16 * 1024) -> Iterator[bytes]:
    sent = 0
    while sent < total:
        part = min(size, total - sent)
        sent += part
        yield b"a" * part


def test_limit_is_256_kib() -> None:
    assert MAX_BODY_BYTES == 262_144


def test_body_at_the_limit_is_accepted(client: TestClient) -> None:
    response = client.post("/raw", content=b"a" * MAX_BODY_BYTES)
    assert response.status_code == 200
    assert response.json() == {"size": MAX_BODY_BYTES}


def test_declared_body_over_the_limit_is_rejected(client: TestClient) -> None:
    response = client.post("/raw", content=b"a" * (MAX_BODY_BYTES + 1))
    assert response.status_code == 413
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["code"] == "payload_too_large"
    assert body["status"] == 413
    assert body["request_id"] == response.headers["x-request-id"]


def test_chunked_body_over_the_limit_is_rejected(client: TestClient) -> None:
    response = client.post("/raw", content=_chunks(MAX_BODY_BYTES + 1))
    assert "content-length" not in response.request.headers
    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"


def test_chunked_body_within_the_limit_is_accepted(client: TestClient) -> None:
    response = client.post("/raw", content=_chunks(100_000))
    assert response.status_code == 200
    assert response.json() == {"size": 100_000}


def test_oversized_json_body_parsed_by_fastapi_gives_413_not_400(client: TestClient) -> None:
    payload = b'{"k": "' + b"a" * MAX_BODY_BYTES + b'"}'
    response = client.post(
        "/json", content=_chunks_of(payload), headers={"content-type": "application/json"}
    )
    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"


def _chunks_of(data: bytes, size: int = 16 * 1024) -> Iterator[bytes]:
    for start in range(0, len(data), size):
        yield data[start : start + size]
