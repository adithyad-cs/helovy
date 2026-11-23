"""In-memory sliding-window rate limiter (docs/07 §1.9; docs/04 §3 core).

Single process only (uvicorn runs one worker; docs/05 §1). Uses the application clock, so
tests can move time. A refused request is not counted.
"""

from __future__ import annotations

import math
import threading
from collections import deque
from datetime import datetime, timedelta

from app.core.errors import AppError


class RateLimiter:
    def __init__(self, limit: int, window: timedelta) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[datetime]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, now: datetime) -> None:
        """Count one request for ``key``, or raise 429 ``rate_limited`` with Retry-After."""
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                wait = (hits[0] + self.window - now).total_seconds()
                raise AppError(
                    "rate_limited",
                    detail="Please wait a moment and try again.",
                    headers={"Retry-After": str(max(1, math.ceil(wait)))},
                )
            hits.append(now)
            if len(self._hits) > 10_000:  # bound memory: forget idle keys
                for idle in [k for k, v in self._hits.items() if not v][:1000]:
                    del self._hits[idle]


def default_limiters() -> dict[str, RateLimiter]:
    return {
        "calculate": RateLimiter(60, timedelta(minutes=1)),  # E-14, per session
        "preview": RateLimiter(20, timedelta(minutes=1)),  # E-20, per session
        "render_retry": RateLimiter(1, timedelta(seconds=10)),  # E-23, per document
    }
