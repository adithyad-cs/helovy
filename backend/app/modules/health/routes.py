"""E-01 ``GET /healthz`` and E-02 ``GET /readyz`` (docs/07 §4). No ``/api/v1`` prefix.

Readiness checks the database, storage and the template registry: the registered template
files must hash to their registry value; with ``APP_ENV=development`` a mismatch reports
``warn`` (still ready), with ``demo`` or ``production`` it fails (docs/07 E-02).
Both endpoints also answer HEAD (docs/07 §1.14): the same checks run once and give the same
status and headers, without a body.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.db import database_is_ready
from app.core.routing import HeadAwareRoute
from app.modules.rendering import registry
from app.modules.storage.client import bucket_is_ready

router = APIRouter(tags=["health"], route_class=HeadAwareRoute)


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: the process is up. Never touches the database or storage."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz(request: Request) -> JSONResponse:
    """Readiness: 200 when every check passes, otherwise 503 without error details."""
    state: Any = request.app.state
    templates_ok = registry.all_match()
    checks = {
        "database": "ok" if database_is_ready(state.db_engine) else "error",
        "storage": "ok" if bucket_is_ready(state.s3, state.settings.s3_bucket) else "error",
        "templates": "ok"
        if templates_ok
        else ("warn" if state.settings.app_env == "development" else "error"),
    }
    ready = all(value in ("ok", "warn") for value in checks.values())
    return JSONResponse(
        {"status": "ready" if ready else "not_ready", "checks": checks},
        status_code=200 if ready else 503,
    )
