# 09 — Financial and Document Rules

| | |
| --- | --- |
| Document | Calculation, validation, numbering, finalisation, snapshot and PDF rules · version 1.1 · 23 November 2026 |
| Status | Normative for P0-Lite. 04, 06 and 07 must agree with this document |
| Marker | **[CA]** marks a rule that a chartered accountant must validate before production use (Q-03, Q-16, Q-17, Q-18). P0-Lite uses it as a documented working policy |

## 1. Scope

P0-Lite produces **no-tax demonstration invoices**. This document defines exactly how amounts are calculated, validated, formatted, numbered, frozen and rendered. Tax and statutory rules are listed in §14 as deferred. None of them is implemented in P0-Lite.

## 2. Decimal approach

1. All money and quantity arithmetic uses Python `decimal.Decimal` inside a local context with precision 28 and the default traps on (`InvalidOperation`, `DivisionByZero`, `Overflow`). The largest intermediate value is 1,000,000 × 10,000,000.00 = 10¹³ with 5 decimal places, which needs 18 significant digits.
2. Values enter the server only as JSON strings, are checked against the patterns in §4, and are converted with `Decimal(string)`. `float()` is never called on money or quantities; a code-review rule and a lint check (`grep -n "float("` in the `calc` and `documents` modules) back this up.
3. PostgreSQL stores `numeric(p,s)` (06 §5). psycopg 3 returns `numeric` columns as `Decimal`.
4. Output strings are `format(value.quantize(q), 'f')`: money and percent to `0.01`, quantity to `0.001`.
5. The browser never computes authoritative amounts. It displays strings returned by the server (04 §4).

## 3. Calculation algorithm (`calc-1.0.0`)

Definitions: `round2(x) = x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`. This is the documented policy, subject to professional validation **[CA]** (A-11).

For each line *i*, with quantity `q`, unit price `p`, discount type `t` and discount value `d`:

| Step | Formula | Notes |
| --- | --- | --- |
| 1. Gross | `gross = round2(q × p)` | `q × p` is exact before rounding |
| 2. Discount | `t = none` → `0.00`; `t = percent` → `round2(gross × d / 100)`; `t = amount` → `d` | Percent: 0 < `d` ≤ 100. Amount: 0 < `d` ≤ `gross`, otherwise `exceeds_gross` |
| 3. Line total | `line_total = gross − discount` | Always ≥ 0.00 |

For the document:

| Step | Formula |
| --- | --- |
| 4. Gross total | `gross_total = Σ gross` |
| 5. Discount total | `discount_total = Σ discount` |
| 6. Grand total | `grand_total = Σ line_total` (always equal to `gross_total − discount_total`) |
| 7. Limit | `grand_total ≤ 9,999,999,999,999.99`, otherwise `total_too_large` |

Rules:

- **Per-line rounding:** each line is rounded, then rounded values are summed. Totals are never re-rounded. **[CA]**
- **No rupee round-off:** totals keep paise (A-10, Q-17). **[CA]**
- **No tax:** there are no tax lines and no tax totals (§5).
- **Zero lines:** free items (`unit_price = 0.00`) and 100 % discounts are allowed on lines. A document whose grand total is 0.00 cannot be finalised (`zero_total`, A-12).
- **Versioning:** the function set is versioned `calc-1.0.0`. Any rule change creates a new version; existing snapshots keep the version recorded in them and are never recalculated (§12).

## 4. Validation rules and limits

The server always validates; the client mirrors these rules for instant feedback only. The field error codes are listed in 07 §1.5.

### 4.1 Numeric inputs (JSON strings only)

