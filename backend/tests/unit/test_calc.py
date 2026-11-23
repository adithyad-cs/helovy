"""UT-CALC-01 to UT-CALC-09 (docs/11 §2.1), driven by tests/fixtures/invoice_fixture.json."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.modules.calc import engine
from app.modules.calc.engine import CalcError, LineInput, calculate_document, calculate_line

FIXTURES: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "invoice_fixture.json").read_text("utf-8")
)
LINES = FIXTURES["lines"]


def _line(raw: dict[str, Any]) -> LineInput:
    discount_type = raw["discount_type"]
    value = raw["discount_value"]
    parsed = None
    if discount_type == "percent":
        parsed = engine.parse_percent(value)
    elif discount_type == "amount":
        parsed = engine.parse_amount_discount(value)
    return LineInput(
        quantity=engine.parse_quantity(raw["quantity"]),
        unit_price=engine.parse_unit_price(raw["unit_price"]),
        discount_type=discount_type,
        discount_value=parsed,
    )


def _strings(result: engine.LineResult) -> dict[str, str]:
    return {
        "gross": engine.money_str(result.gross),
        "discount": engine.money_str(result.discount),
        "line_total": engine.money_str(result.line_total),
    }


@pytest.mark.parametrize(
    ("test_id", "fixture"),
    [
        ("UT-CALC-01", "F-01"),
        ("UT-CALC-02", "F-02"),
        ("UT-CALC-04", "F-04"),
        ("UT-CALC-04", "F-13"),
        ("UT-CALC-05", "F-05"),
        ("UT-CALC-05", "F-07"),
        ("UT-CALC-05", "F-14"),
        ("F-06", "F-06"),
        ("F-08", "F-08"),
    ],
)
def test_fixture_lines(test_id: str, fixture: str) -> None:
    case = LINES[fixture]
    assert _strings(calculate_line(_line(case["input"]))) == case["expected"], test_id


def test_ut_calc_03_document_totals() -> None:
    case = FIXTURES["documents"]["F-03"]
    result = calculate_document([_line(LINES[name]["input"]) for name in case["lines"]])
    totals = {
        "gross_total": engine.money_str(result.totals.gross_total),
        "discount_total": engine.money_str(result.totals.discount_total),
        "grand_total": engine.money_str(result.totals.grand_total),
    }
    assert totals == case["expected"]


def test_ut_calc_04_half_up_not_binary_float() -> None:
    # Binary floating point would give 1.00 for 1.005 x 1.00 and half-even 0.12 for 0.125.
    assert round(1.005 * 1.00, 2) == 1.0  # the float trap the calc module avoids
    assert engine.money_str(engine.line_gross(Decimal("1.005"), Decimal("1.00"))) == "1.01"
    assert engine.money_str(engine.line_gross(Decimal("0.125"), Decimal("1.00"))) == "0.13"


def test_ut_calc_06_amount_discount_above_gross() -> None:
    case = FIXTURES["errors"]["F-09"]
    with pytest.raises(CalcError) as raised:
        calculate_line(_line(case["input"]))
    assert raised.value.code == "exceeds_gross"
    assert "₹1000.00" in raised.value.message


@pytest.mark.parametrize("key", ["F-10a", "F-10b", "F-10c", "F-10d"])
def test_ut_calc_07_quantity_limits(key: str) -> None:
    case = FIXTURES["errors"][key]
    with pytest.raises(CalcError) as raised:
        engine.parse_quantity(case["value"])
    assert raised.value.code == case["code"]


def test_ut_calc_07_total_too_large() -> None:
    with pytest.raises(CalcError) as raised:
        calculate_document([_line(FIXTURES["errors"]["F-11"]["input"])])
    assert raised.value.code == "total_too_large"


def test_ut_calc_07_too_many_lines() -> None:
    line = _line(LINES["F-08"]["input"])
    with pytest.raises(CalcError) as raised:
        calculate_document([line] * FIXTURES["errors"]["F-12"]["line_count"])
    assert raised.value.code == "too_many_lines"
    assert len(calculate_document([line] * 200).lines) == 200


@pytest.mark.parametrize(
    ("parser", "value", "code"),
    [
        (engine.parse_quantity, "1e3", "invalid_decimal"),
        (engine.parse_quantity, "-1", "invalid_decimal"),
        (engine.parse_quantity, " 1", "invalid_decimal"),
        (engine.parse_quantity, "1,000", "invalid_decimal"),
        (engine.parse_quantity, "007", "invalid_decimal"),
        (engine.parse_quantity, "1.", "invalid_decimal"),
        (engine.parse_quantity, ".5", "invalid_decimal"),
        (engine.parse_quantity, "", "invalid_decimal"),
        (engine.parse_quantity, "12345678", "out_of_range"),
        (engine.parse_quantity, None, "must_be_string"),
        (engine.parse_unit_price, "10000000.01", "out_of_range"),
        (engine.parse_unit_price, "1.005", "too_many_decimals"),
        (engine.parse_unit_price, 800, "must_be_string"),
        (engine.parse_percent, "0", "out_of_range"),
        (engine.parse_percent, "100.01", "out_of_range"),
        (engine.parse_percent, "12.555", "too_many_decimals"),
        (engine.parse_amount_discount, "0.00", "out_of_range"),
    ],
)
def test_ut_calc_07_field_codes(parser: Any, value: object, code: str) -> None:
    with pytest.raises(CalcError) as raised:
        parser(value)
    assert raised.value.code == code


@pytest.mark.parametrize(
    ("parser", "value", "expected"),
    [
        (engine.parse_quantity, "1000000", "1000000.000"),
        (engine.parse_quantity, "0.001", "0.001"),
        (engine.parse_unit_price, "0", "0.00"),
        (engine.parse_unit_price, "10000000.00", "10000000.00"),
        (engine.parse_percent, "100", "100.00"),
    ],
)
def test_limits_are_inclusive_where_documented(parser: Any, value: str, expected: str) -> None:
    parsed = parser(value)
    shown = (
        engine.quantity_str(parsed) if parser is engine.parse_quantity else engine.money_str(parsed)
    )
    assert shown == expected


quantities = st.decimals(min_value=Decimal("0.001"), max_value=Decimal("1000"), places=3)
prices = st.decimals(min_value=Decimal("0.00"), max_value=Decimal("100000"), places=2)


@st.composite
def line_inputs(draw: st.DrawFn) -> LineInput:
    quantity, price = draw(quantities), draw(prices)
    kind = draw(st.sampled_from(engine.DISCOUNT_TYPES))
    value: Decimal | None = None
    if kind == "percent":
        value = draw(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("100"), places=2))
    elif kind == "amount":
        gross = engine.line_gross(quantity, price)
        if gross < Decimal("0.01"):
            kind = "none"
        else:
            value = draw(st.decimals(min_value=Decimal("0.01"), max_value=gross, places=2))
    return LineInput(quantity, price, kind, value)


@settings(max_examples=300, deadline=None)
@given(st.lists(line_inputs(), min_size=0, max_size=12))
def test_ut_calc_08_properties(lines: list[LineInput]) -> None:
    result = calculate_document(lines)
    for line in result.lines:
        assert Decimal("0.00") <= line.discount <= line.gross
        assert line.line_total == line.gross - line.discount
        for value in (line.gross, line.discount, line.line_total):
            assert value.as_tuple().exponent == -2
    totals = result.totals
    assert totals.gross_total == sum((r.gross for r in result.lines), Decimal("0.00"))
    assert totals.discount_total == sum((r.discount for r in result.lines), Decimal("0.00"))
    assert totals.grand_total == totals.gross_total - totals.discount_total
    for value in (totals.gross_total, totals.discount_total, totals.grand_total):
        assert format(value, "f").count(".") == 1 and len(format(value, "f").split(".")[1]) == 2


def test_ut_calc_09_no_float_in_results() -> None:
    result = calculate_document([_line(LINES["F-01"]["input"]), _line(LINES["F-02"]["input"])])
    values = [v for line in result.lines for v in (line.gross, line.discount, line.line_total)]
    values += [result.totals.gross_total, result.totals.discount_total, result.totals.grand_total]
    assert all(type(value) is Decimal for value in values)
    with pytest.raises(CalcError) as raised:
        engine.parse_unit_price(800.0)
    assert raised.value.code == "must_be_string"


def test_calc_module_never_calls_float() -> None:
    # docs/09 §2.2: a lint check backs the review rule in the calc and documents modules.
    app_dir = Path(__file__).resolve().parents[2] / "app" / "modules"
    for module in ("calc", "documents"):
        for source in (app_dir / module).glob("*.py"):
            assert "float(" not in source.read_text("utf-8"), source


def test_calc_version() -> None:
    assert engine.CALC_VERSION == "calc-1.0.0"
