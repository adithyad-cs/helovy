# 11 — QA and Acceptance

| | |
| --- | --- |
| Document | Test specification · version 1.1 · 23 November 2026 |
| Separation | §3 = **mandatory demonstration checks** (P0-Lite, 25 November). §4 = **full-product acceptance tests** (P1 and P2, deferred) |
| Fixtures | 09 §15 (F-01 to F-16); demonstration data in §5 |

## 1. Strategy

| Level | Tooling | Where | Runs |
| --- | --- | --- | --- |
| Unit (pure) | pytest, hypothesis | `backend/tests/unit` | Every milestone; no services needed |
| Database | pytest against `ps5_test` (PostgreSQL 16) | `backend/tests/db` | Every milestone from M1 |
| API integration | pytest + httpx (FastAPI test client) against `ps5_test` and a test bucket | `backend/tests/integration` | Every milestone from M1 |
| Frontend static | `tsc --noEmit`, ESLint, `npm run build` | `frontend` | Every milestone from M0 |
| Manual UI | FE-04 checklist, FE-05 responsive matrix | Browser | M7, M8 |
| End to end | E2E-01 manual script (MUST); E2E-02 Playwright (STRETCH, S-03) | Local stack | M8 (E2E-01) |
| Demonstration checks | DC-01 to DC-20 | Demonstration machine | M8, after the freeze |

**Never-cut suites.** These stay automated even under reduction rule R6 (10 §6.3): UT-CALC, UT-NUM, UT-SNAP, UT-SEC, DB-01, DB-03 to DB-08, IT-AUTH, IT-TEN, IT-FIN, IT-PDF-01, IT-PDF-02.

**Test isolation.** Each test module starts from migrated, empty tables (truncated with the migrator role). Tests that create two organizations use factory helpers. A clock fixture freezes time for expiry and financial-year tests.

## 2. Test suites

### 2.1 Backend unit tests

| ID | Test | Expected |
| --- | --- | --- |
| UT-CALC-01 | F-01 line | 2000.00 / 200.00 / 1800.00 |
| UT-CALC-02 | F-02 line | 999.99 / 99.99 / 900.00 |
| UT-CALC-03 | F-03 document totals | 2999.99 / 299.99 / 2700.00 |
| UT-CALC-04 | F-04 and F-13 half-up edges | 1.01 and 0.13 |
| UT-CALC-05 | F-05, F-07, F-14 percent and fractional rounding | As in 09 §15 |
| UT-CALC-06 | F-09 amount discount above gross | `exceeds_gross` with the correct pointer |
| UT-CALC-07 | F-10 to F-12 limits | Field codes `too_many_decimals`, `out_of_range`, `must_be_string`, `total_too_large`, `too_many_lines` |
| UT-CALC-08 | Property-based (hypothesis), valid inputs only | 0 ≤ discount ≤ gross; line_total = gross − discount; totals equal the sums; every output has exactly 2 decimals; grand_total = gross_total − discount_total |
| UT-CALC-09 | Type safety | No `float` in calc results (type assertions); a JSON number input is rejected by the schema |
| UT-NUM-01 | Financial year from dates, including the Asia/Kolkata boundary (09 §7) | `26-27`, `27-28`, `99-00`; 18:29:59Z versus 18:30:00Z on 31 March |
| UT-NUM-02 | Number formatting | 1 → `INV/26-27/00001`; 99999 → 5 digits; 100000 → `INV/26-27/100000` (16 characters); longer → exhausted |
| UT-SNAP-01 | Canonical JSON | Same payload in a different key order gives the same bytes and SHA-256; no whitespace |
| UT-SNAP-02 | JSONB round trip (needs the database) | Stored payload re-canonicalised gives an equal hash |
| UT-SNAP-03 | Snapshot content | Contains seller, buyer, lines, totals and the exact SPECIMEN text; all money values are strings |
| UT-SEC-01 | Argon2id | The hash starts with `$argon2id$`; verification succeeds and fails correctly; parameters meet V-13 |
| UT-SEC-02 | CSRF token | HMAC over the session ID verifies; a token from another session fails; comparison is constant-time (`hmac.compare_digest`) |
| UT-SEC-03 | Restricted URL fetcher | Bundled asset paths are served. `http:`, `https:`, `ftp:`, `data:`, `file:` outside the assets directory and path traversal (`../`) are all rejected |
| UT-FMT-01 | Money, quantity, percent and date formatting (F-15) | ₹1,23,456.78; ₹2,700.00; ₹0.50; ₹99,99,99,99,99,999.99; `2.500` → 2.5; 25 Nov 2026 |
| UT-WORDS-01 | Amount in words (S-05 only) | The 09 §6 examples |

