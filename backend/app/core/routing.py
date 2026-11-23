"""Route class that answers HEAD wherever it answers GET (docs/07 §1.14; RFC 9110 §9.1, §9.3.2).

FastAPI's ``APIRoute`` does not add HEAD to GET routes (Starlette's own ``Route`` does).
``HeadAwareRoute`` matches HEAD exactly like GET and runs the GET endpoint **once**, with
``request.method == "HEAD"``, so an endpoint can skip work or side effects that only matter
when content is sent (for example the ``document.pdf_downloaded`` audit event in M5).
``RequestContextMiddleware`` drops the body of every HEAD response; the status and headers
stay exactly as the GET endpoint produced them.

The route keeps declaring only GET, so the OpenAPI document lists no separate HEAD
operations. Every application router uses this class; a test enforces that.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import routing as fastapi_routing
from fastapi.routing import APIRoute
from starlette.routing import Match
from starlette.types import Receive, Scope, Send

# FastAPI 0.165 runs the routes of included routers through an "effective route context"
# whose ASGI app carries the include-level dependencies (for example the session dependency
# added in main.py). APIRoute.handle selects it, then refuses methods the route does not
# declare; HEAD must use the same app without that GET-only method check. The helper is
# private, so its absence (another FastAPI version) falls back to the route's own app, and
# tests/integration/test_head.py fails if include-level dependencies stop running for HEAD.
_effective_context: Callable[[Scope], Any] | None = getattr(
    fastapi_routing, "_get_scope_effective_route_context", None
)


class HeadAwareRoute(APIRoute):
    def _answers_head(self, scope: Scope) -> bool:
        return scope["method"] == "HEAD" and "GET" in (self.methods or ())

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        if scope["type"] == "http" and self._answers_head(scope):
            # Match the path as GET would; the request itself keeps its HEAD method.
            return super().matches({**scope, "method": "GET"})
        return super().matches(scope)

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self._answers_head(scope):
            context = _effective_context(scope) if _effective_context else None
            if context is not None and context.original_route is self and context.app:
                await context.app(scope, receive, send)
            else:
                await self.app(scope, receive, send)
            return
        await super().handle(scope, receive, send)