| Field | Pattern (regular expression) | Range | Errors |
| --- | --- | --- | --- |
| `quantity` | `^(0\|[1-9][0-9]{0,6})(\.[0-9]{1,3})?$` | > 0 and ≤ 1,000,000 | `must_be_string`, `invalid_decimal`, `too_many_decimals`, `out_of_range` |
| `unit_price` | `^(0\|[1-9][0-9]{0,7})(\.[0-9]{1,2})?$` | ≥ 0.00 and ≤ 10,000,000.00 | same |
| `discount_value` (percent) | `^(0\|[1-9][0-9]{0,2})(\.[0-9]{1,2})?$` | > 0 and ≤ 100 | same |
| `discount_value` (amount) | Same as `unit_price` | > 0.00 and ≤ line gross | same, plus `exceeds_gross` |
| `discount_value` with `discount_type = none` | Must be absent or `null` | — | `invalid_choice` |

`too_many_decimals` is used when the value is a plain decimal that differs from the pattern only in its number of decimal places. Otherwise the error is `invalid_decimal`.

### 4.2 Text inputs

- **Normalisation:** trim leading and trailing whitespace; convert CRLF to LF. An empty string becomes `null` for optional fields and gives `required` for required ones.
- **Characters:** reject U+0000 everywhere. Reject other C0 control characters, except TAB and LF in multi-line fields. Single-line fields reject LF.
- **Length:** counted in Unicode code points, which matches PostgreSQL `char_length`.

| Field | Required | Max length | Lines | Extra rule |
| --- | --- | --- | --- | --- |
| Business `legal_name` | Yes | 200 | Single | |
| Business `trade_name` | No | 200 | Single | |
| `address_line1` | Business: yes. Customer: no | 200 | Single | |
| `address_line2` | No | 200 | Single | |
| `city` | Business: yes. Customer: no | 100 | Single | |
| `state_code` | Business: yes. Customer: no | 2 | — | Must be a code in §4.4 |
| `postal_code` | Business: yes. Customer: no | 6 | — | `^[1-9][0-9]{5}$` |
| `phone` | No | 20 | — | `^[0-9+() -]{6,20}$` |
| `email` | No (user login: yes) | 254 | — | `^[^@\s]+@[^@\s]+\.[^@\s]+$`; login emails are lower-cased |
| `gstin` | No | 15 | — | `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$`; first two digits equal `state_code` when both are present (`state_mismatch`). The checksum is not validated in P0-Lite (P1-05) |
| Customer `display_name` | Yes | 200 | Single | |
| Customer `contact_name` | No | 120 | Single | |
| Document `reference` | No | 100 | Single | |
| Document `notes`, `terms` | No | 2000 each | Multi | |
| Line `description` | Yes | 500 | Multi | |
| Line `unit` | No | 20 | Single | |
| Document `due_date` | No | — | — | Valid date between 2020-01-01 and 2099-12-31; at finalisation, must be on or after the issue date |

### 4.3 Structural limits

| Limit | Value | Error |
| --- | --- | --- |
| Lines per draft | 0–200 (at least 1 to preview or finalise) | `too_many_lines`, `no_lines` |
| Grand total | ≤ ₹9,999,999,999,999.99 | `total_too_large` |
| Request body | 256 KiB | 413 `payload_too_large` |
| Customer search `q` | 1–100 characters | `too_long` |
| Document search `q` | 1–50 characters | `too_long` |

### 4.4 State codes (GST state codes; verify against the current CBIC list before production, V-17)

| Code | State or union territory | Code | State or union territory |
| --- | --- | --- | --- |
| 01 | Jammu and Kashmir | 20 | Jharkhand |
| 02 | Himachal Pradesh | 21 | Odisha |
| 03 | Punjab | 22 | Chhattisgarh |
| 04 | Chandigarh | 23 | Madhya Pradesh |
| 05 | Uttarakhand | 24 | Gujarat |
| 06 | Haryana | 26 | Dadra and Nagar Haveli and Daman and Diu |
| 07 | Delhi | 27 | Maharashtra |
| 08 | Rajasthan | 29 | Karnataka |
| 09 | Uttar Pradesh | 30 | Goa |
| 10 | Bihar | 31 | Lakshadweep |
| 11 | Sikkim | 32 | Kerala |
| 12 | Arunachal Pradesh | 33 | Tamil Nadu |
| 13 | Nagaland | 34 | Puducherry |
| 14 | Manipur | 35 | Andaman and Nicobar Islands |
| 15 | Mizoram | 36 | Telangana |
| 16 | Tripura | 37 | Andhra Pradesh |
| 17 | Meghalaya | 38 | Ladakh |
| 18 | Assam | | |
| 19 | West Bengal | | |

