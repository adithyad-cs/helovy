"""The ``snapshot-1`` payload, its canonical serialisation and hash (docs/09 §10).

The same payload shape serves the final PDF (from the frozen snapshot) and the draft preview
(built from the current draft, with ``number``, ``financial_year``, ``issue_date`` and
``finalized_at`` set to null). All keys are always present; money and quantities are
strings; the only JSON numbers are integer positions. Pure functions: safe to import in a
render worker.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any, Protocol

from app.modules.calc import engine
from app.modules.rendering.constants import DOCUMENT_TITLE, SPECIMEN_TEXT

SCHEMA_VERSION = "snapshot-1"
TAX_RULE_SET = "none"


class _Address(Protocol):
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state_code: str | None
    postal_code: str | None
    country_code: str


class _Line(Protocol):
    position: int
    description: str
    quantity: Any
    unit: str | None
    unit_price: Any
    discount_type: str
    discount_value: Any


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    """UTF-8 of sorted-key JSON without insignificant whitespace (docs/09 §10.2)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def canonical_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _address(party: _Address, state_name: str | None) -> dict[str, Any]:
    return {
        "line1": party.address_line1,
        "line2": party.address_line2,
        "city": party.city,
        "state_code": party.state_code,
        "state_name": state_name,
        "postal_code": party.postal_code,
        "country_code": party.country_code,
    }


def build_payload(
    *,
    document: Any,
    business: Any,
    business_state_name: str | None,
    customer: Any,
    customer_state_name: str | None,
    lines: Sequence[_Line],
    result: engine.DocumentResult,
    number: str | None,
    financial_year: str | None,
    issue_date: str | None,
    finalized_at: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "calc_version": engine.CALC_VERSION,
        "tax_rule_set": TAX_RULE_SET,
        "document": {
            "id": str(document.id),
            "doc_type": document.doc_type,
            "title": DOCUMENT_TITLE,
            "number": number,
            "financial_year": financial_year,
            "issue_date": issue_date,
            "due_date": document.due_date.isoformat() if document.due_date else None,
            "reference": document.reference,
            "currency": document.currency,
            "notes": document.notes,
            "terms": document.terms,
            "template_id": document.template_id,
            "finalized_at": finalized_at,
        },
        "seller": {
            "business_id": str(business.id),
            "legal_name": business.legal_name,
            "trade_name": business.trade_name,
            "address": _address(business, business_state_name),
            "phone": business.phone,
            "email": business.email,
            "gstin": business.gstin,
        },
        "buyer": {
            "customer_id": str(customer.id),
            "display_name": customer.display_name,
            "contact_name": customer.contact_name,
            "email": customer.email,
            "phone": customer.phone,
            "address": _address(customer, customer_state_name),
            "gstin": customer.gstin,
        },
        "lines": [
            {
                "position": line.position,
                "description": line.description,
                "quantity": engine.quantity_str(line.quantity),
                "unit": line.unit,
                "unit_price": engine.money_str(line.unit_price),
                "discount_type": line.discount_type,
                "discount_value": (
                    engine.money_str(line.discount_value)
                    if line.discount_value is not None
                    else None
                ),
                "gross": engine.money_str(amounts.gross),
                "discount": engine.money_str(amounts.discount),
                "line_total": engine.money_str(amounts.line_total),
            }
            for line, amounts in zip(lines, result.lines, strict=True)
        ],
        "totals": {
            "gross_total": engine.money_str(result.totals.gross_total),
            "discount_total": engine.money_str(result.totals.discount_total),
            "grand_total": engine.money_str(result.totals.grand_total),
        },
        "labels": {"specimen_text": SPECIMEN_TEXT},
    }
