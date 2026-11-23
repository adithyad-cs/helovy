"""The session dependency (docs/04 §7): cookie → valid session → tenant on request.state."""

from __future__ import annotations

import ipaddress
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.config import Settings
from app.core.db import get_db
from app.core.errors import AppError
from app.modules.auth.csrf import MAX_TOKEN_LENGTH, SESSION_COOKIE
from app.modules.auth.service import SessionContext, resolve_session
from app.modules.tenancy.dependencies import Tenant, set_tenant


def client_ip(request: Request) -> str | None:
    """The socket address, or the configured proxy header (docs/12 §2.2; V-11).

    ``X-Forwarded-For`` is never trusted unless it is the configured ``CLIENT_IP_HEADER``.
    """
    settings: Settings = request.app.state.settings
    raw: str | None
    if settings.client_ip_header:
        raw = request.headers.get(settings.client_ip_header, "").split(",")[0].strip() or None
    else:
        raw = request.client.host if request.client else None
    if raw is None:
        return None
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None


def presented_token(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token or len(token) > MAX_TOKEN_LENGTH:
        return None
    return token


def authenticate(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SessionContext:
    """401 ``unauthenticated`` unless the cookie names a valid session; sets the tenant."""
    token = presented_token(request)
    context = resolve_session(db, now=clock.now(), token=token) if token else None
    if context is None:
        raise AppError("unauthenticated")
    set_tenant(
        request,
        Tenant(
            org_id=context.org_id,
            user_id=context.user_id,
            role=context.role,
            session_id=context.session_id,
        ),
    )
    request.state.session_context = context
    return context