Codes 25 and 28 are legacy codes and 97 and 99 are special codes. None of them is offered for addresses in P0-Lite.

## 5. Tax-disabled P0-Lite behaviour

- `documents.tax_mode = 'no_tax'` and `document_snapshots.tax_rule_set = 'none'` are the only values allowed (06).
- No tax rate, taxable value, CGST, SGST, IGST, cess, place of supply or HSN/SAC appears in the API, the UI or the PDFs.
- The document title is **"Invoice"**, never "Tax Invoice" or "Bill of Supply".
- A GSTIN, if entered, is printed only as a business detail ("GSTIN: …"). It triggers no tax logic and implies no compliance.
- Every PDF carries the SPECIMEN statement (§13).

## 6. Amount and value formatting

The server formats for PDFs (Jinja filters, tested by UT-FMT-01). The browser formats for screens (a string-based formatter, checked manually in FE-04). Both must produce the same results:

| Value | Rule | Examples |
| --- | --- | --- |
| Money | `₹` + Indian digit grouping (last 3 digits, then groups of 2) + `.` + 2 decimals | `2700.00` → ₹2,700.00 · `123456.78` → ₹1,23,456.78 · `0.50` → ₹0.50 · `9999999999999.99` → ₹99,99,99,99,99,999.99 |
| Quantity | Trailing zeros after the decimal point removed | `2.500` → 2.5 · `3.000` → 3 · `1.005` → 1.005 |
| Percent | Trailing zeros removed, then `%` | `10.00` → 10% · `12.50` → 12.5% |
| Discount column | Percent → `10% (₹200.00)`; amount → `₹99.99`; none → `—` | |
| Dates | `DD Mon YYYY` with English month abbreviations | `2026-11-25` → 25 Nov 2026 |
| Number | As allocated | INV/26-27/00001 |
| Amount in words (S-05 only) | Indian system: "Rupees … and … Paise Only"; tens hyphenated | `2700.00` → Rupees Two Thousand Seven Hundred Only · `123456.78` → Rupees One Lakh Twenty-Three Thousand Four Hundred Fifty-Six and Seventy-Eight Paise Only · `10000000.00` → Rupees One Crore Only · `0.50` → Rupees Zero and Fifty Paise Only |

Money strings are never converted to binary floating-point numbers for formatting.

## 7. Invoice numbering and financial year

| Rule | Definition |
| --- | --- |
| Financial year | For issue date `d`: `start = d.year` if `d.month >= 4`, else `d.year − 1`. The label is `f"{start % 100:02d}-{(start + 1) % 100:02d}"` |
| Issue date | The Asia/Kolkata calendar date of the database `now()` taken inside the finalisation transaction. It cannot be chosen or backdated (A-08) |
| Format | `INV/{fy}/{seq:05d}`, formatted in Python, for example `INV/26-27/00001`. At most 16 characters, using letters, digits, `/` and `-` only (matching the 16-character, `-` and `/` convention of CGST Rule 46(b), kept for future compatibility; verify) **[CA]** |
| Scope | One series per business, per document type and per financial year. A new year starts again at 00001 **[CA]** |
| Width | 5 digits, growing to 6 after 99,999 (`INV/26-27/100000`, 16 characters). Above 999,999 the API returns 409 `number_series_exhausted` |
| Gaps | None from failures: allocation rolls back with the transaction. Deleted drafts never had a number |
| Uniqueness | `documents_number_uq` and `documents_series_seq_uq` (06 §6) |
| Format approval | The working assumption is A-09; Heloavy and a CA confirm it (Q-16) |

