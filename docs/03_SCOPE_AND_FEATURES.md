# 03 — Scope and Features

| | |
| --- | --- |
| Document | Feature inventory · version 1.1 · 23 November 2026 |
| Rule | Build **only** the MUST features in §2 for 25 November, as an aggressive, conditional target: the checkpoints in 10 §6 decide what is reduced or deferred. Start §3 only under the conditions in 10 §5. Everything else is deferred or excluded. |
| Read with | 02 (requirements), 07 (endpoints), 10 (plan and statuses), 11 (acceptance) |

## 1. How to read this inventory

| Field | Meaning |
| --- | --- |
| Status | **MUST COMPLETE**, **STRETCH** or **DEFERRED** (the same three statuses as 10). MUST COMPLETE marks the target scope, built first; it is not a completion guarantee (10 §5). Excluded features (§6) are not planned. |
| Source | **Official**: in the PS5 requirement list. **Engineering**: needed to deliver the official requirements safely. **Enhancement**: a proposal that needs Heloavy's approval. |
| Complexity | For P0-Lite and stretch: S (about 1 h or less), M (1–3 h), L (more than 3 h) for one developer with Claude Code. For P1 and P2: a relative size of S, M, L or XL. |
| Milestone | Where it is built in 10 §3 |

## 2. P0-Lite: the 25 November demonstration (MUST COMPLETE)

### L-01 Landing page and ENTER THE SYSTEM

- **Purpose:** introduce HIVE DOCS and lead into the real application.
- **User benefit:** a visitor understands the value in seconds and reaches the product in one click.
- **Source:** Engineering (presentation entry point required by the master prompt).
- **Dependencies:** L-03 (routes); E-05 (session check for the redirect).
- **Priority:** MUST COMPLETE. **Complexity:** M. **Milestone:** M7.
- **Acceptance conditions:**
  1. The page has a headline, a sub-headline, three value points and a workflow strip (08 §10).
  2. The animation shows an invoice being assembled. At minimum it has three beats: lines appear, the total appears, a FINALISED stamp with the number. It uses the fixture figures (₹1,800.00, ₹900.00, total ₹2,700.00), finishes in under 5 s, plays once, and shows a static final frame under `prefers-reduced-motion`.
  3. ENTER THE SYSTEM goes to `/login`, or to `/app` when a session exists.
  4. There are no pricing, testimonials, client logos or deferred features. A footer note says that the documents are specimens, not tax invoices.

### L-02 Secure demonstration sign-in and session

- **Purpose:** authenticate the single demonstration owner the same way production will.
- **User benefit:** a private workspace protected by a real password check.
- **Source:** Engineering.
- **Dependencies:** M1 migration (users, sessions, organizations, memberships, audit_events); CLI `create-demo-account`.
- **Priority:** MUST COMPLETE. **Complexity:** M. **Milestone:** M1. **Endpoints:** E-03, E-04, E-05.
- **Acceptance conditions:**
  1. FR-02 to FR-07 hold.
  2. The account exists only through the CLI, with a password of at least 12 characters taken from `DEMO_ACCOUNT_PASSWORD` or an interactive prompt.
  3. There is no sign-up page, no default credentials and no auto-login.
  4. IT-AUTH-01 to IT-AUTH-06 pass.

### L-03 Application shell and navigation

- **Purpose:** consistent layout and navigation for every signed-in screen.
- **User benefit:** the owner always knows where they are and can sign out.
- **Source:** Engineering.
- **Dependencies:** L-02.
- **Priority:** MUST COMPLETE. **Complexity:** S. **Milestone:** M1.
- **Acceptance conditions:**
  1. The navigation has Dashboard, Invoices, Customers, Templates and Business, plus a user menu with Sign out.
  2. The current page is highlighted. Below 768 px the navigation opens as a drawer.
  3. Unknown routes show a 404 page. Protected routes redirect to `/login` and return to the original page after sign-in.

### L-04 Business profile (single business)

