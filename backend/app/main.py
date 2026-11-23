"""Application factory (docs/04 §5).

``create_app()`` loads settings (failing fast on missing or invalid values), configures
JSON logging, registers middleware, error handlers and routers, and mounts the built SPA.

``uvicorn app.main:app`` works as documented in docs/05 §10: the module attribute ``app``
is created on first access, so importing this module never needs a configured environment.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import Settings, load_settings
from app.core.db import create_db_engine
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from app.modules.health.routes import router as health_router
from app.modules.storage.client import create_s3_client

STATIC_DIR = Path(__file__).resolve().parent / "static"

logger = logging.getLogger("app")


def _is_spa_route(path: str) -> bool:
    """Paths the SPA routes itself (docs/04 §2, docs/08 §12.1)."""
    return path in ("/", "/login", "/app") or path.startswith("/app/")


def _mount_spa(app: FastAPI, static_dir: Path) -> None:
    """Serve the built SPA from the same origin (ADR-02).

    - ``/assets/...``: hashed build files.
    - ``/``, ``/login``, ``/app/...``: ``index.html`` with 200.
    - other files at the build root (for example a favicon): served as files.
    - any other path outside ``/api``: ``index.html`` with **404**, so the SPA renders its
      not-found page while the HTTP status stays honest (``/docs`` is 404 outside development).
    - ``/api/...`` paths that match no endpoint: problem+json 404.
    """
    index = static_dir / "index.html"
    if not index.is_file():
        logger.info("SPA build not found at %s; only the API is served", static_dir)
        return
    root = static_dir.resolve()
    app.mount("/assets", StaticFiles(directory=root / "assets", check_dir=False), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise StarletteHTTPException(status_code=404)
        if _is_spa_route("/" + full_path):
            return FileResponse(index, media_type="text/html")
        candidate = (root / full_path).resolve()
        if (
            full_path
            and candidate.is_file()
            and candidate.is_relative_to(root)
            and candidate.name != "index.html"
        ):
            return FileResponse(candidate)
        return FileResponse(index, status_code=404, media_type="text/html")


def create_app(settings: Settings | None = None, *, static_dir: Path = STATIC_DIR) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        app.state.db_engine.dispose()

    app = FastAPI(
        title="HIVE DOCS API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    app.state.settings = settings
    app.state.db_engine = create_db_engine(settings)
    app.state.s3 = create_s3_client(settings)

    # Starlette wraps in reverse order of registration: the last added is the outermost.
    # Effective order: request ID + security headers → body size limit → routing.
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(RequestContextMiddleware, hsts=settings.is_https)
    register_error_handlers(app)

    app.include_router(health_router)
    _mount_spa(app, static_dir)
    logger.info("application created", extra={"event": "app.created"})
    return app


_app: FastAPI | None = None


def __getattr__(name: str) -> Any:
    """Create the module-level ``app`` lazily (``uvicorn app.main:app``)."""
    global _app
    if name == "app":
        if _app is None:
            _app = create_app()
        return _app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
