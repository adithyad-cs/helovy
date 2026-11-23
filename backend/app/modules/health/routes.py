"""E-01 ``GET /healthz`` and E-02 ``GET /readyz`` (docs/07 §4). No ``/api/v1`` prefix.

Readiness checks the database and storage. The template-hash check is added with the
template registry in M4 (docs/10 §3).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.db import database_is_ready
from app.modules.storage.client import bucket_is_ready

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: the process is up. Never touches the database or storage."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz(request: Request) -> JSONResponse:
    """Readiness: 200 when every check passes, otherwise 503 without error details."""
    state: Any = request.app.state
    checks = {
        "database": "ok" if database_is_ready(state.db_engine) else "error",
        "storage": "ok" if bucket_is_ready(state.s3, state.settings.s3_bucket) else "error",
    }
    ready = all(value == "ok" for value in checks.values())
    return JSONResponse(
        {"status": "ready" if ready else "not_ready", "checks": checks},
        status_code=200 if ready else 503,
    )
