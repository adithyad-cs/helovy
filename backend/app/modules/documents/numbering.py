"""Invoice numbering and the Indian financial year (docs/09 §7; docs/06 §6).

Numbers are allocated only inside the finalisation transaction (docs/09 §8 step 7) and are
formatted here, in Python, never with SQL ``lpad`` (which truncates).
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

INDIA = ZoneInfo("Asia/Kolkata")
PREFIX = "INV"
MAX_NUMBER_LENGTH = 16


class NumberSeriesExhaustedError(ValueError):
    """The sequence passed 999,999 for the year, or the number would exceed 16 characters."""


def issue_date_for(moment: datetime) -> date:
    """The Asia/Kolkata calendar date of an instant (docs/09 §7)."""
    if moment.tzinfo is None:
        raise ValueError("needs a timezone-aware instant")
    return moment.astimezone(INDIA).date()


def financial_year(day: date) -> str:
    """1 April to 31 March, labelled ``YY-YY``: 2026-11-25 → ``26-27``; 2099-04-01 → ``99-00``."""
    start = day.year if day.month >= 4 else day.year - 1
    return f"{start % 100:02d}-{(start + 1) % 100:02d}"


def format_number(prefix: str, fy: str, sequence: int) -> str:
    """``INV/26-27/00001``; 5 digits growing to 6; above 999,999 → exhausted."""
    if not 1 <= sequence <= 999_999:
        raise NumberSeriesExhaustedError(sequence)
    number = f"{prefix}/{fy}/{sequence:05d}"
    if len(number) > MAX_NUMBER_LENGTH:
        raise NumberSeriesExhaustedError(number)
    return number
