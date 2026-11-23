# 00 — Start Here

| | |
| --- | --- |
| Project | PS5 — Point of Sale (POS) and Smart Document Generation Platform |
| Working name | HIVE DOCS (provisional; needs Heloavy's approval, Q-21) |
| Team | Group 6 · HIVE Hub / Heloavy |
| Document set | Version 1.1 · 23 November 2026 · approved working baseline for P0-Lite |
| Demonstration | Wednesday 25 November 2026, afternoon (exact time: Q-15) |
| Capacity | One developer, assisted by Claude Code |
| Code status | No source code exists yet |

## 1. HIVE DOCS in one paragraph

HIVE DOCS helps owner-run service businesses in India produce correct, professional business documents without retyping their details, miscalculating totals or losing the copy they issued. A business enters its profile once, adds customers, prepares an invoice, lets the server calculate every amount, finalises the invoice under a unique number, and stores the exact PDF it issued, unchanged for as long as it is retained. Invoices come first; receipts, payment requests, bills and salary slips follow after the demonstration.

## 2. The problem we solve

Small businesses often prepare money documents in Word, Excel or as images shared on messaging apps. That causes:

- arithmetic mistakes in discounts and totals;
- duplicate or inconsistent invoice numbers;
- documents that change after they were sent, with no record of the original;
- no searchable history and no quick way to re-send a past document;
- unprofessional, inconsistent layouts.

These pain points come from the research phase and are hypotheses to confirm with pilot customers (Q-02, Q-09).

## 3. Target customers

The working target segment is **owner-operated Indian service businesses with roughly 1–20 staff**: freelancers, consultants, small agencies, IT and design studios. They issue invoices to business clients and currently use Word or spreadsheets.

Retail shops that need checkout, stock and barcode scanning are **not** the first segment. Whether "POS" in the project title means retail checkout is the most important open question (Q-01).

## 4. What we will deliver

| Phase | What it is | When |
| --- | --- | --- |
| **P0-Lite** | A working demonstration of the complete invoice workflow, built by one developer | Target: 25 November 2026 (aggressive, conditional plan; 10 §1) |
| P0 stretch | Small additions only if P0-Lite finishes early (second template, cloud deployment, automated browser test, full landing animation, amount in words) | 25 November 2026, if time allows |
| P1 | First usable client release: sign-up, users, logos, plans and limits, receipts, payment requests, GST after CA approval | After Heloavy confirms scope |
| P2 | Commercial expansion: salary slips, multiple businesses, recurring invoices and more | Driven by customer demand |

The full Revision 2 P0 (68–89 person-hours) is not achievable by one developer before 25 November, so P0-Lite is the honest, genuinely working subset (10 §1). Its own 16.5–22-hour estimate is aggressive and conditional: fixed checkpoints decide what is reduced or deferred, and completion of every P0-Lite item is not guaranteed.

The official requirements (bills, invoices, salary slips, payment requests, receipts, free and premium templates, subscriptions and usage limits) all remain in the product specification. Most are scheduled after the demonstration; `03_SCOPE_AND_FEATURES.md` gives the phase of each.

## 5. The 25 November demonstration (P0-Lite)

```mermaid
flowchart LR
  A[Landing page] --> B[ENTER THE SYSTEM]
  B --> C[Secure demo sign-in]
  C --> D[Business profile]
  D --> E[Create customer]
  E --> F[Invoice draft<br/>multiple lines, discounts]
  F --> G[Server calculates totals]
  G --> H[Draft PDF preview<br/>DRAFT watermark]
  H --> I[Finalise<br/>number + snapshot]
  I --> J[PDF rendered and stored<br/>privately with SHA-256]
  J --> K[Document history]
  K --> L[Reopen and download<br/>the same PDF]
```

This is the planned demonstration. Only stages that pass their checks by the code freeze are shown live; anything unfinished is announced as deferred (10 §6). Everything that is shown is real:

- sign-in checks an Argon2id password hash and creates a server-side session;
- data lives in PostgreSQL and survives restarts;
- the server recalculates every amount with Python `Decimal`;
- finalising allocates a unique number, freezes an immutable snapshot and writes an audit event in one transaction;
- the PDF is rendered by WeasyPrint from the snapshot and stored in private S3-compatible storage, with its SHA-256 recorded;
- history and downloads read the stored records, not mock data.

What the demonstration is **not**:

- not a tax invoice: every PDF says "SPECIMEN — demonstration document, not a tax invoice.";
- no GST calculation, no place of supply, no HSN/SAC codes;
- synthetic data only;
- one organization, one business and one demo account;
- one invoice template ("Classic"); a second template is a stretch goal.

## 6. Deferred from the demonstration

Self-service sign-up and multiple users · logo upload · subscription plans, usage limits and premium templates · GST calculations of any kind · receipts, payment requests, payment recording and bills · cancellation and credit notes · exports · salary slips · multiple businesses · recurring invoices · e-invoicing. Inventory, barcode scanning, retail checkout, AI features and a drag-and-drop template designer are not planned at all. Details and reasons: `03_SCOPE_AND_FEATURES.md`.

## 7. Decisions at a glance

1. **Modular monolith:** one FastAPI application with clear modules; no microservices.
2. **Stack:** React 18 + TypeScript + Vite SPA served by the same deployment; Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, psycopg 3, Alembic; PostgreSQL 16.
3. **Money:** Python `Decimal` with ROUND_HALF_UP, PostgreSQL `NUMERIC`, decimal strings in JSON; no floats.
4. **PDF:** Jinja2 (autoescape on) + WeasyPrint 70.x with a restricted URL fetcher, bundled fonts and no network access.
5. **Storage:** private S3-compatible bucket; SeaweedFS locally, DigitalOcean Spaces when deployed; never the container's own disk.
6. **Tenancy:** the organization comes from the session; every tenant-owned row carries `org_id`; composite foreign keys; other tenants' records return 404.
7. **Finalisation:** one database transaction allocates the number, freezes the snapshot and writes the audit event; an `Idempotency-Key` prevents duplicates; PDF failures retry without a new number.
8. **Honesty:** SPECIMEN label on every PDF; GST stays locked until a chartered accountant (CA) signs off.

## 8. How to navigate this package

| Reader | Suggested order |
| --- | --- |
| Teammates and presenters | 00 → 13 → `PROJECT_SUMMARY.md` → 03 → 14 |
| Developer | 00 → 03 → 10 → 04 → 06 → 07 → 09 → 08 → 11 → 12 → 05 → 15 |
| Claude Code | `CLAUDE.md` → 15 → every document, then the current milestone in 10 |
| Heloavy reviewer | 00 → 01 → 03 → 11 (demonstration checks) → 14 |

Identifiers used across documents:

| Prefix | Meaning | Defined in |
| --- | --- | --- |
| L-xx | P0-Lite feature | 03 |
| S-xx | Stretch feature | 03 |
| P1-xx, P2-xx | Later-phase feature | 03 |
| FR-xx, NFR-xx, BR-xx, US-xx | Requirement, rule, user story | 02 |
| E-xx | API endpoint | 07 |
| M0–M8, CP1–CP5, R1–R6 | Milestone, checkpoint, scope-reduction rule | 10 |
| DC-xx | Mandatory demonstration check | 11 |
| Q-xx, A-xx, C-xx | Open question, assumption, upstream contradiction | 14 |
| ADR-xx | Architecture decision record | 04 |
| RK-xx | Project risk | 01 |
| V-xx | Item to verify in the real development environment | 05 |
| UT-, DB-, IT-, FE-, E2E-, AT- | Automated, manual and deferred tests | 11 |

## 9. How teammates should describe the project

| Say | Do not say |
| --- | --- |
| "A working demonstration of the invoice workflow, built to production standards for correctness and data safety." | "A complete POS system." |
| "The PDF is marked SPECIMEN because GST rules need a chartered accountant's approval first." | "GST-compliant" or "tax-ready". |
| "Receipts, payment requests and salary slips are planned after the demonstration." | That deferred features already work. |
| "Built by one developer with an AI coding assistant, in two days." | "AI-powered" (the product has no AI features). |
| "HIVE DOCS is a working name awaiting Heloavy's approval." | That the name is final. |

## 10. How Claude Code should use these documents

- `CLAUDE.md` sends the agent to `15_CLAUDE_CODE_INSTRUCTIONS.md`, whose rules are binding.
- Scope comes from 03, milestones from 10, contracts from 06 (schema), 07 (API) and 09 (financial rules), screens from 08, tests from 11 and safeguards from 12.
- If two documents disagree, the agent stops and asks; it never picks one silently. Known upstream contradictions are listed in 14 §4.

## 11. Status and dates

| Date (IST) | Event |
| --- | --- |
| 23 Nov 2026 | Documentation package 1.1 approved as the working baseline; development starts |
| 24 Nov 2026 | Core workflow built and verified (checkpoints CP2–CP4) |
| 25 Nov 2026, 11:00 | Code freeze, then rehearsal |
| 25 Nov 2026, afternoon | Demonstration to HIVE Hub / Heloavy |
