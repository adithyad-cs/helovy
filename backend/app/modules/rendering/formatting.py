"""Server-side display formatting for PDFs (docs/09 §6; UT-FMT-01).

Strings in, strings out: money values arrive as the API's decimal strings and are grouped in
the Indian system without ever becoming binary floating-point numbers. The browser applies
the same rules (frontend/src/lib/money.ts).
"""

from __future__ import annotations

import re
from datetime import date

_MONEY = re.compile(r"^(-?)(\d+)\.(\d{2})$")
MINUS = "\u2212"  # U+2212 MINUS SIGN, as in the UI
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def group_indian(digits: str) -> str:
    """Last 3 digits, then groups of 2: ``1234567`` → ``12,34,567``."""
    if len(digits) <= 3:
        return digits
    head, last3 = digits[:-3], digits[-3:]
    groups: list[str] = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + last3


def money(value: str | None) -> str:
    """``"123456.78"`` → ``₹1,23,456.78``."""
    if value is None:
        return "—"
    match = _MONEY.match(value)
    if match is None:
        raise ValueError(f"not a money string: {value!r}")
    sign, whole, paise = match.groups()
    whole = whole.lstrip("0") or "0"
    return f"{MINUS if sign else ''}₹{group_indian(whole)}.{paise}"


def deduction(value: str) -> str:
    """A discount shown as a deduction (U+2212 minus): ``"299.99"`` → minus ``₹299.99``;
    zero stays ``₹0.00``."""
    shown = money(value)
    return shown if value.strip("0") == "." else MINUS + shown


def quantity(value: str) -> str:
    """Trailing zeros removed: ``"2.500"`` → ``2.5``; ``"3.000"`` → ``3``."""
    if "." not in value:
        return value
    return value.rstrip("0").rstrip(".")


def percent(value: str) -> str:
    """``"10.00"`` → ``10%``; ``"12.50"`` → ``12.5%``."""
    return quantity(value) + "%"


def discount_column(line: dict[str, str | None]) -> str:
    """Percent → ``10% (₹200.00)``; amount → ``₹99.99``; none → ``—`` (docs/09 §6)."""
    kind = line.get("discount_type")
    if kind == "percent":
        return f"{percent(str(line['discount_value']))} ({money(line.get('discount'))})"
    if kind == "amount":
        return money(line.get("discount"))
    return "—"


def long_date(value: str | None) -> str:
    """``2026-11-25`` → ``25 Nov 2026``."""
    if not value:
        return "—"
    parsed = date.fromisoformat(value)
    return f"{parsed.day:02d} {_MONTHS[parsed.month - 1]} {parsed.year}"


FILTERS = {
    "money": money,
    "deduction": deduction,
    "quantity": quantity,
    "percent": percent,
    "discount_column": discount_column,
    "long_date": long_date,
}
