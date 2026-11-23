"""Origin and CSRF check for unsafe methods (docs/07 §1.3; docs/12 §4.2; docs/04 §5).

Placed after the body size limit and before routing, so an unsafe request that fails the
check gets 403 ``csrf_failed`` before any route, session, tenant or record is considered
(docs/07 §1.13).

- Every request whose method is not safe (GET, HEAD, OPTIONS, TRACE) must carry
  ``Origin`` equal to ``APP_ORIGIN``.
- Sign-in (E-03) has no session yet, so it is checked for ``Origin`` only (login CSRF).
- Every other unsafe request must also carry ``X-CSRF-Token`` equal to
  base64url(HMAC-SHA256(CSRF_SECRET, session ID)) for the session named by the
  ``ps5_session`` cookie, compared in constant time. The session row is found by its token
  hash whatever its state: whether the session is still valid is decided afterwards by the
  session dependency (401), so a revoked cookie with its token gets 401, not 403 (IT-AUTH-04).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers
from starlette.requests import cookie_parser
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.errors import problem_response
from app.modules.auth import security
from app.modules.auth.service import session_id_for_token

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
LOGIN_PATH = "/api/v1/auth/login"
SESSION_COOKIE = "ps5_session"
MAX_TOKEN_LENGTH = 256

logger = logging.getLogger("app.auth")


class CsrfOriginMiddleware:
    def __init__(self, app: ASGIApp, *, origin: str, csrf_key: bytes) -> None:
        self.app = app
        self.origin = origin
        self.csrf_key = csrf_key

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in SAFE_METHODS:
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        if headers.get("origin") != self.origin:
            await self._deny(scope, receive, send)
            return
        if scope["path"] != LOGIN_PATH:
            presented = headers.get("x-csrf-token", "")
            cookie = cookie_parser(headers.get("cookie", "")).get(SESSION_COOKIE, "")
            if not presented or not cookie or len(cookie) > MAX_TOKEN_LENGTH:
                await self._deny(scope, receive, send)
                return
            try:
                session_id = await run_in_threadpool(self._lookup, scope, cookie)
            except Exception as exc:  # noqa: BLE001 - the database is unavailable
                logger.warning("CSRF session lookup failed: %s", type(exc).__name__)
                await problem_response("dependency_unavailable", instance=scope["path"])(
                    scope, receive, send
                )
                return
            if session_id is None or not security.csrf_token_valid(
                self.csrf_key, session_id, presented
            ):
                await self._deny(scope, receive, send)
                return
        await self.app(scope, receive, send)

    @staticmethod
    def _lookup(scope: Scope, cookie: str) -> uuid.UUID | None:
        state: Any = scope["app"].state
        with state.db_sessions() as db:
            return session_id_for_token(db, cookie)

    @staticmethod
    async def _deny(scope: Scope, receive: Receive, send: Send) -> None:
        await problem_response("csrf_failed", instance=scope["path"])(scope, receive, send)