### 2.2 API integration tests (general)

| ID | Test | Expected |
| --- | --- | --- |
| IT-BIZ-01 | Create a business; create a second one | 201 with ETag; then 409 `business_already_exists` |
| IT-BIZ-02 | Business validation | PIN code, state code, GSTIN pattern and `state_mismatch` give 422 with pointers |
| IT-BIZ-03 | PATCH concurrency | Stale `If-Match` → 412; missing → 428; success increments the ETag |
| IT-CUS-01 | Customers: create, list, prefix search, pagination | Correct order; `q` is a case-insensitive prefix; `next_cursor` works; a tampered cursor gives 422 |
| IT-CUS-02 | Customer PATCH with ETag; clearing optional fields with `null` | 200 and the new ETag; `display_name: null` gives 422 `validation_failed` with field code `not_null` |
| IT-DOC-01 | Create a draft; PATCH with full line replacement; GET | Computed lines and totals match the fixtures; `version` increments |
| IT-DOC-02 | Delete a draft; try to delete a finalised document | 204; then 409 `document_not_draft` |
| IT-DOC-03 | E-14 calculate | Fixture results; JSON numbers rejected; 0 lines gives zero totals; the 61st call in a minute gives 429 |
| IT-DOC-04 | E-20 preview | 200 `application/pdf`, starts with `%PDF-`. The rendered HTML (template-level assertion) contains "DRAFT — NOT ISSUED", the exact SPECIMEN text and no number. 0 lines → 422 `validation_failed` with field code `no_lines`. Finalised → 409 |
| IT-DOC-05 | E-16 history list | Status filter; `q` matches a number prefix and a customer prefix (snapshot name for finalised, current name for drafts); pagination; drafts have `grand_total: null` |
| IT-HLT-01 | Health | `/healthz` 200 without the database. `/readyz` 503 when the database or storage is down, or the template hash mismatches with `APP_ENV=demo`; 200 when all is well |
| IT-GEN-01 | Conventions | Unknown field → 422 `validation_failed` with field code `unknown_field`; non-JSON body → 400 `malformed_request`; body over 256 KiB → 413; problem+json shape (`code`, `request_id`); `X-Request-ID` echoed; `Cache-Control: no-store` |

### 2.3 Financial calculation tests

Covered by UT-CALC-01 to UT-CALC-09 (§2.1), driven by fixtures F-01 to F-14 in `invoice_fixture.json`. In addition:

- the same fixtures are run through E-14 (IT-DOC-03) and through finalisation (IT-FIN-01), so the API and the snapshot agree with the pure module;
- the database backstop `document_lines_discount_ck` is checked by DB-02 with an amount discount above `round(quantity × unit_price, 2)`.

### 2.4 Database tests

| ID | Test | Expected |
| --- | --- | --- |
| DB-01 | `alembic upgrade head` on an empty `ps5_test` | Succeeds; every constraint, index and trigger name in 06 exists (checked through `pg_catalog`) |
| DB-02 | Constraints | Composite FKs reject a document whose customer belongs to another business; the discount check rejects an amount above gross; the state check rejects a finalised row without a number |
| DB-03 | `trg_documents_guard` | UPDATE or DELETE of a finalised document raises SQLSTATE 23001; the draft → finalized transition is allowed |
| DB-04 | `trg_document_lines_guard` | INSERT, UPDATE or DELETE of a finalised document's lines raises |
| DB-05 | `trg_document_snapshots_immutable` | UPDATE or DELETE raises |
| DB-06 | `trg_document_artifacts_guard` | DELETE raises; UPDATE of a `ready` artifact raises |
| DB-07 | `trg_audit_events_append_only` | UPDATE or DELETE raises |
| DB-08 | Grants | As `ps5_app`: UPDATE and DELETE on `document_snapshots`, `audit_events` and `stored_files` are denied; TRUNCATE is denied everywhere; any write to `templates` is denied |
| DB-09 | Uniqueness | Duplicate `(business_id, doc_type, document_number)` and `(number_series_id, sequence_no)` are rejected |

