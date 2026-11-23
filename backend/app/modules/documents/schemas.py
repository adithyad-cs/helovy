"""Request schemas for E-14, E-15 and E-18 (docs/07 §3.3, §4; docs/09 §4).

Money and quantities must be JSON strings and are parsed by the ``calc`` module's parsers,
so the API, the snapshot and the pure module apply identical rules. Line errors point at
``/lines/{i}/{field}``. Lines in requests contain only inputs; position is the array order.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field, ValidationInfo, field_validator
from pydantic_core import PydanticCustomError

from app.core.schemas import StrictModel, clean_text, field_error
from app.modules.calc import engine
from app.modules.calc.engine import CalcError, DiscountType

DUE_DATE_MIN = date(2020, 1, 1)
DUE_DATE_MAX = date(2099, 12, 31)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _calc_error(error: CalcError) -> PydanticCustomError:
    return PydanticCustomError(error.code, error.message)


class CalcLine(StrictModel):
    """The numeric inputs of one line (E-14)."""

    quantity: Decimal
    unit_price: Decimal
    discount_type: DiscountType = "none"
    discount_value: Decimal | None = None

    @field_validator("quantity", mode="before")
    @classmethod
    def _quantity(cls, value: object) -> Decimal:
        try:
            return engine.parse_quantity(value)
        except CalcError as error:
            raise _calc_error(error) from None

    @field_validator("unit_price", mode="before")
    @classmethod
    def _unit_price(cls, value: object) -> Decimal:
        try:
            return engine.parse_unit_price(value)
        except CalcError as error:
            raise _calc_error(error) from None

    @field_validator("discount_value", mode="before")
    @classmethod
    def _discount_value(cls, value: object, info: ValidationInfo) -> Decimal | None:
        kind = info.data.get("discount_type")
        if kind is None:
            return None  # discount_type itself is invalid and already reported
        if kind == "none":
            if value is not None:
                raise field_error(
                    "invalid_choice", "Remove the discount value, or choose a discount type."
                )
            return None
        if value is None:
            noun = "percentage" if kind == "percent" else "amount"
            raise field_error("required", f"Enter the discount {noun}.")
        try:
            if kind == "percent":
                return engine.parse_percent(value)
            amount = engine.parse_amount_discount(value)
        except CalcError as error:
            raise _calc_error(error) from None
        quantity, unit_price = info.data.get("quantity"), info.data.get("unit_price")
        if quantity is not None and unit_price is not None:
            gross = engine.line_gross(quantity, unit_price)
            if amount > gross:
                raise PydanticCustomError(
                    "exceeds_gross",
                    "The discount cannot be more than the line amount (₹{gross}).",
                    {"gross": engine.money_str(gross)},
                )
        return amount

    def calc_input(self) -> engine.LineInput:
        return engine.LineInput(
            self.quantity, self.unit_price, self.discount_type, self.discount_value
        )


class DocumentLineIn(StrictModel):
    """A full draft line (E-15, E-18): description and unit, then the numeric inputs."""

    description: str | None
    quantity: Decimal
    unit: str | None = None
    unit_price: Decimal
    discount_type: DiscountType = "none"
    discount_value: Decimal | None = None

    _quantity = field_validator("quantity", mode="before")(CalcLine._quantity.__func__)  # type: ignore[attr-defined]
    _unit_price = field_validator("unit_price", mode="before")(CalcLine._unit_price.__func__)  # type: ignore[attr-defined]
    _discount_value = field_validator("discount_value", mode="before")(
        CalcLine._discount_value.__func__  # type: ignore[attr-defined]
    )

    @field_validator("description")
    @classmethod
    def _description(cls, value: str | None) -> str:
        if value is None:
            raise field_error("not_null", "Enter a description.")
        cleaned = clean_text(value, max_length=500, multiline=True, required=True)
        assert cleaned is not None  # noqa: S101 - required=True never returns None
        return cleaned

    @field_validator("unit")
    @classmethod
    def _unit(cls, value: str | None) -> str | None:
        return None if value is None else clean_text(value, max_length=20)

    def calc_input(self) -> engine.LineInput:
        return engine.LineInput(
            self.quantity, self.unit_price, self.discount_type, self.discount_value
        )


def _lines_count(value: object) -> object:
    if isinstance(value, list) and len(value) > engine.MAX_LINES:
        raise field_error("too_many_lines", f"Use at most {engine.MAX_LINES} lines.")
    return value


class CalculateRequest(StrictModel):
    lines: list[CalcLine]

    _count = field_validator("lines", mode="before")(lambda value: _lines_count(value))


def _due_date(value: str | None) -> date | None:
    if value is None:
        return None
    if not _DATE.match(value):
        raise field_error("invalid_format", "Use the format YYYY-MM-DD.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise field_error("invalid_format", "Enter a real calendar date.") from None
    if not DUE_DATE_MIN <= parsed <= DUE_DATE_MAX:
        raise field_error("out_of_range", "Choose a date between 2020 and 2099.")
    return parsed


class _DraftRules(StrictModel):
    @field_validator("reference", check_fields=False)
    @classmethod
    def _reference(cls, value: str | None) -> str | None:
        return None if value is None else clean_text(value, max_length=100)

    @field_validator("notes", "terms", check_fields=False)
    @classmethod
    def _long_text(cls, value: str | None) -> str | None:
        return None if value is None else clean_text(value, max_length=2000, multiline=True)

    @field_validator("customer_id", "template_id", check_fields=False)
    @classmethod
    def _required_reference(cls, value: str | None) -> str:
        if value is None:
            raise field_error("not_null", "This field can't be empty.")
        return value

    @field_validator("lines", mode="before", check_fields=False)
    @classmethod
    def _lines(cls, value: object) -> object:
        if value is None:
            raise field_error("not_null", "Send the full list of lines (it may be empty).")
        return _lines_count(value)

    def provided(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.model_fields_set}


class DocumentCreate(_DraftRules):
    doc_type: Literal["invoice"] = "invoice"
    customer_id: str | None
    template_id: str | None = "classic@1"
    reference: str | None = None
    due_date: date | None = None
    notes: str | None = None
    terms: str | None = None
    lines: list[DocumentLineIn] = Field(default_factory=list)

    _due = field_validator("due_date", mode="before")(lambda value: _due_date(value))


class DocumentPatch(_DraftRules):
    customer_id: str | None = None
    template_id: str | None = None
    reference: str | None = None
    due_date: date | None = None
    notes: str | None = None
    terms: str | None = None
    lines: list[DocumentLineIn] | None = None

    _due = field_validator("due_date", mode="before")(lambda value: _due_date(value))
