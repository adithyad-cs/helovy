# HIVE DOCS (PS5): Project Summary

**For HIVE Hub teammates and reviewers · version 1.1 · 23 November 2026**

PS5, "Point of Sale (POS) and Smart Document Generation Platform", is being built by Group 6 for HIVE Hub / Heloavy under the working name **HIVE DOCS** (provisional; needs Heloavy's approval). It is a web application that helps small Indian businesses produce correct, professional business documents: details are entered once, every amount is calculated on the server, each issued document gets one unique number, and the exact PDF that was issued is stored privately and stays unchanged for as long as it is retained. How long documents are retained, and how they are deleted, will follow the policy Heloavy approves and the applicable legal requirements.

## Status at a glance

| Item | Status |
| --- | --- |
| Research and architecture | Complete: original blueprint, Revision 2, Revision 2.1 errata, and independent reviews of the Perplexity, Grok and Gemini research reports (accepted recommendations consolidated here; the original reports are not bundled in the ZIP) |
| Documentation package | Version 1.1, approved as the working baseline (16 documents + README, summary and consistency audit) |
| Source code | Not started; development begins 23 November with one developer and Claude Code |
| Demonstration | Wednesday 25 November 2026, afternoon. Code freeze at 11:00 the same day |
| Capacity reality | The full Revision 2 P0 (68–89 person-hours) is **not achievable** by one developer in the time. A focused, genuinely working **P0-Lite** is the target instead. Its 16.5–22-hour estimate against about 19 focused hours is **aggressive and conditional**: completion of every P0-Lite item is not guaranteed, and fixed checkpoints decide what is reduced or deferred |

## The problem

Small businesses often make invoices in Word, Excel or WhatsApp. That leads to calculation mistakes, skipped or duplicate numbers, documents edited after they were sent, scattered records and inconsistent layouts. These problems come from the research and still need confirmation with pilot customers.

**Working target customer:** owner-run Indian service businesses with about 1–20 staff (freelancers, consultants, studios, agencies). Retail checkout, stock and barcode scanning are not the first target. What "POS" should mean is the most important open question for Heloavy.

## What the 25 November demonstration aims to show (P0-Lite)

Landing page → ENTER THE SYSTEM → secure sign-in → business profile → add a customer → create an invoice with several lines, quantities, prices and percent or fixed discounts → server-calculated totals → watermarked PDF preview → finalise (unique number + frozen snapshot + audit record) → real PDF stored privately with a SHA-256 fingerprint → history → reopen and download the same PDF.

Only stages that pass their checks by the code freeze are shown live; anything unfinished is described as deferred, never mocked. Everything shown is real:

- a real password check (Argon2id) and a server session;
- a PostgreSQL database that survives restarts;
- exact `Decimal` calculations on the server;
- an atomic, concurrency-safe finalisation transaction;
- a WeasyPrint PDF rendered from the frozen snapshot, stored privately and checked against its fingerprint on every download;
- organization-level data isolation.

**Honest limits:**

- every PDF says "SPECIMEN — demonstration document, not a tax invoice.";
- no GST calculations;
- one business, one owner account and one invoice template;
- synthetic data only;
- runs locally in Docker on a laptop (a cloud deployment is only a stretch goal);
- the retention period is not yet defined: it will follow Heloavy's approved policy and the applicable legal requirements.

## Technology (frozen)

| Layer | Choice |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, React Router, TanStack Query, React Hook Form, Zod, Tailwind CSS, Radix UI |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, psycopg 3, Alembic: one modular monolith |
| Database | PostgreSQL 16 (money as NUMERIC, never floats) |
| PDF | Jinja2 (autoescape) + WeasyPrint 70.x, with bundled Noto fonts, a restricted fetcher and no network |
| Storage | Private S3-compatible storage: SeaweedFS locally (retained by team decision; its pinned image, bucket initialization and authenticated PUT/GET must pass M0 verification), DigitalOcean Spaces in the cloud reference design |
| Security | Argon2id, server-side sessions, HttpOnly/Secure/SameSite cookies, CSRF tokens, organization-scoped access |
| Runtime | Docker; environment-based configuration; no secrets in source control |

## Engineering guarantees

1. **Correct money:** the server recalculates every amount with `Decimal` and ROUND_HALF_UP (to be validated by a chartered accountant). The fixture invoice gives ₹1,800.00 + ₹900.00 = ₹2,700.00.
2. **One number, exactly once:** numbering happens inside the finalisation transaction, with idempotency keys against double clicks and retries.
3. **Issued means frozen:** finalised invoices are immutable snapshots, protected by database triggers, for as long as they are retained.
4. **The same PDF every time:** the PDF is stored privately and its SHA-256 is verified before every download. A failed render is retried without a new number.
5. **Private by design:** the organization always comes from the session; other tenants' records return "not found"; composite database keys enforce isolation.

## Roadmap after the demonstration

- **P1, first usable client release (composition to be confirmed by Heloavy):**
  - sign-up and accounts;
  - receipts and payment requests;
  - bills (once defined);
  - subscription plans, usage limits and premium templates;
  - cancellation and credit notes;
  - logo upload;
  - production security hardening;
  - GST only after written chartered-accountant approval.
- **P2, commercial expansion:** salary slips (with a payroll privacy module), multiple businesses, recurring invoices, email or WhatsApp sending, simple reports, e-invoicing for eligible businesses.
- **Not planned:** inventory, barcode scanning, retail checkout, payment gateway in the demonstration, AI features, drag-and-drop template designer, complex analytics, microservices.

## The plan for one developer

| Milestone | Scope |
| --- | --- |
| M0 | Foundation, plus risk spikes for WeasyPrint and storage |
| M1 | Authentication |
| M2 | Business profile and customers |
| M3 | Calculations and drafts |
| M4 | Template and preview |
| M5 | Finalisation and PDF storage |
| M6 | History |
| M7 | Landing page and polish |
| M8 | Verification and freeze |

- **Checkpoints:** Monday 22:30, Tuesday 13:00, 17:30 and 21:00, Wednesday 11:00 (freeze).
- **When behind:** at each checkpoint, written reduction rules remove polish, convenience or scope first. Working hours do not grow. Calculation correctness, tenant isolation, finalisation integrity and data and PDF persistence are never weakened: anything that cannot be finished safely is deferred and left out of the live demonstration.
- **Fallbacks:** a backup laptop, a labelled screen recording and pre-exported PDFs.

## Questions for Heloavy (most urgent first)

1. **Q-14 / Q-15:** Is a local laptop demonstration acceptable, or is a public URL required? What are the exact time, format, screen and internet arrangements?
2. **Q-01:** What does "POS" mean for this product: billing documents, or retail checkout?
3. **Q-03:** Are GST tax invoices required, by when, and which chartered accountant will approve the rules?
4. **Q-06 / Q-13:** Which document types come first after the demonstration, and what exactly is a "bill"?
5. **Q-08:** What are the subscription plans, prices and usage limits?
6. **Q-04 / Q-05:** Who owns the hosting, and which database and storage providers are acceptable?
7. **Q-12:** What are the acceptance criteria, for the demonstration and for the first release?
8. **Q-21:** Is the name "HIVE DOCS" approved?

## Known deviations, reported rather than silently decided

- **MinIO → SeaweedFS** for local storage: carried over from Revision 2.1, because MinIO's community images are no longer reliably maintained (verify). Now retained by team decision, subject to the M0 verification gate.
- **Deferred from the demonstration:** subscriptions and usage limits, premium templates and salary slips, all official requirements. They remain in the product plan.
- **Revision 2.1's reserved database columns** are left out of the P0-Lite schema and will be added in P1.
- **Cloud deployment** moves from the demonstration path to a stretch goal.

## Research provenance

The Perplexity, Grok and Gemini research reports were independently reviewed, their relevant recommendations were audited, and the accepted decisions are consolidated in this package. The original full reports are not bundled in the ZIP.

## Where to read more

All documents are in `docs/`:

- `00_START_HERE.md` (overview)
- `13_TEAM_HANDOFF.md` (plain-language guide and talking points)
- `03_SCOPE_AND_FEATURES.md` (what is in and out)
- `10_IMPLEMENTATION_PLAN.md` (the plan)
- `14_OPEN_QUESTIONS_AND_ASSUMPTIONS.md` (questions and contradictions)