### 2.5 Tenant isolation tests

| ID | Test | Expected |
| --- | --- | --- |
| IT-TEN-01 | Organization B's session calls every org-scoped endpoint (E-07 to E-12, E-14 to E-23) with organization A's IDs | 404 `not_found` every time, with no difference in response shape or timing class from a truly missing ID |
| IT-TEN-02 | Lists (E-09, E-16) for organization B | Never include organization A's records |
| IT-TEN-03 | Database level, bypassing the app | Inserting a document with organization B's `org_id` and organization A's business, or a line pointing at another organization's document, fails the composite FKs |

### 2.6 Authentication tests

| ID | Test | Expected |
| --- | --- | --- |
| IT-AUTH-01 | Successful sign-in | 200; the cookie is HttpOnly, Secure, SameSite=Lax and Path=/; the body has `csrf_token`; audit `auth.login_succeeded`; any old session presented is revoked |
| IT-AUTH-02 | Wrong password versus unknown email versus inactive user | Identical 401 `invalid_credentials` bodies; audit `auth.login_failed` with `subject_hash` |
| IT-AUTH-03 | Throttling | The 6th attempt within 15 minutes for one email → 429 with `Retry-After`; the same per IP across different emails; failures older than 15 minutes stop counting |
| IT-AUTH-04 | Sign-out | 204; reusing the cookie → 401 |
| IT-AUTH-05 | Expiry (frozen clock) | Idle for more than 24 h → 401; older than 7 days → 401 even if active |
| IT-AUTH-06 | CSRF and Origin | A POST, PATCH or DELETE without the token, with a wrong token or with a wrong `Origin` → 403 `csrf_failed`; sign-in with a wrong `Origin` → 403 |

### 2.7 Invoice finalisation tests

| ID | Test | Expected |
| --- | --- | --- |
| IT-FIN-01 | Happy path | 200. Number `INV/{fy}/00001`; issue date is the Asia/Kolkata date of the frozen clock. The snapshot exists with a valid `canonical_sha256` and fixture totals. Audit `document.finalized`. The artifact goes from `pending` to `ready` (the background task runs in the test). `version` incremented |
| IT-FIN-02 | Preconditions | No `Idempotency-Key` → 400; no `If-Match` → 428; stale → 412 |
| IT-FIN-03 | Idempotency | The same key and request → the same body with `Idempotent-Replayed: true`, and no second number. The same key on a different document → 422 `idempotency_key_mismatch` |
| IT-FIN-04 | Concurrency (threads with separate connections) | Ten drafts finalised at once → numbers 00001 to 00010, unique and without gaps. One draft with two different keys at once → one 200 and one 409 `document_not_draft`. The same key twice at once → one 200, and the other is replayed or gets 409 `idempotency_in_progress` |
| IT-FIN-05 | Blocked finalisation | No lines → `no_lines`; F-06 → `zero_total`; F-11 → `total_too_large`; past due date → `due_date_before_issue_date`; inactive template → `inactive`; all 422 `finalization_blocked` |
| IT-FIN-06 | Rollback consumes no number | Inject a failure after step 7 (for example at the snapshot insert) → 5xx; the next finalisation still gets 00001 |
| IT-FIN-07 | Exhaustion | Set `next_seq = 1000000` → 409 `number_series_exhausted`; nothing persisted |

### 2.8 PDF tests

| ID | Test | Expected |
| --- | --- | --- |
| IT-PDF-01 | Final PDF storage | Object key `orgs/{org}/documents/{doc}/final-{artifact}.pdf`; `stored_files.sha256` equals the SHA-256 of the bytes; an anonymous S3 GET of the object is refused; E-22 returns identical bytes with `Content-Digest`; the template-level render contains the exact SPECIMEN text and the title "Invoice" |
| IT-PDF-02 | Tamper detection | Overwrite the object in storage → E-22 returns 500 `integrity_check_failed`, does not serve the bytes, and logs an ERROR line |
| IT-PDF-03 | Failure and retry | Storage unavailable during the render → artifact `failed` (`storage_error`) and audit `document.pdf_render_failed`. Storage back + E-23 → `ready`; `document_number` unchanged; `attempts` = 2 |
| IT-PDF-04 | Retry rules | `ready` → 200 with nothing done; `pending` for less than 120 s → 409 `pdf_render_in_progress`; `pending` for more than 120 s (frozen clock) → 202; a second call within 10 s → 429 |
| IT-PDF-05 | Rendering isolation | A template variant referencing an external URL renders without fetching it (the fetcher refuses it); a render exceeding the timeout is killed and recorded as `render_timeout` |

