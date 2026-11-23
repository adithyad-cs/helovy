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

from fastapi.routing import APIRoute
from starlette.routing import Match
from starlette.types import Receive, Scope, Send


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
            await self.app(scope, receive, send)
            return
        await super().handle(scope, receive, send)
