"""RFC 9457 problem details and the error code catalogue (docs/07 §1.5, §1.12).

Clients branch on ``code``. Bodies never contain stack traces, SQL or internal hostnames:
unexpected exceptions become 500 ``internal_error`` and are logged server-side only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match, Mount
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from app.core.logging import request_id_var

PROBLEM_TYPE_BASE = "https://hive-docs.invalid/problems/"  # placeholder domain until Q-26
PROBLEM_MEDIA_TYPE = "application/problem+json"

logger = logging.getLogger("app.errors")


@dataclass(frozen=True)
class ProblemKind:
    status: int
    title: str
    detail: str


# The 25 codes of docs/07 §1.12 with their HTTP status. Titles and details are generic.
CATALOGUE: dict[str, ProblemKind] = {
    "malformed_request": ProblemKind(400, "Malformed request", "The request could not be read."),
    "idempotency_key_missing": ProblemKind(
        400, "Idempotency key missing", "This request needs an Idempotency-Key header."
    ),
    "unauthenticated": ProblemKind(401, "Not signed in", "Sign in to continue."),
    "invalid_credentials": ProblemKind(
        401, "Invalid credentials", "Email or password is incorrect."
    ),
    "csrf_failed": ProblemKind(403, "Request not trusted", "The CSRF token or Origin is invalid."),
    "forbidden_role": ProblemKind(403, "Not allowed", "Your role does not allow this action."),
    "not_found": ProblemKind(404, "Not found", "The requested resource was not found."),
    "method_not_allowed": ProblemKind(
        405, "Method not allowed", "The request method is not supported by this resource."
    ),
    "business_already_exists": ProblemKind(
        409, "Business already exists", "This organization already has a business."
    ),
    "document_not_draft": ProblemKind(
        409, "Document is not a draft", "Finalised documents cannot be changed."
    ),
    "document_not_finalized": ProblemKind(
        409, "Document is not finalised", "The document has not been finalised."
    ),
    "pdf_not_ready": ProblemKind(409, "PDF not ready", "The PDF is not ready yet."),
    "pdf_render_in_progress": ProblemKind(
        409, "PDF render in progress", "The PDF is still being generated."
    ),
    "number_series_exhausted": ProblemKind(
        409, "Number series exhausted", "No more document numbers are available this year."
    ),
    "idempotency_in_progress": ProblemKind(
        409, "Request in progress", "A request with this Idempotency-Key is still running."
    ),
    "version_mismatch": ProblemKind(
        412, "Version mismatch", "The resource was changed by another request."
    ),
    "payload_too_large": ProblemKind(
        413, "Payload too large", "The request body is larger than 256 KiB."
    ),
    "validation_failed": ProblemKind(422, "Some fields are invalid", "Some fields need attention."),
    "finalization_blocked": ProblemKind(
        422, "Finalisation blocked", "The document cannot be finalised yet."
    ),
    "idempotency_key_mismatch": ProblemKind(
        422, "Idempotency key reused", "The Idempotency-Key was used for a different request."
    ),
    "precondition_required": ProblemKind(
        428, "Precondition required", "This request needs an If-Match header."
    ),
    "rate_limited": ProblemKind(429, "Too many requests", "Please wait and try again."),
    "internal_error": ProblemKind(500, "Internal error", "Something went wrong."),
    "integrity_check_failed": ProblemKind(
        500, "Integrity check failed", "The stored file failed its integrity check."
    ),
    "dependency_unavailable": ProblemKind(
        503, "Service unavailable", "A required service is temporarily unavailable."
    ),
}


class AppError(Exception):
    """An expected failure, rendered as problem+json with a catalogue code."""

    def __init__(
        self,
        code: str,
        *,
        detail: str | None = None,
        errors: list[dict[str, str]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        if code not in CATALOGUE:
            raise ValueError(f"unknown error code {code!r}")
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.errors = errors
        self.headers = headers


def problem_response(
    code: str,
    *,
    instance: str,
    detail: str | None = None,
    errors: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    kind = CATALOGUE[code]
    body: dict[str, Any] = {
        "type": PROBLEM_TYPE_BASE + code,
        "title": kind.title,
        "status": kind.status,
        "detail": detail or kind.detail,
        "instance": instance,
        "code": code,
        "request_id": request_id_var.get(),
    }
    if errors is not None and kind.status == 422:
        body["errors"] = errors
    return JSONResponse(
        body, status_code=kind.status, media_type=PROBLEM_MEDIA_TYPE, headers=headers
    )


# Framework HTTP errors mapped onto catalogue codes.
_HTTP_STATUS_CODES = {
    400: "malformed_request",
    401: "unauthenticated",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    429: "rate_limited",
    503: "dependency_unavailable",
}

# Pydantic error types mapped onto the field error codes of docs/07 §1.5. Body endpoints
# arrive from M1 onwards and extend this mapping with their own validators.
_FIELD_CODES = {
    "missing": "required",
    "extra_forbidden": "unknown_field",
    "string_too_long": "too_long",
    "string_too_short": "too_short",
    "string_type": "must_be_string",
    "literal_error": "invalid_choice",
    "enum": "invalid_choice",
}

# Custom validators raise errors whose type already is a documented field code (07 §1.5).
DOCUMENTED_FIELD_CODES = frozenset(
    {
        "required", "unknown_field", "not_null",
        "must_be_string", "invalid_decimal", "too_many_decimals",
        "out_of_range", "too_long", "too_short", "invalid_format", "invalid_choice",
        "exceeds_gross", "state_mismatch", "not_found", "inactive",
        "too_many_lines", "no_lines", "total_too_large", "zero_total",
        "due_date_before_issue_date",
    }
)  # fmt: skip


def field_code(error_type: str) -> str:
    """The docs/07 §1.5 field error code for a Pydantic error type."""
    if error_type in DOCUMENTED_FIELD_CODES:
        return error_type
    return _FIELD_CODES.get(error_type, "invalid_format")


def json_pointer(loc: tuple[int | str, ...]) -> str:
    """RFC 6901 pointer for a Pydantic error location: ("body", "lines", 1, "x") -> /lines/1/x."""
    parts = loc[1:] if loc and loc[0] in ("body", "query", "path", "header") else loc
    escaped = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(escaped) if escaped else ""


async def _app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(AppError, exc)
    return problem_response(
        error.code,
        instance=request.url.path,
        detail=error.detail,
        errors=error.errors,
        headers=error.headers,
    )


# Methods probed when building Allow: the RFC 9110 methods an application route can serve,
# plus PATCH (RFC 5789). CONNECT and TRACE are never routed.
PROBE_METHODS = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")


def allowed_methods(request: Request) -> list[str]:
    """Every method the requested path supports, across all routes (RFC 9110 §15.5.6).

    Starlette reports only the methods of the first route that matches the path. A path can
    be served by several routes (from M2, for example GET and PATCH on
    ``/api/v1/businesses/{business_id}``), possibly inside included routers, and ``Allow``
    must list all of their methods. Each method is therefore probed through the public
    ``matches()`` interface of every top-level route: a method is allowed when some route
    would fully match it. HEAD-aware routes match HEAD wherever they match GET (docs/07
    §1.14). The answer depends on the routes only, never on whether a record exists.
    """
    scope = request.scope
    # A matched mount rewrites root_path; app_root_path keeps the application's own.
    root_path = scope.get("app_root_path", scope.get("root_path", ""))

    def probe(method: str) -> Scope:
        return {"type": "http", "method": method, "path": scope["path"], "root_path": root_path}

    methods: set[str] = set()
    for route in request.app.router.routes:
        if isinstance(route, Mount):
            # A mount matches any method; static files serve GET and HEAD only.
            if isinstance(route.app, StaticFiles) and route.matches(probe("GET"))[0] is Match.FULL:
                methods.update(("GET", "HEAD"))
            continue
        for method in PROBE_METHODS:
            if route.matches(probe(method))[0] is Match.FULL:
                methods.add(method)
    return sorted(methods)


async def _http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(StarletteHTTPException, exc)
    code = _HTTP_STATUS_CODES.get(error.status_code, "internal_error")
    if code == "internal_error":
        logger.error("unmapped HTTP status %s", error.status_code)
    framework_headers = error.headers or {}
    headers: dict[str, str] = {}
    if retry_after := framework_headers.get("Retry-After"):
        headers["Retry-After"] = retry_after
    if error.status_code == 405:
        # RFC 9110 §15.5.6: a 405 response must carry Allow with the supported methods.
        allow = allowed_methods(request) or [
            method.strip() for method in framework_headers.get("Allow", "").split(",")
        ]
        headers["Allow"] = ", ".join(method for method in allow if method)
    return problem_response(code, instance=request.url.path, headers=headers or None)


async def _validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    raw = cast(RequestValidationError, exc).errors()
    if any(error.get("type") == "json_invalid" for error in raw):
        return problem_response("malformed_request", instance=request.url.path)
    errors = [
        {
            "pointer": json_pointer(tuple(error.get("loc", ()))),
            "code": field_code(str(error.get("type"))),
            "message": str(error.get("msg", "Invalid value.")),
        }
        for error in raw
    ]
    noun = "field needs" if len(errors) == 1 else "fields need"
    return problem_response(
        "validation_failed",
        instance=request.url.path,
        detail=f"{len(errors)} {noun} attention.",
        errors=errors,
    )


async def _database_unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    # Connection failures and lock timeouts; never echo the driver message (docs/07 §1.5).
    logger.warning("database unavailable: %s", type(exc).__name__)
    return problem_response("dependency_unavailable", instance=request.url.path)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(OperationalError, _database_unavailable_handler)
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