Examples:

- `2026-11-25` → `26-27`; `2027-03-31` → `26-27`; `2027-04-01` → `27-28`; `2099-04-01` → `99-00`.
- Time-zone boundary:
  - finalised at `2027-03-31T18:29:59Z` (23:59:59 IST) → `26-27`;
  - finalised at `2027-03-31T18:30:00Z` (00:00:00 IST on 1 April) → `27-28`.

## 8. Finalisation transaction (normative)

**Step 0 (before the transaction):**

- Session valid; CSRF token and `Origin` valid.
- `Idempotency-Key` present (400 `idempotency_key_missing`) and well formed (400 `malformed_request`).
- `If-Match` present (428).
- Fingerprint = SHA-256 hex of the UTF-8 string `"POST\n/api/v1/documents/{document_id}/finalize\n{If-Match value}"`.

| Step | Action | Failure → response (the transaction rolls back) |
| --- | --- | --- |
| 1 | `BEGIN`; `SET LOCAL lock_timeout = '5s'` (READ COMMITTED) | — |
| 2 | `INSERT INTO idempotency_keys (org_id, scope='document.finalize', idem_key, request_fingerprint, status='in_progress', user_id, expires_at=now()+24h) ON CONFLICT DO NOTHING`. On conflict, read the row: a different fingerprint → 422 `idempotency_key_mismatch`; a completed row → roll back and **replay** the stored status and body with `Idempotent-Replayed: true` | Lock timeout → 409 `idempotency_in_progress` |
| 3 | `SELECT … FROM documents WHERE id = :id AND org_id = :org FOR UPDATE`. Then status must be `draft` and `version` must equal `If-Match` | Missing → 404; not a draft → 409 `document_not_draft`; stale → 412 `version_mismatch`; lock timeout → 503 |
| 4 | `SELECT now()` → `finalized_at`; `issue_date` = its Asia/Kolkata date; `fy` per §7 | — |
| 5 | Validate the preconditions: 1–200 lines, all valid (§4); grand total > 0.00 and within the limit; `due_date` (if set) ≥ `issue_date`; template active | 422 `finalization_blocked` with `errors[]` |
| 6 | Recalculate every line and total from the stored inputs with `calc-1.0.0` (§3) | — |
| 7 | Allocate the number: series upsert, then `UPDATE … SET next_seq = next_seq + 1 … RETURNING id, prefix, next_seq - 1` (06 §6); format in Python | Check violation or more than 16 characters → 409 `number_series_exhausted`; lock timeout → 503 |
| 8 | Build the snapshot payload (§10), canonicalise, compute SHA-256, `INSERT INTO document_snapshots` | — |
| 9 | `UPDATE documents SET status='finalized', number_series_id, sequence_no, document_number, issue_date, finalized_at, finalized_by, version = version + 1, updated_at = now()` | — |
| 10 | `INSERT INTO document_artifacts (kind='final_pdf', status='pending', attempts=0, template_id)` | — |
| 11 | `INSERT INTO audit_events ('document.finalized', subject = document, details = {number, snapshot_sha256})` | — |
| 12 | `UPDATE idempotency_keys SET status='completed', response_status=200, response_body=<document JSON>, resource_id=:id` | — |
| 13 | `COMMIT`; respond 200 (`pdf.status = "pending"`); schedule the background render (§11) | Commit failure → 503; nothing persisted |

Lock order is always idempotency record → document → number series (P1 adds the usage counter last). No other code path locks these rows in a different order.

## 9. Draft versus finalised states