- **Purpose:** hold the issuer details printed on invoices.
- **User benefit:** details are entered once and appear correctly on every invoice.
- **Source:** Official (business profiles).
- **Dependencies:** L-02.
- **Priority:** MUST COMPLETE. **Complexity:** S–M. **Milestone:** M2. **Endpoints:** E-06, E-07, E-08.
- **Acceptance conditions:**
  1. The profile is created once per organization; a second create returns 409 `business_already_exists`.
  2. Edits use `If-Match`.
  3. Validation follows 09 §4 (PIN code, state, optional GSTIN format and state match).
  4. `business.created` and `business.updated` audit events are written.
  5. Editing the profile does not change issued invoices (DC-15).

### L-05 Customers

- **Purpose:** store buyer details for reuse.
- **User benefit:** no re-typing; quick search.
- **Source:** Official (supports invoices).
- **Dependencies:** L-04.
- **Priority:** MUST COMPLETE. **Complexity:** M. **Milestone:** M2. **Endpoints:** E-09, E-10, E-11, E-12.
- **Acceptance conditions:**
  1. The owner can create, list (newest first, cursor pagination), search by case-insensitive name prefix and edit (`If-Match`).
  2. Validation follows 09 §4.
  3. Another organization's customer IDs return 404.
  4. Audit events `customer.created` and `customer.updated` are written.

### L-06 Invoice drafts

- **Purpose:** prepare an invoice that can be saved and changed until it is issued.
- **User benefit:** work can be interrupted and resumed safely.
- **Source:** Official (invoices).
- **Dependencies:** L-05, L-07.
- **Priority:** MUST COMPLETE. **Complexity:** L. **Milestone:** M3. **Endpoints:** E-15, E-17, E-18, E-19.
- **Acceptance conditions:**
  1. A draft is created for a chosen customer.
  2. The owner can add and remove lines (up to 200), with description, quantity, unit, unit price and a discount of none, percent or amount.
  3. Due date, reference, notes and terms are optional.
  4. Saving with a stale version gives 412 and the screen offers to reload.
  5. Reloading the page shows the saved draft (DC-10).
  6. A draft can be deleted after confirmation.
  7. Leaving with unsaved changes asks for confirmation.

### L-07 Server calculation and validation

- **Purpose:** make the server the only source of financial truth.
- **User benefit:** totals are always right.
- **Source:** Official (automatic calculations).
- **Dependencies:** none (pure module).
- **Priority:** MUST COMPLETE. **Complexity:** M. **Milestone:** M3. **Endpoint:** E-14 (also used inside E-17 and E-21).
- **Acceptance conditions:**
  1. The fixtures in 09 §15 match exactly.
  2. Half-up edge: 1.005 × ₹1.00 → ₹1.01.
  3. Money and quantity accept JSON strings only.
  4. Limits are enforced with JSON-pointer errors.
  5. Every response carries `calc_version` `calc-1.0.0`.
  6. UT-CALC-01 to UT-CALC-09 pass.

### L-08 Classic template with the SPECIMEN statement

- **Purpose:** a professional, consistent invoice layout.
- **User benefit:** documents look trustworthy without design work.
- **Source:** Official (free templates).
- **Dependencies:** L-07.
- **Priority:** MUST COMPLETE. **Complexity:** M. **Milestone:** M4. **Endpoint:** E-13.
- **Acceptance conditions:**
  1. The A4 layout follows 08 §20 and uses only the bundled fonts; the ₹ glyph renders.
  2. The title is "Invoice". The exact text "SPECIMEN — demonstration document, not a tax invoice." appears on every page.
  3. Amounts use Indian digit grouping.
  4. Long content flows across pages with a repeated table header and page numbers.
  5. The template files match their registered SHA-256; otherwise `/readyz` fails.

### L-09 Watermarked draft preview

