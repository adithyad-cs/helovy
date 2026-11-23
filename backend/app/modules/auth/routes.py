"""E-03 ``POST /api/v1/auth/login``, E-04 ``POST /api/v1/auth/logout``, E-05 ``GET /me``.

The session cookie ``ps5_session`` is HttpOnly, Secure, SameSite=Lax, Path=/, host-only,
with Max-Age 7 days (docs/07 §1.2; docs/12 §4.1). Browsers treat http://localhost as a
secure context, so the Secure cookie also works for the local demonstration (V-12).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.config import Settings
from app.core.db import get_db
from app.core.routing import HeadAwareRoute
from app.core.schemas import require_json_body, rfc3339
from app.modules.auth import service
from app.modules.auth.csrf import SESSION_COOKIE
from app.modules.auth.dependencies import authenticate, client_ip, presented_token
from app.modules.auth.schemas import LoginRequest
from app.modules.auth.security import csrf_token
from app.modules.auth.service import SessionContext

COOKIE_MAX_AGE = int(service.SESSION_ABSOLUTE.total_seconds())  # 604800

# The business summary ({"id", "legal_name"}) comes from the businesses module, which auth
# must not import (docs/04 §3). The application factory installs the provider.
BusinessSummary = Callable[[Session, uuid.UUID], dict[str, str] | None]

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
    route_class=HeadAwareRoute,
    dependencies=[Depends(require_json_body)],
)


def session_body(request: Request, db: Session, context: SessionContext) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    provider: BusinessSummary | None = getattr(request.app.state, "business_summary", None)
    return {
        "user": {
            "id": str(context.user_id),
            "email": context.email,
            "display_name": context.display_name,
        },
        "organization": {"id": str(context.org_id), "name": context.org_name},
        "role": context.role,
        "business": provider(db, context.org_id) if provider else None,
        "csrf_token": csrf_token(settings.csrf_key, context.session_id),
        "session_expires_at": rfc3339(context.expires_at),
    }


@router.post("/login")
def login(
    body: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> JSONResponse:
    result = service.login(
        db,
        request.app.state.settings,
        now=clock.now(),
        email=body.email,
        password=body.password,
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent"),
        presented_token=presented_token(request),
    )
    response = JSONResponse(session_body(request, db, result.context))
    response.set_cookie(
        SESSION_COOKIE,
        result.token,
        max_age=COOKIE_MAX_AGE,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    context: Annotated[SessionContext, Depends(authenticate)],
    db: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> Response:
    service.logout(db, now=clock.now(), context=context, ip=client_ip(request))
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    return response


@router.get("/me")
def me(
    request: Request,
    context: Annotated[SessionContext, Depends(authenticate)],
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    return JSONResponse(session_body(request, db, context))
