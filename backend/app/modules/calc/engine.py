"""Invoice calculation ``calc-1.0.0`` (docs/09 §2, §3, §4.1, §4.3).

Pure functions only: no I/O and no imports from other modules (docs/04 §3, rule 1).
Values enter as strings, are checked against the documented patterns and converted with
``Decimal(string)``; ``float`` is never used. Arithmetic runs in a local context with
precision 28 and the default traps on. Each line is rounded with ROUND_HALF_UP to 0.01, and
the rounded values are summed; totals are never re-rounded.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from typing import Literal

CALC_VERSION = "calc-1.0.0"

MONEY = Decimal("0.01")
QUANTITY = Decimal("0.001")
ZERO = Decimal("0.00")
HUNDRED = Decimal(100)

QUANTITY_MAX = Decimal("1000000")
UNIT_PRICE_MAX = Decimal("10000000.00")
PERCENT_MAX = Decimal("100")
GRAND_TOTAL_MAX = Decimal("9999999999999.99")
MAX_LINES = 200

DiscountType = Literal["none", "percent", "amount"]
DISCOUNT_TYPES: tuple[DiscountType, ...] = ("none", "percent", "amount")

# docs/09 §4.1 patterns.
_QUANTITY = re.compile(r"^(0|[1-9][0-9]{0,6})(\.[0-9]{1,3})?$")
_MONEY = re.compile(r"^(0|[1-9][0-9]{0,7})(\.[0-9]{1,2})?$")
_PERCENT = re.compile(r"^(0|[1-9][0-9]{0,2})(\.[0-9]{1,2})?$")
# A plain decimal: digits, no sign, exponent, spaces, grouping or leading zeros.
_PLAIN = re.compile(r"^(0|[1-9][0-9]*)(\.([0-9]+))?$")


def _context() -> Context:
    return Context(prec=28, rounding=ROUND_HALF_UP)


class CalcError(ValueError):
    """An input rule failed; ``code`` is the docs/07 §1.5 field error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def round2(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def money_str(value: Decimal) -> str:
    """Money and percent output: exactly 2 decimals, never an exponent (docs/09 §2.4)."""
    return format(value.quantize(MONEY, rounding=ROUND_HALF_UP), "f")


def quantity_str(value: Decimal) -> str:
    """Quantity output: exactly 3 decimals (docs/07 §1.4)."""
    return format(value.quantize(QUANTITY, rounding=ROUND_HALF_UP), "f")


def _parse(
    value: object,
    *,
    pattern: re.Pattern[str],
    decimals: int,
    minimum: Decimal,
    minimum_inclusive: bool,
    maximum: Decimal,
    range_message: str,
) -> Decimal:
    if not isinstance(value, str):
        raise CalcError("must_be_string", 'Send this value as a string, for example "2.5".')
    plain = _PLAIN.match(value)
    if plain is None:
        raise CalcError("invalid_decimal", "Enter a number such as 2.5, without signs or spaces.")
    fraction = plain.group(3) or ""
    if len(fraction) > decimals:
        noun = "decimal place" if decimals == 1 else "decimal places"
        raise CalcError("too_many_decimals", f"Use at most {decimals} {noun}.")
    number = Decimal(value)
    below = number < minimum if minimum_inclusive else number <= minimum
    if below or number > maximum or pattern.match(value) is None:
        raise CalcError("out_of_range", range_message)
    return number


def parse_quantity(value: object) -> Decimal:
    """``quantity``: > 0 and ≤ 1,000,000, at most 3 decimals (docs/09 §4.1)."""
    return _parse(
        value,
        pattern=_QUANTITY,
        decimals=3,
        minimum=Decimal(0),
        minimum_inclusive=False,
        maximum=QUANTITY_MAX,
        range_message="Enter a quantity above 0 and up to 10,00,000.",
    )


def parse_unit_price(value: object) -> Decimal:
    """``unit_price``: ≥ 0.00 and ≤ 10,000,000.00, at most 2 decimals."""
    return _parse(
        value,
        pattern=_MONEY,
        decimals=2,
        minimum=Decimal(0),
        minimum_inclusive=True,
        maximum=UNIT_PRICE_MAX,
        range_message="Enter a price from ₹0.00 to ₹1,00,00,000.00.",
    )


def parse_percent(value: object) -> Decimal:
    """A percent discount: > 0 and ≤ 100, at most 2 decimals."""
    return _parse(
        value,
        pattern=_PERCENT,
        decimals=2,
        minimum=Decimal(0),
        minimum_inclusive=False,
        maximum=PERCENT_MAX,
        range_message="Enter a percentage above 0 and up to 100.",
    )


def parse_amount_discount(value: object) -> Decimal:
    """An amount discount: > 0.00 (the ≤ gross rule is checked with the line)."""
    return _parse(
        value,
        pattern=_MONEY,
        decimals=2,
        minimum=Decimal(0),
        minimum_inclusive=False,
        maximum=UNIT_PRICE_MAX * QUANTITY_MAX,
        range_message="Enter a discount above ₹0.00.",
    )


@dataclass(frozen=True)
class LineInput:
    quantity: Decimal
    unit_price: Decimal
    discount_type: DiscountType
    discount_value: Decimal | None


@dataclass(frozen=True)
class LineResult:
    gross: Decimal
    discount: Decimal
    line_total: Decimal


@dataclass(frozen=True)
class Totals:
    gross_total: Decimal
    discount_total: Decimal
    grand_total: Decimal


@dataclass(frozen=True)
class DocumentResult:
    lines: tuple[LineResult, ...]
    totals: Totals


def line_gross(quantity: Decimal, unit_price: Decimal) -> Decimal:
    with localcontext(_context()):
        return round2(quantity * unit_price)


def calculate_line(line: LineInput) -> LineResult:
    """Steps 1-3 of docs/09 §3. Raises CalcError ``exceeds_gross`` for an amount discount."""
    with localcontext(_context()):
        gross = round2(line.quantity * line.unit_price)
        if line.discount_type == "none":
            discount = ZERO
        elif line.discount_type == "percent":
            if line.discount_value is None:
                raise CalcError("required", "Enter the discount percentage.")
            discount = round2(gross * line.discount_value / HUNDRED)
        else:
            if line.discount_value is None:
                raise CalcError("required", "Enter the discount amount.")
            if line.discount_value > gross:
                raise CalcError(
                    "exceeds_gross",
                    f"The discount cannot be more than the line amount (₹{money_str(gross)}).",
                )
            discount = round2(line.discount_value)
        return LineResult(gross=gross, discount=discount, line_total=gross - discount)


def calculate_document(lines: Sequence[LineInput]) -> DocumentResult:
    """Steps 4-7 of docs/09 §3. Raises CalcError ``total_too_large`` above the limit."""
    if len(lines) > MAX_LINES:
        raise CalcError("too_many_lines", f"Use at most {MAX_LINES} lines.")
    with localcontext(_context()):
        results = tuple(calculate_line(line) for line in lines)
        gross_total = sum((r.gross for r in results), ZERO)
        discount_total = sum((r.discount for r in results), ZERO)
        grand_total = sum((r.line_total for r in results), ZERO)
    if grand_total > GRAND_TOTAL_MAX:
        raise CalcError("total_too_large", "The total is above the allowed maximum.")
    return DocumentResult(results, Totals(gross_total, discount_total, grand_total))
