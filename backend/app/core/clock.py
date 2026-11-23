"""One injectable clock (docs/04 §5).

The application reads the current time only through ``app.state.clock``, so tests can
freeze it for session expiry, throttling windows and financial-year boundaries (docs/11 §1).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

from fastapi import Request


class Clock(Protocol):
    def now(self) -> datetime:
        """The current time, timezone-aware, in UTC."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FrozenClock:
    """A clock that only moves when told to (test helper; also usable from the CLI)."""

    def __init__(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("FrozenClock needs a timezone-aware datetime")
        self._now = at.astimezone(UTC)

    def now(self) -> datetime:
        return self._now

    def set(self, at: datetime) -> None:
        self._now = at.astimezone(UTC)

    def advance(self, delta: timedelta) -> None:
        self._now += delta


def get_clock(request: Request) -> Clock:
    clock: Clock = request.app.state.clock
    return clock