### 2.9 Frontend tests

| ID | Test | Expected |
| --- | --- | --- |
| FE-01 | `npx tsc --noEmit` | No errors |
| FE-02 | `npm run lint` | No errors |
| FE-03 | `npm run build` | Succeeds; no inline scripts in `index.html` (CSP) |
| FE-04 | Manual UI checklist, per page in 08 | Loading, empty, error and success states each seen once. Keyboard-only run of the main flow with visible focus. `aria-live` messages announced (spot check with a screen reader if one is available). No out-of-scope UI (03 §8). Money formatting matches 09 §6, including a lakh value. Reduced motion respected |

No frontend unit-test runner is used (05 §2; C-10 in 14 §4).

### 2.10 Responsive tests

| ID | Test | Expected |
| --- | --- | --- |
| FE-05 | Responsive matrix: every P0-Lite page at 360, 768 and 1280 px (R4: 360 and 1280 only) in Chrome device emulation, plus one real phone if available | No horizontal scrolling at 360 px (except inside the editor lines table at 768 px and above); navigation drawer below 768 px; lists as cards below 768 px; the editor's sticky total bar visible on mobile; dialogs fit the viewport |

### 2.11 End-to-end workflow

| ID | Test | Status |
| --- | --- | --- |
| E2E-01 | The demonstration script in §7, run manually on the frozen build | MUST |
| E2E-02 | The same flow automated with Playwright against the local stack | STRETCH (S-03) |

## 3. Mandatory demonstration checks (P0-Lite)

Run on the **demonstration machine** after the freeze (M8). Record the result (Pass / Fail / Deferred) of each in PROGRESS.md.

| ID | Check | How | Expected |
| --- | --- | --- | --- |
| DC-01 | Stack health | `docker compose up -d`; open `/healthz` and `/readyz` | Both 200; `readyz` checks all `ok` |
| DC-02 | Landing page | Open `/`; reload with reduced motion emulated | Animation shows the lines → ₹2,700.00 → FINALISED INV/26-27/00001 in under 5 s; a static final frame under reduced motion; ENTER THE SYSTEM opens `/login` |
| DC-03 | Sign-in failure | **One** attempt with a wrong password. Do not repeat, because 5 failures throttle the account and this IP for 15 minutes | "Email or password is incorrect." |
| DC-04 | Sign-in, cookie, sign-out | Sign in; inspect the cookie in DevTools; sign out; press Back | Dashboard; `ps5_session` is HttpOnly, Secure, SameSite=Lax; after sign-out, protected pages redirect to `/login` |
| DC-05 | Business profile | Edit the phone number; try PIN `012345` | Saved with a toast; the invalid PIN shows a field error |
| DC-06 | Customers | Create "Harbour Line Logistics (Demo)"; search "Harb"; edit the city | Appears in the list; prefix search finds it; the edit is saved |
| DC-07 | Fixture totals | New invoice; lines F-01 and F-02 | Line amounts ₹1,800.00 and ₹900.00; Subtotal ₹2,999.99; Discount −₹299.99; Total **₹2,700.00** (from E-14) |
| DC-08 | Half-up edge | Temporary line 1.005 × ₹1.00 | Amount ₹1.01; then remove the line |
| DC-09 | Validation | Quantity `0`; amount discount above gross; quantity `1.0005` | Inline field messages; Save blocked; nothing invalid stored |
| DC-10 | Draft persistence | Save; reload the browser | Identical draft and totals |
| DC-11 | Watermarked preview | Preview PDF | Classic layout; diagonal "DRAFT — NOT ISSUED"; "Not yet issued"; footer with the exact text "SPECIMEN — demonstration document, not a tax invoice." |
| DC-12 | Finalisation | Finalise → confirm | Next number (for example `INV/26-27/00002`); today's date in India; status Finalised; the editor is replaced by the read-only details |
| DC-13 | Duplicate protection | Double-click Finalise on another draft; in IT-FIN-03, a replay with the same key | Exactly one number allocated; history shows no duplicate |
| DC-14 | Final PDF integrity | Wait for Ready → Download → run `sha256sum` on the file | The hash equals the PDF SHA-256 on the details page; the PDF title is "Invoice"; the SPECIMEN text is on every page; no watermark |
| DC-15 | Snapshot integrity | Change the business phone and the customer city; re-download the finalised invoice | Byte-identical file (same SHA-256), still showing the original phone and city |
| DC-16 | Immutability | `curl` E-18 on the finalised document (with session and CSRF); as `ps5_app`, run `UPDATE documents SET notes='x' WHERE id=…` in `psql` | 409 `document_not_draft`; the database raises the trigger error |
| DC-17 | Persistence across restart | `docker compose down` (**without** `-v`) → `docker compose up -d` | Every invoice, customer and PDF is still there; the re-downloaded hash is unchanged |
| DC-18 | PDF failure and retry | `docker compose stop storage` → finalise a draft → status Failed → `docker compose start storage` → Retry | The number is kept; the PDF becomes Ready; it downloads and its hash matches |
| DC-19 | Tenant isolation | Run `pytest tests/integration/test_tenancy.py` on the frozen build. In a private window, sign in as the second account (§5) and open organization A's invoice URL | Suite green; "This item doesn't exist or you don't have access to it." |
| DC-20 | Responsive, states, keyboard | FE-05 widths on the main pages; trigger one empty, one loading and one error state; keyboard-only finalise flow | Usable layouts; states shown as specified; keyboard flow works |

