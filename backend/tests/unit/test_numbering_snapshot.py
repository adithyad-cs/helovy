"""UT-NUM-01, UT-NUM-02, UT-SNAP-01, UT-SNAP-03 (docs/11 §2.1)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime

import pytest

from app.modules.documents import numbering
from app.modules.documents.snapshot import canonical_bytes, canonical_sha256
from app.modules.rendering.constants import SPECIMEN_TEXT
from tests.unit.test_rendering import sample_payload


@pytest.mark.parametrize(
    ("day", "label"),
    [(date(2026, 11, 25), "26-27"), (date(2027, 3, 31), "26-27"), (date(2027, 4, 1), "27-28"),
     (date(2099, 4, 1), "99-00"), (date(2026, 4, 1), "26-27"), (date(2026, 3, 31), "25-26")],
)  # fmt: skip
def test_ut_num_01_financial_year(day: date, label: str) -> None:
    assert numbering.financial_year(day) == label


def test_ut_num_01_asia_kolkata_boundary() -> None:
    before = datetime(2027, 3, 31, 18, 29, 59, tzinfo=UTC)  # 23:59:59 IST on 31 March
    after = datetime(2027, 3, 31, 18, 30, 0, tzinfo=UTC)  # 00:00:00 IST on 1 April
    assert numbering.financial_year(numbering.issue_date_for(before)) == "26-27"
    assert numbering.financial_year(numbering.issue_date_for(after)) == "27-28"
    assert numbering.issue_date_for(datetime(2026, 11, 24, 19, 0, tzinfo=UTC)) == date(2026, 11, 25)
    with pytest.raises(ValueError):
        numbering.issue_date_for(datetime(2026, 11, 25))  # naive: refused


@pytest.mark.parametrize(
    ("sequence", "number"),
    [(1, "INV/26-27/00001"), (99999, "INV/26-27/99999"), (100000, "INV/26-27/100000"),
     (999999, "INV/26-27/999999")],
)  # fmt: skip
def test_ut_num_02_formatting(sequence: int, number: str) -> None:
    assert numbering.format_number("INV", "26-27", sequence) == number
    assert len(number) <= 16


@pytest.mark.parametrize("sequence", [0, 1_000_000, -1])
def test_ut_num_02_exhausted(sequence: int) -> None:
    with pytest.raises(numbering.NumberSeriesExhaustedError):
        numbering.format_number("INV", "26-27", sequence)


def test_ut_snap_01_canonical_json_is_order_independent_and_compact() -> None:
    payload = sample_payload(final=True)
    reordered = json.loads(json.dumps(payload))
    reordered = {key: reordered[key] for key in reversed(list(reordered))}
    reordered["document"] = {
        k: reordered["document"][k] for k in reversed(list(reordered["document"]))
    }
    assert canonical_bytes(payload) == canonical_bytes(reordered)
    assert canonical_sha256(payload) == canonical_sha256(reordered)
    raw = canonical_bytes(payload)
    documented = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert raw == documented.encode("utf-8")  # docs/09 §10.2, exactly
    assert b"\n" not in raw and b'": ' not in raw
    assert canonical_sha256(payload) == hashlib.sha256(raw).hexdigest()
    assert "—".encode() in raw  # ensure_ascii=False: UTF-8, not \\u escapes


def test_ut_snap_03_snapshot_content() -> None:
    payload = sample_payload(final=True)
    assert set(payload) == {"schema_version", "calc_version", "tax_rule_set", "document", "seller",
                            "buyer", "lines", "totals", "labels"}  # fmt: skip
    assert payload["schema_version"] == "snapshot-1" and payload["calc_version"] == "calc-1.0.0"
    assert payload["labels"]["specimen_text"] == SPECIMEN_TEXT
    assert payload["seller"]["legal_name"] and payload["buyer"]["display_name"]
    assert payload["document"]["title"] == "Invoice"

    def money_values(value: object) -> list[object]:
        if isinstance(value, dict):
            return [v for item in value.values() for v in money_values(item)]
        if isinstance(value, list):
            return [v for item in value for v in money_values(item)]
        return [value]

    for value in money_values(payload):
        assert not isinstance(value, float)
    for line in payload["lines"]:
        assert isinstance(line["position"], int)
        for key in ("quantity", "unit_price", "gross", "discount", "line_total"):
            assert isinstance(line[key], str)