- **Purpose:** show the owner exactly what will be issued.
- **User benefit:** catch mistakes before issuing.
- **Source:** Official (PDF generation).
- **Dependencies:** L-08.
- **Priority:** MUST COMPLETE. **Complexity:** S. **Milestone:** M4. **Endpoint:** E-20.
- **Acceptance conditions:**
  1. The preview has a diagonal "DRAFT — NOT ISSUED" watermark and the SPECIMEN text.
  2. It shows no number, and "Assigned when finalised" in place of the issue date.
  3. It opens in an in-app preview dialog (download or open on small screens) and is not stored.
  4. It is rate-limited to 20 per minute per session.
  5. Finalised documents return 409 `document_not_draft`.

### L-10 Atomic finalisation

- **Purpose:** issue the invoice exactly once, with a unique number and a frozen record.
- **User benefit:** numbers are never duplicated, and issued invoices cannot drift.
- **Source:** Official (invoices) + Engineering.
- **Dependencies:** L-06, L-07, L-08.
- **Priority:** MUST COMPLETE. **Complexity:** L. **Milestone:** M5. **Endpoint:** E-21.
- **Acceptance conditions:**
  1. The transaction follows 09 §8.
  2. `Idempotency-Key` is required: missing gives 400; the same key and request replays with `Idempotent-Replayed: true`; the same key with a different request gives 422; a concurrent duplicate gives 409.
  3. `If-Match` is required: missing gives 428, stale gives 412.
  4. Numbers are consecutive and unique under concurrency (IT-FIN-04); a rollback consumes no number (IT-FIN-06).
  5. Snapshot, audit event and pending artifact are written in the same transaction.
  6. Database triggers block later changes (DB-03 to DB-05).

### L-11 Final PDF: render, private storage, SHA-256, retry

- **Purpose:** produce and store the exact issued file.
- **User benefit:** the PDF the owner sent can be downloaded again, byte for byte, for as long as it is retained.
- **Source:** Official (PDF generation) + Engineering.
- **Dependencies:** L-10.
- **Priority:** MUST COMPLETE. **Complexity:** M–L. **Milestone:** M5. **Endpoints:** E-21 (starts the render), E-22, E-23.
- **Acceptance conditions:**
  1. The render runs after commit, in a separate worker process (at most 2 at once, killed after 20 s).
  2. The object is stored under `orgs/{org_id}/documents/{document_id}/final-{artifact_id}.pdf` in a private bucket.
  3. SHA-256 and size are recorded.
  4. Download checks the hash first, and a tampered object returns 500 `integrity_check_failed` (IT-PDF-02).
  5. Retry works for `failed` artifacts, and for `pending` artifacts older than 120 s, without renumbering (DC-18).

### L-12 History, details, reopen and download

- **Purpose:** find and reuse past invoices.
- **User benefit:** any invoice is found in seconds and re-sent unchanged.
- **Source:** Official (document management and history).
- **Dependencies:** L-10, L-11.
- **Priority:** MUST COMPLETE. **Complexity:** M. **Milestone:** M6. **Endpoints:** E-16, E-17, E-22.
- **Acceptance conditions:**
  1. The list shows number, customer, status, issue date, grand total (finalised only) and PDF status, newest first.
  2. It has a status filter, a search by number or customer-name prefix, and cursor pagination.
  3. The details page is read-only for finalised invoices.
  4. Downloads are byte-identical (DC-15).

### L-13 Minimal dashboard

- **Purpose:** a starting point after sign-in.
- **User benefit:** the next action is obvious.
- **Source:** Engineering.
- **Dependencies:** L-04, L-12.
- **Priority:** MUST COMPLETE. **Complexity:** S. **Milestone:** M6. **Endpoint:** E-16 (`limit=5`); business status from E-05.
- **Acceptance conditions:**
  1. Without a business, the dashboard shows only the "Set up your business" call to action.
  2. Otherwise it shows the New invoice and New customer actions and the five most recent invoices, with an empty state when there are none.
  3. It shows no charts, revenue figures or analytics.

### L-14 Tenant-scoped authorization