| Aspect | Draft | Finalised |
| --- | --- | --- |
| Stored | Header fields and line **inputs** only | The snapshot, frozen; the document row and lines are locked by triggers |
| Amounts | Computed on every read and on E-14 (never stored) | Taken from the snapshot; never recomputed |
| Customer and business details | Live references; edits show immediately | Frozen copies in the snapshot |
| Number, issue date | `NULL` | Set once |
| Editable | Yes (`If-Match`) | No (409; triggers reject) |
| Deletable | Yes | No |
| PDF | Preview only (watermarked, not stored) | Final PDF stored with SHA-256 |
| ETag `version` | Increments on each save | Incremented once at finalisation, then fixed |
| Retention and deletion | The owner may delete a draft | Immutable while retained. How long finalised documents are retained, and how they are deleted, follows the Heloavy-approved policy and the applicable legal requirements (Q-18, 12 §16); retention-based deletion is not part of P0-Lite |

## 10. Immutable snapshots (`snapshot-1`)

### 10.1 Payload

All keys are always present (the key set is fixed); absent values are `null`.

```json
{
  "schema_version": "snapshot-1",
  "calc_version": "calc-1.0.0",
  "tax_rule_set": "none",
  "document": {
    "id": "4e6a8c0d-2f3b-4c5e-9a7d-9f1b3d5f7a9c", "doc_type": "invoice", "title": "Invoice",
    "number": "INV/26-27/00001", "financial_year": "26-27",
    "issue_date": "2026-11-25", "due_date": "2026-12-10", "reference": "PO-4471",
    "currency": "INR", "notes": "Thank you for your business.",
    "terms": "Payment within 15 days of the invoice date.",
    "template_id": "classic@1", "finalized_at": "2026-11-25T05:42:10Z"
  },
  "seller": {
    "business_id": "2c4e6a8b-0d1f-4a3c-9e5b-7d9f1b3d5e7a",
    "legal_name": "Lotus Lane Design Studio (Demo)", "trade_name": null,
    "address": { "line1": "12 Example Road", "line2": "Indiranagar", "city": "Bengaluru",
                 "state_code": "29", "state_name": "Karnataka", "postal_code": "560038", "country_code": "IN" },
    "phone": "+91 80 0000 0000", "email": "accounts@demo.invalid", "gstin": null
  },
  "buyer": {
    "customer_id": "3d5f7b9c-1e2a-4b4d-8f6c-8e0a2c4e6f8b",
    "display_name": "Riverstone Consulting (Demo)", "contact_name": "A. Kumar",
    "email": "ap@riverstone.invalid", "phone": null,
    "address": { "line1": "4th Floor, Sample Towers", "line2": null, "city": "Pune",
                 "state_code": "27", "state_name": "Maharashtra", "postal_code": "411001", "country_code": "IN" },
    "gstin": null
  },
  "lines": [
    { "position": 1, "description": "Brand identity consultation", "quantity": "2.500", "unit": "hrs",
      "unit_price": "800.00", "discount_type": "percent", "discount_value": "10.00",
      "gross": "2000.00", "discount": "200.00", "line_total": "1800.00" },
    { "position": 2, "description": "Website support hours", "quantity": "3.000", "unit": "hrs",
      "unit_price": "333.33", "discount_type": "amount", "discount_value": "99.99",
      "gross": "999.99", "discount": "99.99", "line_total": "900.00" }
  ],
  "totals": { "gross_total": "2999.99", "discount_total": "299.99", "grand_total": "2700.00" },
  "labels": { "specimen_text": "SPECIMEN — demonstration document, not a tax invoice." }
}
```

The generated columns read `payload #>> '{buyer,display_name}'` and `payload #>> '{totals,grand_total}'` (06 §3.11). These paths must not change within `snapshot-1`.

### 10.2 Canonical serialisation and hash

