"""One injectable clock (docs/04 §5).

The application reads the current time only through ``app.state.clock``, so tests can
freeze it for session expiry, throttling windows and financial-year boundaries (docs/11 §1).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class Clock(Protocol):
    def now(self) -> datetime:
        """The current time, timezone-aware, in UTC."""
        ...

    def transaction_now(self, db: Session) -> datetime:
        """The database's ``now()`` inside the current transaction (docs/09 §8 step 4)."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def transaction_now(self, db: Session) -> datetime:
        value: datetime = db.execute(select(func.now())).scalar_one()
        return value.astimezone(UTC)


class FrozenClock:
    """A clock that only moves when told to (test helper; also usable from the CLI)."""

    def __init__(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("FrozenClock needs a timezone-aware datetime")
        self._now = at.astimezone(UTC)

    def now(self) -> datetime:
        return self._now

    def transaction_now(self, db: Session) -> datetime:
        return self._now

    def set(self, at: datetime) -> None:
        self._now = at.astimezone(UTC)

    def advance(self, delta: timedelta) -> None:
        self._now += delta


def get_clock(request: Request) -> Clock:
    clock: Clock = request.app.state.clock
    return clock
