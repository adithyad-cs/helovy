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

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.core.config import Settings, load_settings
from app.core.db import create_db_engine
from app.core.errors import problem_response, register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from app.core.routing import HeadAwareRoute
from app.modules.health.routes import router as health_router
from app.modules.storage.client import create_s3_client

STATIC_DIR = Path(__file__).resolve().parent / "static"

logger = logging.getLogger("app")


# Pages the SPA routes itself (docs/04 §2, docs/08 §12.1). Each is a GET route that also
# answers HEAD (docs/07 §1.14), so another method on these paths is answered 405 with
# ``Allow: GET, HEAD`` (docs/07 §1.13).
SPA_PAGE_PATHS = ("/", "/login", "/app")
SPA_APP_PREFIX = "/app/{rest:path}"


def _file_route(path: Path) -> Any:
    def serve_file() -> FileResponse:
        return FileResponse(path)

    return serve_file


def _mount_spa(app: FastAPI, static_dir: Path) -> None:
    """Serve the built SPA from the same origin (ADR-02).

    Every route below answers GET and HEAD (docs/07 §1.14).

    - ``/assets/...``: hashed build files.
    - ``/``, ``/login``, ``/app`` and ``/app/...``: ``index.html`` with 200.
    - other files at the build root (for example a favicon): served as files.
    - a GET or HEAD for any other path outside ``/api`` and ``/assets``: ``index.html`` with
      **404**, so the SPA renders its not-found page while the HTTP status stays honest
      (``/docs`` is 404 outside development, docs/12 §17).
    - everything else that matches no route, including any ``/api/...`` path: problem+json 404.
    - a path that matches a route with a method it does not support: problem+json 405 with
      ``Allow`` (docs/07 §1.13). There is deliberately no catch-all route: one would make
      every unknown path "exist" for GET and turn its other methods into 405.
    """
    index = static_dir / "index.html"
    if not index.is_file():
        logger.info("SPA build not found at %s; only the API is served", static_dir)
        return
    root = static_dir.resolve()
    app.mount("/assets", StaticFiles(directory=root / "assets", check_dir=False), name="assets")

    def serve_index() -> FileResponse:
        return FileResponse(index, media_type="text/html")

    def serve_app_page(rest: str) -> FileResponse:
        return FileResponse(index, media_type="text/html")

    for page in SPA_PAGE_PATHS:
        app.add_api_route(page, serve_index, methods=["GET"], include_in_schema=False)
    app.add_api_route(SPA_APP_PREFIX, serve_app_page, methods=["GET"], include_in_schema=False)

    for file in sorted(p for p in root.iterdir() if p.is_file() and p.name != "index.html"):
        app.add_api_route(
            f"/{file.name}", _file_route(file), methods=["GET"], include_in_schema=False
        )

    async def not_found(request: Request, exc: Exception) -> Response:
        path = request.url.path
        is_api = path == "/api" or path.startswith("/api/")
        is_page_read = request.method in ("GET", "HEAD")
        if is_page_read and not is_api and not path.startswith("/assets/"):
            return FileResponse(index, status_code=404, media_type="text/html")
        return problem_response("not_found", instance=path)

    app.add_exception_handler(404, not_found)


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
    # Every route added to the application answers HEAD wherever it answers GET; routers
    # included later bring their own HeadAwareRoute class (docs/07 §1.14).
    app.router.route_class = HeadAwareRoute
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
