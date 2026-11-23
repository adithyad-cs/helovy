# 01 — Project Charter

| | |
| --- | --- |
| Document | Project charter · version 1.1 · 23 November 2026 |
| Status | Frozen baseline for P0-Lite; changes go through 14 §6 (change control) |
| Read with | 00 (overview), 03 (scope), 10 (plan), 14 (questions and assumptions) |

## 1. Project identity

| Item | Value |
| --- | --- |
| Project ID | PS5 |
| Official title | Point of Sale (POS) and Smart Document Generation Platform |
| Working product name | HIVE DOCS (provisional; needs Heloavy's approval, Q-21) |
| Team | Group 6 |
| Organization | HIVE Hub / Heloavy (problem owner, client and evaluator) |
| Delivery team | One developer, assisted by Claude Code |
| Demonstration | Wednesday 25 November 2026, afternoon (exact time: Q-15) |
| Code status on 23 November 2026 | No source code exists; research and architecture documents are complete |

## 2. Background

HIVE Hub / Heloavy issued problem statement PS5. The master documentation prompt restates its official requirements as:

- bills, invoices, salary slips, payment requests and receipts;
- free and premium templates;
- business profiles and branding;
- automatic calculations;
- PDF generation;
- document management and history;
- subscription plans and usage limits;
- modular extensibility.

The project went through four documentation stages:

1. **Original blueprint:** market, regulatory and technical research, with a proposed architecture.
2. **Revision 2:** corrections A–F after comparison with an independent Perplexity report: schema, e-invoicing threshold, separating demonstration tax from certified GST, persistent storage, atomic issuance and a realistic schedule.
3. **Revision 2.1:** errata and 20 frozen decisions (health paths, WeasyPrint pin, hosting, storage, CSRF design).
4. **This package:** the final specification, re-scoped for one developer and a two-day deadline (P0-Lite).

**Research provenance.** The Perplexity, Grok and Gemini research reports were independently reviewed, their relevant recommendations were audited, and the accepted decisions are consolidated in this package. The original full reports are not bundled in the documentation ZIP.

Revision 2 remains the technical baseline. This package narrows what gets built first; it does not change the architecture.

## 3. Problem statement

Small Indian businesses often prepare invoices and similar documents in word processors, spreadsheets or messaging apps. The research identified these recurring problems, which still need confirmation with pilot customers (Q-02, Q-09):

1. Totals and discounts are calculated by hand or in fragile spreadsheet formulas, so errors reach customers.
2. Numbering is manual, so numbers are skipped, duplicated or inconsistent.
3. An issued document can be edited and re-sent, and no trustworthy record remains of what the customer actually received.
4. Past documents are scattered across folders, email and chat, so finding and re-sending one is slow.
5. Layouts vary from document to document and look unprofessional.

The official PS5 title includes "Point of Sale". The research found no requirement for checkout hardware, stock or barcode scanning in the restated requirements. The meaning of "POS" is the most important open question (Q-01).

## 4. Product vision

> A small business enters its details once and from then on issues correct, professional documents in minutes. Every issued document keeps its number, its amounts and its exact PDF unchanged for as long as it is retained.

Immutability and retention are separate. Finalised documents remain immutable while they are retained; how long they are retained, and how they are deleted, follows the retention policy Heloavy approves and the applicable legal requirements (Q-18, 12 §16).

The guiding principles are:

- **Correct before clever:** the server calculates every amount with exact decimal arithmetic.
- **Issued means frozen:** finalised documents are immutable snapshots with a stored, hash-verified PDF, for as long as they are retained.
- **Honest by default:** nothing is labelled as compliant, certified or complete unless it is.
- **Modular growth:** each new document type (receipts, payment requests, bills, salary slips) reuses the same draft, finalise, snapshot and PDF pipeline.

## 5. Objectives

### 5.1 Demonstration objectives (25 November 2026)

| ID | Objective | Measured by |
| --- | --- | --- |
| O-1 | Show the complete invoice workflow, from landing page to re-download, working against real persistent data | DC-01 to DC-20 (11 §3) pass on the demonstration machine |
| O-2 | Prove that calculations are correct and documents keep their integrity | The fixtures give ₹1,800.00, ₹900.00 and ₹2,700.00; the downloaded file's SHA-256 matches the stored hash |
| O-3 | Prove secure sign-in and tenant isolation | IT-AUTH and IT-TEN suites pass on the frozen build |
| O-4 | Present the project honestly | Every PDF carries the SPECIMEN text; deferred features are named as deferred |
| O-5 | Hand over a specification and codebase that can grow into the product | This package; PROGRESS.md; the tagged demonstration build |

### 5.2 Product objectives (after the demonstration; targets need Heloavy's agreement, Q-12)

| ID | Objective |
| --- | --- |
| O-6 | Run a pilot of the first usable release (P1) with 3–5 businesses (Q-09) |
| O-7 | Add the official document types in the order Heloavy confirms (Q-06) |
| O-8 | Offer GST documents only after a chartered accountant (CA) approves the rules (Q-03) |
| O-9 | Complete the production hardening (P1-14) before any real customer data is stored |

## 6. Stakeholders

| Stakeholder | Role | Decides or approves |
| --- | --- | --- |
| Heloavy | Problem owner and client | Scope, product name, hosting, pricing, acceptance (Q-01 to Q-12) |
| HIVE Hub | Programme and evaluation | Demonstration format and logistics (Q-14, Q-15) |
| Group 6 teammates | Communication, presentation, demonstration-day support | Presentation material that stays within 13 (team handoff) |
| Developer (one person) | Builds P0-Lite and owns technical decisions inside the frozen baseline | Implementation details that 04–09 leave open |
| Claude Code | Implementation assistant | Nothing; it follows 15 and asks before changing a decision |
| Chartered accountant (not yet identified) | Tax and statutory review | GST rules, rounding, numbering, retention (Q-03, Q-16, Q-17, Q-18) |
| Pilot businesses (not yet identified) | Validate problems and the P1 release | Feedback only |
| Document recipients | The business's customers, who receive PDFs | Nothing; a clear and correct document is what they need |

## 7. Target customers

| Segment | Status | Why |
| --- | --- | --- |
| Owner-run Indian service businesses with about 1–20 staff (freelancers, consultants, agencies, studios) | **Primary working assumption** (A-01, Q-02) | Invoice-heavy, low tooling, no inventory needs, match the P0-Lite workflow |
| Small traders who need simple bills or receipts | Possible later segment | Depends on what "bills" means (Q-13) and on the POS decision (Q-01) |
| Businesses that issue salary slips | Later (P2-01) | Payroll data needs a separate privacy module and statutory input (Q-22) |
| Retail counters needing checkout, stock and barcode scanning | **Not targeted** | Excluded from the restated scope; would be a different product (Q-01) |
| Businesses above the e-invoicing threshold | Not targeted until P2-06 | Needs Invoice Registration Portal (IRP) integration and CA approval |

## 8. Business value

| For | Value | Delivered by |
| --- | --- | --- |
| Business owners | Fewer calculation mistakes; consistent numbering; a professional look; any past document found in seconds | L-07, L-10, L-08, L-12 |
| Their customers | Clear, consistent PDFs whose figures add up | L-07, L-08 |
| Heloavy | A foundation that is already structured for real deployment: tenancy, integrity, audit, modular document types | 04 architecture |
| Heloavy (commercial) | A path to free and premium templates and plans with usage limits | P1-04, once pricing is decided (Q-08) |

No market-size or revenue figures are claimed: none have been validated.

## 9. Success criteria

### 9.1 Demonstration

1. All 20 mandatory demonstration checks (11 §3) pass on the demonstration machine after the code freeze at 11:00 on 25 November. Any check that fails is removed from the live script and announced as deferred.
2. The presenter completes the workflow (sign-in → issued PDF → re-download) live in under five minutes.
3. Nothing shown is mocked; every screen reads and writes the real database and storage.
4. The audience hears clearly what is deferred and why.

### 9.2 Product (proposed; to be agreed with Heloavy, Q-12)

1. Zero known calculation defects across the fixture suites and pilot usage.
2. Zero duplicate or reused document numbers.
3. Zero cross-tenant data exposure, verified by tests on every release.
4. Pilot users can issue their first invoice within 10 minutes of signing up (P1).

## 10. Constraints

| Constraint | Consequence |
| --- | --- |
| One developer, about 19 focused hours before the freeze | Only P0-Lite is planned; the full Revision 2 P0 (68–89 person-hours) is **not achievable** (10 §1). P0-Lite's own 16.5–22-hour estimate is aggressive and conditional: checkpoints decide what is reduced or deferred, and its full completion is not guaranteed |
| Fixed demonstration date | Scope reduces when checkpoints slip; hours do not grow (10 §6) |
| Approved technology stack frozen | No new frameworks, services or architecture changes without approval (15) |
| No GST in P0-Lite | Documents are titled "Invoice", carry the SPECIMEN text and calculate no tax |
| Quality floor | Calculation correctness, tenant isolation, finalisation integrity and data and PDF persistence are never weakened to meet the deadline; unfinished work is deferred, not faked |
| Synthetic data only | No real personal or business data until production hardening is complete |
| Hosting not yet approved | The local Docker stack is the guaranteed demonstration runtime; cloud deployment is a stretch goal (S-02) |

## 11. Assumptions

The full list, with the question each depends on, is in 14 §3. The most important are:

- **A-01:** the primary segment is owner-run service businesses.
- **A-02:** "POS" is initially satisfied by billing documents, not retail checkout.
- **A-03:** a local Docker demonstration is acceptable.
- **A-04:** synthetic data only.
- **A-07:** no tax in P0-Lite.
- **A-13:** the P1 composition.
- **A-18:** one developer with about 19 focused hours.

## 12. Risks

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- | --- |
| RK-01 | Schedule overrun: the aggressive, conditional estimate is 16.5–22 h against about 19 h available | High | High | Risk-first order, checkpoints CP1–CP5, reduction rules R1–R6, fixed stop times (10) | Developer |
| RK-02 | WeasyPrint system libraries or fonts fail inside the container | Medium | High | Render a test PDF in the container in M0, before any feature work | Developer |
| RK-03 | SeaweedFS behaves differently from the cloud S3 service (authentication, versioning) | Medium | Medium | SeaweedFS verification gate in M0: pinned image, bucket initialization, authenticated PUT/GET, anonymous access refused (05 §14.1); one S3 code path; IT-PDF-01 checks the bucket is private | Developer |
| RK-04 | Heloavy expected retail POS features | Medium | High | Ask Q-01 early; describe the scope honestly (13) | Team lead |
| RK-05 | Demonstration-day machine, Docker or network failure | Medium | High | Fully local stack; backup machine with a database dump; labelled screen recording; pre-exported PDFs (10 §7) | Team |
| RK-06 | Audience reads the specimen as a GST tax invoice | Low | High | SPECIMEN text on every PDF; title "Invoice"; presentation rules in 00 §9 | Presenter |
| RK-07 | Duplicate numbers under concurrent finalisation | Low | High | Counter row updated in the finalising transaction; unique constraints; IT-FIN-04 | Developer |
| RK-08 | Cross-tenant data exposure | Low | High | Organization taken from the session; composite foreign keys; IT-TEN suite | Developer |
| RK-09 | AI-generated code drifts from the specification | Medium | Medium | Binding rules in 15; one milestone per session; tests at every milestone; review before commit | Developer |
| RK-10 | Fatigue errors from late-night work | Medium | Medium | Stop at 22:30 on Monday and 21:00 on Tuesday; reduce scope instead | Developer |
| RK-11 | Evaluators require a public cloud URL | Medium | Medium | Ask Q-14 now; S-02 is time-boxed to 90 minutes | Team lead |

RK-12 was withdrawn in version 1.1 and is not reused.