**Acceptance rule:** P0-Lite is demonstration-ready when DC-01 to DC-20 pass. A failing check is either fixed before the freeze (an S1 or S2 defect, §6) or removed from the live script and announced as deferred. It is never hidden.

## 4. Full-product acceptance tests (DEFERRED)

These apply to P1 and P2 and are detailed when each feature is approved. Client acceptance criteria must be agreed with Heloavy (Q-12).

| ID | Feature | Acceptance focus |
| --- | --- | --- |
| AT-01 | P1-01 sign-up, verification, reset | Unverified accounts are blocked; reset tokens are single-use and expire; flows are throttled |
| AT-02 | P1-02 roles | Every endpoint enforces roles; staff cannot access owner-only actions (`forbidden_role`) |
| AT-03 | P1-03 logo upload | PNG only, re-encoded, size and dimension limits, metadata stripped; SVG and EPS rejected; private storage |
| AT-04 | P1-04 plans and limits | Limits enforced atomically at finalisation; premium templates gated; no real checkout without an approved provider |
| AT-05 | P1-05 GST | CA-approved fixtures match; place of supply always explicit; `gst_approved` impossible without a recorded CA approval; e-invoicing gate respected |
| AT-06 | P1-06 receipts | Own number series; snapshot and PDF pipeline; optional link to an invoice |
| AT-07 | P1-07 payment requests | Own series; correct content; no gateway unless approved |
| AT-08 | P1-08 payment recording | Partial payments; balances correct to the paisa; audit |
| AT-09 | P1-09 bills | As defined after Q-13 |
| AT-10 | P1-10 cancellation and credit notes | The original stays immutable; the credit note references it; reports reflect it |
| AT-11 | P1-12 exports | Organization-scoped; only finalised data; audit event |
| AT-12 | P1-14 hardening | Row-level security blocks cross-tenant SQL even with app bugs; MFA; backup restore drill passes; document encryption; monitoring alerts fire |
| AT-13 | P2-01 salary slips | Payroll privacy controls (restricted roles, field encryption, minimal retention); statutory components approved (Q-22) |
| AT-14 | P2-02 multiple businesses | Per-business series and profiles; no cross-business leakage |
| AT-15 | P2-06 e-invoicing | IRP integration verified in the sandbox; only eligible businesses |

## 5. Test and demonstration data (synthetic only)

