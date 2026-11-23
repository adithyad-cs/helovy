"""UT-FMT-01 (docs/11 §2.1): money, quantity, percent and date formatting (F-15, docs/09 §6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.rendering import formatting

FIXTURES = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "invoice_fixture.json").read_text("utf-8")
)


@pytest.mark.parametrize(("value", "expected"), sorted(FIXTURES["formatting"]["F-15"].items()))
def test_ut_fmt_01_money_f15(value: str, expected: str) -> None:
    assert formatting.money(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("0.00", "₹0.00"), ("100.00", "₹100.00"), ("1000.00", "₹1,000.00"), ("100000.00", "₹1,00,000.00"),
     ("10000000.00", "₹1,00,00,000.00"), ("999.99", "₹999.99")],
)  # fmt: skip
def test_money_indian_grouping(value: str, expected: str) -> None:
    assert formatting.money(value) == expected


def test_money_rejects_non_money_strings() -> None:
    for bad in ("1e3", "12.5", "abc", "1,000.00"):
        with pytest.raises(ValueError):
            formatting.money(bad)


@pytest.mark.parametrize(
    ("value", "expected"), [("2.500", "2.5"), ("3.000", "3"), ("1.005", "1.005"), ("10", "10")]
)
def test_ut_fmt_01_quantity(value: str, expected: str) -> None:
    assert formatting.quantity(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"), [("10.00", "10%"), ("12.50", "12.5%"), ("33.33", "33.33%")]
)
def test_percent(value: str, expected: str) -> None:
    assert formatting.percent(value) == expected


def test_discount_column() -> None:
    assert (
        formatting.discount_column(
            {"discount_type": "percent", "discount_value": "10.00", "discount": "200.00"}
        )
        == "10% (₹200.00)"
    )
    assert (
        formatting.discount_column(
            {"discount_type": "amount", "discount_value": "99.99", "discount": "99.99"}
        )
        == "₹99.99"
    )
    assert (
        formatting.discount_column(
            {"discount_type": "none", "discount_value": None, "discount": "0.00"}
        )
        == "—"
    )


def test_ut_fmt_01_dates_and_deduction() -> None:
    assert formatting.long_date("2026-11-25") == "25 Nov 2026"
    assert formatting.long_date("2027-03-01") == "01 Mar 2027"
    assert formatting.deduction("299.99") == "\u2212₹299.99"
    assert formatting.deduction("0.00") == "₹0.00"


def test_money_is_never_converted_to_float() -> None:
    source = (
        Path(__file__).resolve().parents[2] / "app" / "modules" / "rendering" / "formatting.py"
    ).read_text()
    assert "float(" not in source