- **Purpose:** keep each organization's data private.
- **User benefit:** confidence that nobody else sees the business's documents.
- **Source:** Engineering (mandatory decisions 2, 3, 14, 15).
- **Dependencies:** all tenant endpoints.
- **Priority:** MUST COMPLETE. **Complexity:** M (cross-cutting). **Milestones:** M1–M6.
- **Acceptance conditions:**
  1. The organization always comes from the session.
  2. Composite foreign keys tie every child row to its organization (06 §4).
  3. IT-TEN-01 to IT-TEN-03 pass: other organizations' IDs return 404, lists never leak, and the database rejects cross-tenant references.

### L-15 Responsive UI, states, accessibility and reduced motion

- **Purpose:** a usable, professional interface on any screen.
- **User benefit:** works on a phone or a laptop; failures are explained.
- **Source:** Engineering.
- **Dependencies:** all screens.
- **Priority:** MUST COMPLETE. **Complexity:** M (cross-cutting). **Milestones:** M1–M7.
- **Acceptance conditions:**
  1. Every page in 08 has its loading, empty, error and success states.
  2. Layouts work at 360, 768 and 1280 px.
  3. The main flow works by keyboard alone, with visible focus.
  4. `prefers-reduced-motion` is honoured.
  5. Colour contrast meets the 08 §4 tokens.
  6. The FE-04 checklist passes.

### L-16 Docker runtime, persistence and health

- **Purpose:** a reliable, reproducible runtime for development and the demonstration.
- **User benefit:** the demonstration runs offline on one laptop, and data survives restarts.
- **Source:** Engineering (mandatory decision 10).
- **Dependencies:** none (built first).
- **Priority:** MUST COMPLETE. **Complexity:** M. **Milestones:** M0, M8.
- **Acceptance conditions:**
  1. Docker Compose runs the app, PostgreSQL 16 and SeaweedFS with named volumes; ports are bound to 127.0.0.1 only.
  2. `/healthz` and `/readyz` behave as in 07 (E-01, E-02).
  3. Restarting without deleting volumes keeps all data and PDFs (DC-17).
  4. No secrets are committed; `.env.example` contains placeholders only.

## 3. P0 stretch features (STRETCH)

Start these only when the conditions in 10 §5 hold. They never displace a MUST item.

| ID | Feature | Priority | Purpose / user benefit | Dependencies | Complexity | Acceptance conditions |
| --- | --- | --- | --- | --- | --- | --- |
| S-01 | Second free template "Minimal" and selector | STRETCH | A choice of look; demonstrates the template registry | L-08 | M | `minimal@1` appears in E-13; the editor selector saves `template_id`; the snapshot records it; SPECIMEN present; hash registered |
| S-02 | Cloud deployment on DigitalOcean BLR1 (time-boxed to 90 minutes) | STRETCH | A shareable HTTPS URL for evaluators | All MUST items done; CP4 passed | M | App Platform service from the Dockerfile; managed PostgreSQL 16 with `sslmode=require`; private Spaces bucket; `/readyz` 200; synthetic data only. If not healthy within 90 minutes, stop; the local stack stays the demonstration path |
| S-03 | Playwright automation of the E2E-01 script | STRETCH | Repeatable regression check | All MUST items | M | Runs headless against the local stack and passes; it does not replace the manual DC checks |
| S-04 | Full landing storyboard (six beats, line typing, history stack) | STRETCH | A richer first impression | L-01 | S–M | Matches 08 §10.3 in full; under 5 s; reduced-motion variant |
| S-05 | Amount in words (Indian system) on the PDF | STRETCH | Matches common Indian invoice practice | L-08 | S | UT-WORDS-01 fixtures pass, for example ₹2,700.00 → "Rupees Two Thousand Seven Hundred Only" |

## 4. P1: first usable client release (DEFERRED)

The composition of P1 is a working assumption (A-13) until Heloavy answers Q-06. Priorities are proposals for Heloavy to confirm. Nothing here may appear in the P0-Lite user interface.