| Item | Value |
| --- | --- |
| Demonstration account | `owner@demo.invalid`, display name "Demo Owner", organization "Demo Studio". The password is set through `DEMO_ACCOUNT_PASSWORD` at creation and is **never written in any document or repository** |
| Isolation-check account (DC-19) | `auditor@demo.invalid`, organization "Isolation Check Org" (no business, or its own) |
| Business | "Lotus Lane Design Studio (Demo)", 12 Example Road, Indiranagar, Bengaluru, state 29, PIN 560038, phone +91 80 0000 0000, `accounts@demo.invalid`, **GSTIN empty** |
| Customers | "Riverstone Consulting (Demo)", Pune, 27, 411001 · "Saffron Leaf Foods (Demo)", Chennai, 33, 600001 · "Harbour Line Logistics (Demo)" (created live) |
| Prepared documents | One finalised invoice for Riverstone with lines F-01 + F-02 (total ₹2,700.00), PDF ready. One draft for Saffron Leaf |
| Rules | Every name carries "(Demo)". Emails use `.invalid`. Phone numbers are placeholders. No real GSTINs, people or companies. No real personal data |
| Automated test data | Factories plus `tests/fixtures/invoice_fixture.json`; the test database and bucket only |

## 6. Definition of done and defect severity

**A milestone is done when:**

1. its deliverables (10 §3) exist;
2. its listed tests pass;
3. ruff, mypy, ESLint and `tsc` are clean;
4. no stub or mock is presented as working;
5. PROGRESS.md is updated;
6. the work is committed.

**A feature is done when** its 03 acceptance conditions hold, all its UI states exist, and it shows nothing out of scope.

| Severity | Examples | Rule before the freeze |
| --- | --- | --- |
| S1 Blocker | Wrong totals; duplicate or reused numbers; cross-tenant data visible; data lost on restart; issued document changed; security bypass; demonstration path broken | Fix, or remove the feature from the demonstration (deferred). Never ship it |
| S2 Major | Feature broken but with a workaround; a missing state on a main page | Fix if time allows; otherwise document it and avoid it in the script |
| S3 Minor | Layout glitch on one width; unclear copy | Fix if trivial; otherwise record it in PROGRESS.md |
| S4 Cosmetic | Spacing, alignment | Record it |

## 7. Demonstration script (E2E-01, about 5 minutes)

**Before starting:**

- laptop on mains power, sleep and notifications off;
- Chrome at 100 % zoom; stack started and DC-01 run;
- the prepared data (§5) present;
- the password typed carefully: five failures throttle sign-in for 15 minutes;
- never run `docker compose down -v`.

| Step | Action | Say or show |
| --- | --- | --- |
| 1 | Open `/`; let the animation play | "The server calculates, numbers once and stores the exact PDF it issued." |
| 2 | ENTER THE SYSTEM → sign in | Real Argon2id password check and a server session |
| 3 | Dashboard | The prepared invoice INV/26-27/00001 |
| 4 | Business profile | Details entered once; issued invoices keep their original details |
| 5 | Customers → New customer "Harbour Line Logistics (Demo)" | Saved to PostgreSQL |
| 6 | Invoices → New invoice → choose Harbour Line | A draft is created |
| 7 | Add line 1: 2.5 × ₹800.00, 10 % discount | ₹1,800.00 calculated by the server |
| 8 | Add line 2: 3 × ₹333.33, ₹99.99 discount | Total ₹2,700.00 |
| 9 | Save → reload the page | The draft persists |
| 10 | Preview PDF | Watermark and the SPECIMEN statement |
| 11 | Finalise → confirm | Next number and today's date; one transaction |
| 12 | Wait for Ready → Download → open the PDF | The real stored PDF |
| 13 | Integrity section; optionally `sha256sum` | The fingerprint matches |
| 14 | Invoices → Finalised → search "Harb" → open → Download again | Byte-identical file |
| 15 (optional) | Try to edit | Locked: finalised invoices are immutable |
| 16 (optional) | Private window as `auditor@demo.invalid`, paste the invoice URL | Not found: tenant isolation |
| 17 | Close | What is deferred (receipts, payment requests, salary slips, plans, GST after CA approval) and the next steps (14) |

If a step fails, follow the fallback strategy (10 §7). Never improvise a workaround that hides the failure.
