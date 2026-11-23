"""Template registry, worker pool and template-level content (docs/09 §11, §13; IT-PDF-05)."""

from __future__ import annotations

import re
import types
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.cli import main as cli_main
from app.modules.calc import engine
from app.modules.documents.snapshot import build_payload, canonical_sha256
from app.modules.rendering import constants, registry
from app.modules.rendering.pool import RenderError, RenderJob, RenderPool
from app.modules.rendering.renderer import TemplateIntegrityError, render_html

FORBIDDEN = ("Tax Invoice", "CGST", "SGST", "IGST", "HSN", "SAC", "certified", "compliant")


def sample_payload(*, final: bool, gstin: str | None = None, lines: int = 2) -> dict[str, Any]:
    document = types.SimpleNamespace(
        id="4e6a8c0d-2f3b-4c5e-9a7d-9f1b3d5f7a9c", doc_type="invoice", due_date=date(2026, 12, 10),
        reference="PO-4471", currency="INR", notes="Thank you <b>for</b> your business.", terms=None,
        template_id="classic@1",
    )  # fmt: skip
    business = types.SimpleNamespace(
        id="2c4e6a8b-0d1f-4a3c-9e5b-7d9f1b3d5e7a", legal_name="Lotus Lane Design Studio (Demo)",
        trade_name=None, address_line1="12 Example Road", address_line2=None, city="Bengaluru",
        state_code="29", postal_code="560038", country_code="IN", phone=None, email=None, gstin=gstin,
    )  # fmt: skip
    customer = types.SimpleNamespace(
        id="3d5f7b9c-1e2a-4b4d-8f6c-8e0a2c4e6f8b", display_name="Riverstone Consulting (Demo)",
        contact_name=None, email=None, phone=None, address_line1=None, address_line2=None, city="Pune",
        state_code="27", postal_code=None, country_code="IN", gstin=None,
    )  # fmt: skip
    rows = [
        types.SimpleNamespace(position=i + 1, description=f"Line {i + 1}", quantity=Decimal("2.5"), unit="hrs",
                              unit_price=Decimal("800.00"), discount_type="percent", discount_value=Decimal("10"))
        for i in range(lines)
    ]  # fmt: skip
    result = engine.calculate_document(
        [
            engine.LineInput(r.quantity, r.unit_price, r.discount_type, r.discount_value)
            for r in rows
        ]
    )
    return build_payload(
        document=document, business=business, business_state_name="Karnataka", customer=customer,
        customer_state_name="Maharashtra", lines=rows, result=result,
        number="INV/26-27/00001" if final else None, financial_year="26-27" if final else None,
        issue_date="2026-11-25" if final else None, finalized_at="2026-11-25T05:42:10Z" if final else None,
    )  # fmt: skip


def test_registered_hash_matches_files_and_cli(capsys: pytest.CaptureFixture[str]) -> None:
    entry = registry.get("classic@1")
    assert registry.template_hash(entry.directory) == entry.sha256
    assert registry.all_match()
    assert cli_main(["template-hash", "classic@1"]) == 0
    assert capsys.readouterr().out.strip() == entry.sha256
    assert cli_main(["template-hash", "fancy@9"]) == 2


def test_template_hash_follows_docs_09_section_11(tmp_path: Any) -> None:
    import hashlib

    (tmp_path / "b.css").write_bytes(b"b")
    (tmp_path / "a.html").write_bytes(b"a")
    expected = hashlib.sha256()
    for name, data in (("a.html", b"a"), ("b.css", b"b")):
        expected.update(f"{name}\0{hashlib.sha256(data).hexdigest()}\n".encode())
    assert registry.template_hash(tmp_path) == expected.hexdigest()


def test_preview_html_has_watermark_specimen_and_no_number() -> None:
    html = render_html("classic@1", sample_payload(final=False), preview=True)
    assert constants.WATERMARK_TEXT in html
    assert constants.SPECIMEN_TEXT == "SPECIMEN — demonstration document, not a tax invoice."
    assert constants.SPECIMEN_TEXT in html
    assert "Not yet issued" in html and "Assigned when finalised" in html
    assert not re.search(r"INV/\d{2}-\d{2}/\d+", html)
    assert "<b>for</b>" not in html and "&lt;b&gt;for&lt;/b&gt;" in html  # autoescaped


def test_final_html_has_title_number_specimen_and_no_watermark() -> None:
    html = render_html("classic@1", sample_payload(final=True), preview=False)
    assert ">Invoice<" in html
    assert "INV/26-27/00001" in html and "25 Nov 2026" in html
    assert constants.SPECIMEN_TEXT in html
    assert constants.WATERMARK_TEXT not in html
    for word in FORBIDDEN:
        assert word not in html
    assert "GST" not in html  # no GSTIN entered, so not even the label


def test_gstin_is_printed_only_as_a_label() -> None:
    html = render_html(
        "classic@1", sample_payload(final=True, gstin="29ABCDE1234F1Z5"), preview=False
    )
    assert "GSTIN: 29ABCDE1234F1Z5" in html
    assert re.findall(r"GST\w*", html) == ["GSTIN"]


def test_payload_money_is_strings_only() -> None:
    payload = sample_payload(final=True)

    def walk(value: Any) -> None:
        assert not isinstance(value, float)
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    assert payload["totals"]["grand_total"] == "3600.00"
    assert payload["labels"]["specimen_text"] == constants.SPECIMEN_TEXT


def test_template_integrity_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = registry.get("classic@1")
    monkeypatch.setitem(
        registry.REGISTRY,
        "classic@1",
        registry.RegisteredTemplate("classic@1", entry.directory, "0" * 64),
    )
    with pytest.raises(TemplateIntegrityError):
        render_html("classic@1", sample_payload(final=False), preview=True)


def test_pool_renders_and_checks_snapshot_hash() -> None:
    pool = RenderPool(1, 60)
    payload = sample_payload(final=True, lines=3)
    try:
        pdf = pool.render(
            RenderJob(
                "classic@1", payload, preview=False, expected_sha256=canonical_sha256(payload)
            )
        )
        assert pdf.startswith(b"%PDF-") and pdf.rstrip().endswith(b"%%EOF")
        with pytest.raises(RenderError) as raised:
            pool.render(RenderJob("classic@1", payload, preview=False, expected_sha256="0" * 64))
        assert raised.value.code == "snapshot_integrity"
    finally:
        pool.close()


def test_it_pdf_05_render_exceeding_the_timeout_is_killed() -> None:
    pool = RenderPool(1, 0.05)
    try:
        with pytest.raises(RenderError) as raised:
            pool.render(RenderJob("classic@1", sample_payload(final=False), preview=True))
        assert raised.value.code == "render_timeout"
        assert not pool._started  # the timed-out worker was killed and removed
    finally:
        pool.close()