| ID | Feature | Source | Priority (proposed) | Purpose and user benefit | Dependencies | Complexity | Acceptance conditions (summary) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P1-01 | Sign-up, email verification, password reset | Engineering | High | Real businesses can onboard themselves | Q-26 (domain, email provider) | M | Verified email before use; reset tokens single-use and expiring; throttled |
| P1-02 | Multiple users and roles (owner, staff) | Enhancement | Medium | Staff can prepare documents without owner credentials | P1-01 | M | Role checks on every endpoint; `forbidden_role` responses; invitations |
| P1-03 | Logo upload | Official (branding) | Medium | Branded documents | Private storage | M | PNG only, re-encoded server-side, size and dimension limits, metadata stripped; never SVG or EPS |
| P1-04 | Plans, usage limits and premium templates | Official | High | Commercial model; premium designs | Q-08 (pricing, payment provider) | L | Plan entitlements enforced at finalisation; usage counted atomically; premium templates gated; no real checkout until a provider is approved |
| P1-05 | GST: demonstration mode, then CA-approved mode | Official (calculations) + professional approval | High (gated by CA approval) | Tax invoices for registered businesses | Q-03, CA sign-off | XL | Place of supply chosen explicitly (never inferred); HSN/SAC codes; CGST/SGST/IGST rules; title rules; certified mode (`gst_approved`) stays locked until written CA approval; e-invoicing gate when turnover exceeds ₹5 crore (verify with CA) |
| P1-06 | Receipts | Official | High | Acknowledge payments received | P1-08 (for linked receipts) | M | Own number series; snapshot and PDF pipeline reused |
| P1-07 | Payment requests | Official | High | Ask customers to pay with clear details | Q-08 | M | Own number series; no payment gateway unless approved |
| P1-08 | Payment recording | Enhancement | Medium | Track paid and unpaid invoices | P1-06 | M | Partial payments; balance due; audit |
| P1-09 | Bills | Official | Medium (after Q-13) | Meaning to be defined | Q-13 | M–L | Defined after Q-13 is answered |
| P1-10 | Cancellation and credit notes | Engineering | High | Correct issued invoices without editing them | L-10 | M | Original stays immutable; the credit note references it; status `cancelled` added by migration |
| P1-11 | Duplicate a document as a new draft | Enhancement | Low | Faster repeat invoices | L-06 | S | Copies lines and customer; never copies number or dates |
| P1-12 | Exports (CSV) | Enhancement | Low | Hand data to an accountant | L-12 | S–M | Org-scoped; finalised invoices only; audit event |
| P1-13 | Customer archive | Engineering | Low | Hide inactive customers safely | L-05 | S | `archived_at` added; archived customers excluded from selection; issued documents unaffected |
| P1-14 | Production hardening | Engineering | High | Safe for real customer data | Q-04, Q-05, Q-11 | L | PostgreSQL row-level security; MFA; document encryption; backups with restore drill; monitoring and alerting; DPDP review (12 §14) |
| P1-15 | Product and service catalogue | Enhancement | Low | Reuse common line items | L-06 | M | Catalogue items prefill lines; prices are copied into the draft, not linked |
| P1-16 | Quick Counter Bill (optional) | Official title ("POS") interpretation | Conditional (Q-01) | Fast simple bills at a counter | **Written confirmation from Heloavy** (Q-01) | M | Only if confirmed; reuses the document pipeline; no checkout hardware, stock or barcode |

## 5. P2: future commercial expansion (DEFERRED)