1. UTF-8 bytes produced by `json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
2. Object keys are sorted by code point; all keys are ASCII.
3. There is no insignificant whitespace.
4. Money and quantities are strings; the only JSON numbers are integers (`position`). There are no floats and no exponents.
5. `canonical_sha256` = lowercase hex SHA-256 of those bytes.
6. **Round-trip check:** reading `payload` back from JSONB and re-serialising it with the same function must give the same hash (UT-SNAP-02). JSONB keeps strings and integers exactly. Validation (§4.2) rejects U+0000, which JSONB cannot store.
7. This follows the spirit of RFC 8785 (JSON Canonicalization Scheme). It is equivalent for this payload (ASCII keys, no floats), but no JCS compliance is claimed.

### 10.3 Use

- The final PDF is rendered **only** from the snapshot payload. Before rendering, the worker re-computes the hash and refuses to render on a mismatch (`snapshot_integrity`).
- The API's finalised document representation (07 §3.3) is built from the snapshot.

## 11. PDF file integrity

| Item | Rule |
| --- | --- |
| File hash | SHA-256 of the exact stored bytes, recorded in `stored_files.sha256` and checked on every download (E-22). A mismatch returns 500 `integrity_check_failed` and the file is not served |
| Transport | `Content-Digest: sha-256=:<base64>:` on downloads; the details page shows the hex hash so a tester can compare it with `sha256sum` (DC-14) |
| Storage | Private bucket; key `orgs/{org_id}/documents/{document_id}/final-{artifact_id}.pdf`; versioning on in the cloud |
| Template hash | SHA-256 over the template directory. Files are sorted by relative POSIX path; for each file, the hash is fed `path` + `\0` + hex SHA-256 of the file bytes + `\n`. The expected value lives in `rendering/registry.py`. `python -m app.cli template-hash classic@1` prints it |
| Template freeze | Once `classic@1` is registered (end of M4), its files never change. Any change becomes `classic@2` |
| Recorded per artifact | `template_id`, `template_sha256`, `renderer_version` (the installed WeasyPrint version) |
| Determinism | Not required. Re-rendering may produce different bytes (for example the PDF creation date); the stored file is authoritative and is never replaced once `ready` |

## 12. Document versioning

| Versioned thing | Mechanism | Rule |
| --- | --- | --- |
| Draft edits | `documents.version` → ETag | Every save increments it; a stale `If-Match` → 412 |
| Templates | `code@version` (`classic@1`) | A registered version is immutable |
| Calculation rules | `calc_version` (`calc-1.0.0`) | Recorded in each snapshot; old snapshots are never recalculated |
| Snapshot structure | `schema_version` (`snapshot-1`) | New fields create a new schema version; the renderer supports every version present |
| Issued invoices | **Not versioned** | Never revised. Corrections use cancellation and credit notes, which are new documents with their own numbers (P1-10) **[CA]** |

## 13. SPECIMEN statement and watermark

| Item | Rule |
| --- | --- |
| Exact text | `SPECIMEN — demonstration document, not a tax invoice.` (with an em dash, U+2014, between spaces, and a final full stop). It is one constant in code, copied into `labels.specimen_text` |
| Placement | Every page of **every** PDF (preview and final), in the running footer (a CSS `@page` margin box), at least 8 pt, in the muted ink colour, never hidden or clipped |
| Final PDF | Title "Invoice"; SPECIMEN footer; no watermark |
| Draft preview | Diagonal watermark `DRAFT — NOT ISSUED` on every page behind the content (light grey); number shown as "Not yet issued"; issue date shown as "Assigned when finalised"; SPECIMEN footer |
| Forbidden words in P0-Lite PDFs | "Tax Invoice", "GST" (except the "GSTIN" label of an entered GSTIN), "CGST", "SGST", "IGST", "HSN", "SAC", "certified", "compliant" |
| Tests | Template-level assertions in IT-DOC-04 and IT-PDF-01; visual checks in DC-11 and DC-14 |

## 14. Deferred tax and statutory rules (not implemented; all [CA])

Each item must be reviewed and approved in writing by a CA before implementation (P1-05 and later). The references describe rules found during research and must be re-verified.

| Topic | What must be decided | Why it is deferred |
| --- | --- | --- |
| GST calculation | Rates per line; CGST + SGST versus IGST; cess | Depends on place of supply and registration; errors create tax liability |
| Place of supply | Chosen explicitly by the user, never inferred automatically (Revision 2 correction 4), including the IGST Act section 12 special cases for services (verify) | Wrong inference gives the wrong tax type |
| Tax invoice contents | The mandatory particulars of CGST Rule 46, including clause (b) (serial number of at most 16 characters, unique per financial year) and the signature requirement (verify clause references) | Required for a valid tax invoice |
| Document titles | "Tax Invoice" versus "Bill of Supply" and other variants | Depends on registration type |
| E-invoicing gate | Applies when aggregate turnover **exceeds** ₹5 crore in any preceding financial year from 2017-18, with exempt classes. Under Rule 48(5), an invoice not issued through the IRP when required is not a valid invoice (verify) | Requires IRP integration (P2-06) |
| Rounding | ROUND_HALF_UP per line (A-11); rupee round-off on the grand total (Q-17) | Professional confirmation needed |
| Numbering | Format, series per document type, financial-year reset (A-09, Q-16) | Must meet Rule 46(b) once GST applies |
| Credit notes and cancellation | Process and reporting | P1-10 |
| Record retention | Period and format; CGST Act section 36 reportedly requires 72 months from the annual-return due date (verify) | Affects deletion policy (Q-18, 12 §16) |
| Salary slips | Statutory components (PF, ESI, professional tax, TDS) | Payroll expertise needed (Q-22, P2-01) |

## 15. Fixtures (canonical test cases)

These fixtures live in `backend/tests/fixtures/invoice_fixture.json` and drive UT-CALC, UT-FMT and DC-07/DC-08.

| ID | Input | Expected |
| --- | --- | --- |
| F-01 | `2.5` × `800.00`, percent `10` | gross 2000.00, discount 200.00, line 1800.00 |
| F-02 | `3` × `333.33`, amount `99.99` | gross 999.99, discount 99.99, line 900.00 |
| F-03 | Document with F-01 + F-02 | gross_total 2999.99, discount_total 299.99, **grand_total 2700.00** |
| F-04 | `1.005` × `1.00`, none | gross **1.01** (half-up; binary floating point would give 1.00) |
| F-05 | `1` × `999.99`, percent `12.5` | discount 125.00 (from 124.99875), line 874.99 |
| F-06 | `1` × `100.00`, percent `100`, as the only line | line 0.00; finalisation blocked with `zero_total` |
| F-07 | `0.333` × `3.00` | gross 1.00 (from 0.999) |
| F-08 | `2` × `0.00` | gross 0.00 (allowed on a line) |
| F-09 | `1` × `1000.00`, amount `1000.01` | 422 `validation_failed` with field code `exceeds_gross` at `/lines/0/discount_value` |
| F-10 | quantity `"1.0005"`; `"0"`; `"1000000.001"`; JSON number `2.5` | `too_many_decimals`; `out_of_range`; `out_of_range`; `must_be_string` |
| F-11 | `1000000` × `10000000.00` | gross 10,000,000,000,000.00 → `total_too_large` |
| F-12 | 201 lines | `too_many_lines` |
| F-13 | `0.125` × `1.00` | gross **0.13** (ROUND_HALF_UP; ROUND_HALF_EVEN would give 0.12) |
| F-14 | `1` × `100.00`, percent `33.33` | discount 33.33, line 66.67 |
| F-15 | Format `123456.78`, `2700.00`, `0.50`, `9999999999999.99` | ₹1,23,456.78 · ₹2,700.00 · ₹0.50 · ₹99,99,99,99,99,999.99 |
| F-16 | Financial year and number formatting | As in §7: `26-27`, `27-28`, `99-00`; sequence 1 → `INV/26-27/00001`; 100000 → `INV/26-27/100000` |
