"""ASGI middleware (docs/04 §5): request ID → security headers → body size limit → routing.

``RequestContextMiddleware`` is the outermost application middleware. It assigns the
request ID, adds the security headers of docs/12 §4.3 and ``Cache-Control`` to every
response, turns unhandled exceptions into a 500 problem response (so even that response
carries the headers), drops the body of every HEAD response (docs/07 §1.14; RFC 9110
§9.3.2) while keeping the GET status and headers, and writes one JSON access line per request.

The Origin and CSRF check for unsafe methods sits between the body limit and routing
(``app.modules.auth.csrf``, owned by the auth module; docs/04 §3).
"""

from __future__ import annotations

import logging
import re
import secrets
import time

from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import problem_response
from app.core.logging import request_id_var

MAX_BODY_BYTES = 256 * 1024  # docs/07 §1.1

_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

SECURITY_HEADERS: tuple[tuple[str, str], ...] = (
    (
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src blob:; "
        "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
    ),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "same-origin"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"),
    ("X-Frame-Options", "DENY"),
)
HSTS_VALUE = "max-age=31536000"
ASSET_CACHE_CONTROL = "public, max-age=31536000, immutable"

access_logger = logging.getLogger("app.access")
error_logger = logging.getLogger("app.errors")


def new_request_id() -> str:
    return "req_" + secrets.token_urlsafe(12)


def _route_label(scope: Scope) -> str:
    """The matched route template for logs; never the raw path (it may carry identifiers)."""
    route_path = getattr(scope.get("route"), "path", None)
    if route_path:
        return str(route_path)
    if str(scope.get("path", "")).startswith("/assets/"):
        return "/assets/{file}"  # static mount: Starlette records no route for mounts
    return "unmatched"


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, *, hsts: bool) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get("x-request-id", "")
        request_id = incoming if _REQUEST_ID.match(incoming) else new_request_id()
        token = request_id_var.set(request_id)
        path: str = scope["path"]
        is_head = scope["method"] == "HEAD"
        started = time.perf_counter()
        response: dict[str, int | bool] = {"status": 500, "started": False}

        async def send_with_headers(message: Message) -> None:
            if is_head and message["type"] == "http.response.body":
                # A HEAD response carries no content; Content-Length and the other headers
                # stay as the GET response would send them (RFC 9110 §9.3.2).
                message = {**message, "body": b""}
            if message["type"] == "http.response.start":
                status = int(message["status"])
                response["status"] = status
                response["started"] = True
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                for name, value in SECURITY_HEADERS:
                    headers[name] = value
                if self.hsts:
                    headers["Strict-Transport-Security"] = HSTS_VALUE
                if path.startswith("/assets/") and status == 200:
                    headers["Cache-Control"] = ASSET_CACHE_CONTROL
                else:
                    headers["Cache-Control"] = "no-store"
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception:
            error_logger.exception("unhandled exception")
            if response["started"]:
                raise
            await problem_response("internal_error", instance=path)(
                scope, receive, send_with_headers
            )
        finally:
            access_logger.info(
                "request",
                extra={
                    "event": "http.request",
                    "method": scope.get("method"),
                    "route": _route_label(scope),
                    "status": response["status"],
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    # Set by the session dependency: identifiers only (docs/12 §10).
                    "org_id": scope.get("state", {}).get("log_org_id"),
                    "user_id": scope.get("state", {}).get("log_user_id"),
                },
            )
            request_id_var.reset(token)


class BodySizeLimitMiddleware:
    """Rejects bodies over ``max_bytes`` with 413 ``payload_too_large`` (docs/07 §1.1).

    A declared Content-Length over the limit is refused before the body is read. A body
    without Content-Length (chunked) is counted while it is read; crossing the limit raises
    an HTTP 413 error, which FastAPI passes through unchanged to the problem+json handler.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = Headers(scope=scope).get("content-length")
        if declared is not None:
            if not declared.isdigit():
                await problem_response("malformed_request", instance=scope["path"])(
                    scope, receive, send
                )
                return
            if int(declared) > self.max_bytes:
                await problem_response("payload_too_large", instance=scope["path"])(
                    scope, receive, send
                )
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise StarletteHTTPException(status_code=413)
            return message

        await self.app(scope, limited_receive, send)