| ID | Feature | Source | Priority (proposed) | Purpose and user benefit | Dependencies | Complexity | Acceptance conditions (summary) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P2-01 | Salary slips | Official | High (official) | Private, accurate monthly slips for staff | Q-22; a payroll privacy module (separate permissions, field encryption, restricted access, minimal retention) | L | Payroll privacy controls in place (restricted roles, field encryption, minimal retention); statutory components approved (Q-22); slips use the snapshot and PDF pipeline |
| P2-02 | Multiple businesses per organization | Enhancement | Medium | Owners with several firms | Remove `UNIQUE (org_id)` on `businesses`; business switcher | M | Per-business profiles and number series; switching business never shows another business's data |
| P2-03 | Recurring invoices | Enhancement | Medium | Automate monthly retainers | A job scheduler; P1-04 limits | M | Schedules create drafts by default (automatic finalisation only if approved); plan limits respected; every run audited |
| P2-04 | Email and WhatsApp sending | Enhancement | Medium | Send documents from the app | Provider approval; consent; P1-01 | M | Sending only through an approved provider, with recipient consent; the stored PDF is what is sent; delivery recorded |
| P2-05 | Advanced business management (reminders, simple reports) | Enhancement | Low | Visibility of dues and activity | P1-08 | L | Reports computed from finalised snapshots only; reminders are opt-in |
| P2-06 | E-invoicing through the IRP | Official (for eligible clients) | Conditional (eligible clients) | Required for businesses above the threshold | P1-05; CA; IRP access | XL | IRP sandbox verified; only eligible businesses (threshold verified with a CA); IRN and QR data stored in the snapshot |
| P2-07 | Localization (Hindi interface and documents) | Enhancement | Low | Wider reach | Q-23; Devanagari fonts already bundled | M | Hindi interface strings and documents render correctly with the bundled Devanagari font; language chosen per document |

## 6. Excluded features (not planned)

| Feature | Why excluded | What would change that |
| --- | --- | --- |
| Inventory management | Not in the restated requirements; a different product | A Heloavy decision under Q-01, re-planned as a new phase |
| Barcode scanning | Depends on inventory and retail checkout | As above |
| Retail checkout and POS hardware (cash drawer, receipt printer) | Not in the restated requirements; the P1-16 Quick Counter Bill is the most that is considered | Q-01 |
| Payment gateway; real subscription checkout in the demonstration | No provider approved; real money flows need production hardening | Q-08 and P1-14 |
| AI features | No requirement; no value for correctness | — |
| Drag-and-drop template designer | High complexity and rendering risk; versioned code templates are safer | — |
| Complex analytics | Not needed to prove the workflow | P2-05 covers simple reports if approved |
| Microservices | Mandatory decision 1 (modular monolith) | — |
| Recurring billing in P0-Lite and P1 | Restricted by the prompt | P2-03 if approved |

## 7. Official requirement traceability

| Official requirement | Covered by |
| --- | --- |
| Invoices | L-06, L-07, L-10, L-11, L-12 (P0-Lite); P1-05, P1-10, P2-06 |
| Bills | P1-09 (after Q-13); P1-16 if POS-style bills are confirmed |
| Salary slips | P2-01 |
| Payment requests | P1-07 |
| Receipts | P1-06 |
| Free templates | L-08; S-01 |
| Premium templates | P1-04 |
| Business profiles and branding | L-04; P1-03 |
| Automatic calculations | L-07; P1-05 |
| PDF generation | L-09, L-11 |
| Document management and history | L-12, L-13; P1-11, P1-12 |
| Subscription plans and usage limits | P1-04 |
| Modular extensibility | 04 §3 and ADR-01: the document-type field, versioned templates and calculation, and the shared finalise pipeline |

## 8. What the P0-Lite interface must not show

- pricing, plans, premium badges or upgrade prompts;
- GST rates, tax totals, place of supply or HSN/SAC fields (the optional GSTIN field on profiles is allowed);
- menu items or "coming soon" teasers for receipts, payment requests, bills, salary slips or any other deferred feature;
- testimonials, client logos or usage statistics;
- charts, revenue figures or analytics;
- any wording such as "GST-compliant", "certified", "tax-ready" or "AI-powered".

## 9. Scope change control

Any addition, removal or reprioritisation:

1. is recorded in 14 §6 with the requester, the reason and its effect on the plan in 10;
2. needs the developer's agreement for P0-Lite, and Heloavy's for P1 and P2;
3. is never made by Claude Code on its own initiative (15, rules 3 and 15).
