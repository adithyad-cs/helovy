# 14 — Open Questions, Assumptions and Contradictions

| | |
| --- | --- |
| Document | Decision register · version 1.2 · 23 November 2026 |
| Use | Ask Heloavy the questions in §2 in priority order. Until a question is answered, its working assumption (§3) applies. §4 lists contradictions between the source materials; none was resolved silently |

## 1. How to use this register

- **Q-xx** is a question for an external party (Heloavy, HIVE Hub, a chartered accountant, legal) or for the team.
- **A-xx** is the assumption the documentation and the build follow until the matching question is answered.
- **C-xx** is a contradiction between the official statement, Revision 2 or 2.1, the research reports and the master documentation prompt, with how it is handled.
- The **Blocks** column says whether an unanswered question blocks the **demonstration** (25 November) or only **production**.
- **Withdrawn in version 1.1 (identifiers not reused):** Q-24 and C-02 here, and RK-12 in 01. They rested on an incorrect statement about research provenance, corrected in §7.

## 2. Questions (priority order)

| ID | Question | Why it matters | Working assumption | Who answers | Blocks |
| --- | --- | --- | --- | --- | --- |
| Q-01 | **What does "Point of Sale (POS)" mean for this product?** Is retail checkout (counter billing, cash drawer, receipt printer, stock, barcode) expected, or are billing documents for service businesses acceptable as the first product? If POS-style bills are wanted, please confirm the optional Quick Counter Bill (P1-16) in writing | Decides whether this is a document platform or a retail system, two very different products | A-02: billing documents first; no retail checkout | Heloavy | Production (the demonstration follows A-02 and says so) |
| Q-02 | **Who are the target customers?** Is it owner-run Indian service businesses with about 1–20 staff? Which pain points matter most? | Shapes features, templates, pricing and pilots | A-01 | Heloavy | Production |
| Q-03 | **Are GST-certified (tax-invoice) documents required, and by when?** Which chartered accountant will review the tax rules, and what form will the approval take? | GST errors create tax liability; certified mode stays locked without approval (mandatory decision 18) | A-07: no tax in P0-Lite; GST in P1-05 only after written CA approval | Heloavy + CA | Production |
| Q-04 | **Who owns the hosting** (cloud account, billing, administrative access)? Is there a budget? | Determines deployment, cost and responsibility | A-15: DigitalOcean BLR1 as the reference design, not yet provisioned | Heloavy | Production (the demonstration runs locally, A-03) |
| Q-05 | **Which database and storage providers are acceptable?** Is managed PostgreSQL plus DigitalOcean Spaces acceptable? Must data stay in India? Is SSE-C-only encryption acceptable, or is application-level encryption required? | Data residency, encryption and lock-in | A-15; synthetic data only until resolved | Heloavy | Production |
| Q-06 | **Which document types are required in the first client release (P1)?** In what order? Can salary slips wait for P2? | Defines P1; salary slips need a privacy module | A-13 (P1 composition), A-14 (salary slips in P2) | Heloavy | Production |
| Q-07 | **Who owns and designs templates?** Who decides what counts as premium, and who holds the template IP? | Premium templates and branding | Templates are designed in-house as versioned code; there is no user template designer | Heloavy | Production |
| Q-08 | **What are the pricing and subscription limits?** Plans, prices, limits (for example documents per month), the free tier, and which payment provider handles subscriptions | P1-04 design; no checkout is built until decided | No plans, limits or checkout in P0-Lite | Heloavy | Production |
| Q-09 | **Will Heloavy provide pilot customers?** Who are they, how many, and when? | Validates the problem and the P1 scope | 3–5 pilot businesses after P1 (O-6) | Heloavy | Production |
| Q-10 | **Who maintains the product after handover?** Hosting operations, updates, security patches, support hours | Long-term viability and the security patching duty | Not defined; the team maintains it until a handover is agreed | Heloavy + team | Production |
| Q-11 | **What are the production security and privacy requirements?** MFA, audits, penetration test, backup objectives (RPO/RTO), the DPDP compliance owner, incident reporting | Scope and cost of P1-14 | The 12 §14 checklist as a proposal | Heloavy (+ legal) | Production |
| Q-12 | **What are the client acceptance criteria?** What will be judged on 25 November (working functionality, design, code, documentation), and what defines acceptance of P1? | Focuses demonstration preparation and the P1 definition of done | A-17: the demonstration is judged on genuinely working functionality and honesty | Heloavy, HIVE Hub | Demonstration (focus) and production |
| Q-13 | What exactly is a "bill" in the official requirements: a supplier bill received, a bill of supply, or a simple counter bill? | P1-09 cannot be designed without it | Undefined; P1-09 waits | Heloavy | Production |
| Q-14 | **Is a local Docker demonstration on our laptop acceptable, or is a public cloud URL required?** | If a URL is required, S-02 becomes MUST and another feature must be deferred | A-03: local is acceptable | Heloavy, HIVE Hub | **Demonstration** |
| Q-15 | Demonstration logistics: exact time, duration, in person or online, screen and projector, internet availability | Rehearsal, timing, equipment | Afternoon of 25 November; about 10 minutes including 5 minutes of live flow; no internet needed | HIVE Hub | **Demonstration** |
| Q-16 | Is the invoice number format `INV/YY-YY/NNNNN` (per business, per financial year) acceptable? | Numbers are permanent once issued | A-09 | Heloavy + CA | Production (the demonstration uses A-09) |
| Q-17 | Should grand totals be rounded to the nearest rupee? | Changes calculation output; needs a new `calc_version` | A-10: no round-off | CA | Production |
| Q-18 | What are the record retention and deletion policies (documents, logs, audit events)? | Statutory retention versus privacy duties | 12 §16; GST records reportedly 72 months (verify) | CA + legal | Production |
| Q-19 | Who owns the code and IP, and where should the repository live (for example a GitHub organization)? | Access, licensing, continuity | The team's repository until told otherwise | Heloavy | Production |
| Q-20 | Product branding: logo, colours, visual identity | The landing page and templates use provisional tokens (08 §4) | Provisional design | Heloavy | Neither |
| Q-21 | Is the name "HIVE DOCS" approved? If not, what name should be used? | Branding everywhere | Working name, labelled provisional | Heloavy | Neither |
| Q-22 | Salary slips: required fields, statutory components (PF, ESI, professional tax, TDS), approver, privacy expectations | P2-01 design and legal risk | Not built until answered | Heloavy + CA or payroll expert | Production |
| Q-23 | Are Hindi or regional-language documents or interfaces needed? | P2-07; fonts are already bundled | English only | Heloavy | Production |
| Q-25 | **Answered 23 November 2026:** SeaweedFS is retained as the local S3-compatible server. (The master prompt named MinIO; Revision 2.1 replaced it after finding MinIO's community container images no longer reliably maintained; verify current status.) Its configured image and version, bucket initialization and authenticated PUT/GET must pass the M0 verification gate (05 §14.1) | A broken local storage setup would block M0 and M5; the code only speaks the S3 API | A-16 | Team (Heloavy informed) | Neither (the M0 gate decides) |
| Q-26 | Production domain name and transactional email provider (for sign-up and verification) | P1-01; problem `type` URIs use `hive-docs.invalid` until then (07 §1.5) | Not decided | Heloavy | Production |

## 3. Working assumptions

| ID | Assumption | Linked question | If wrong |
| --- | --- | --- | --- |
| A-01 | The primary segment is owner-run Indian service businesses with about 1–20 staff | Q-02 | Personas, templates and P1 priorities change |
| A-02 | "POS" is initially satisfied by billing documents, not retail checkout | Q-01 | Retail features need a new plan; P1-16 at most in the near term |
| A-03 | A local Docker demonstration on the presenter's laptop is acceptable | Q-14 | S-02 becomes MUST, and a MUST feature must be deferred to make room |
| A-04 | Only synthetic data is used until production hardening is complete | Q-11 | — (non-negotiable for safety) |
| A-05 | P0-Lite has one organization, one business and one owner account (plus a second account only for the isolation check) | — | — |
| A-06 | INR only; customers are in India | Q-02 | Currency and address model changes |
| A-07 | No tax in P0-Lite; PDFs are titled "Invoice" with the SPECIMEN statement | Q-03 | — (mandatory decision 17) |
| A-08 | The issue date is the finalisation date in Asia/Kolkata; no backdating | Q-16 | Numbering and date rules change (CA) |
| A-09 | The number format is `INV/YY-YY/NNNNN` per business and financial year | Q-16 | A new format for future documents only |
| A-10 | No rupee round-off | Q-17 | A new `calc_version` |
| A-11 | ROUND_HALF_UP per line, then sum | Q-03 | A new `calc_version` |
| A-12 | A grand total must be above ₹0.00 to finalise | Q-12 | A one-line rule change |
| A-13 | P1 = sign-up and accounts, receipts, payment requests, bills (once defined), plans, limits and premium templates, cancellation and credit notes, logo, hardening; GST after CA approval | Q-06 | The P1 plan changes |
| A-14 | Salary slips belong in P2 (they need a payroll privacy module) | Q-06, Q-22 | Earlier privacy work is required |
| A-15 | DigitalOcean BLR1 (App Platform, managed PostgreSQL 16, Spaces) is the reference cloud design | Q-04, Q-05 | Deployment documents change; the code is unaffected (S3 API, PostgreSQL) |
| A-16 | SeaweedFS is the local S3-compatible server (team decision, 23 November 2026), subject to the M0 verification gate (05 §14.1) | Q-25 | If the gate fails, stop and decide (15 §7); the code is unaffected because it only uses the S3 API |
| A-17 | Demonstration evaluation focuses on genuinely working functionality and honest presentation | Q-12 | Preparation emphasis changes |
| A-18 | One developer with about 19 focused hours before the freeze; Claude Code available throughout | — | The plan (10) is re-baselined |
| A-19 | The demonstration browser is current desktop Chrome; mobile is checked through emulation and one phone | Q-15 | Extra browser checks |
| A-20 | Demonstration data leaves GSTIN fields empty and uses `.invalid` emails | — | — |

## 4. Upstream contradictions and how they are handled

| ID | Contradiction | Sources | Handling | Status |
| --- | --- | --- | --- | --- |
| C-01 | Local object storage: **MinIO** versus **SeaweedFS** | The master prompt §4 (MinIO); the Revision 2.1 errata (SeaweedFS, concrete defect) | SeaweedFS retained (ADR-13). The prompt itself freezes the stack "unless Revision 2 identifies a concrete defect", and Revision 2 ranks above the prompt's own decisions | **Resolved** by team decision on 23 November 2026, subject to the M0 verification gate (05 §14.1) |
| C-03 | Revision 2 P0 (two free templates, demonstration GST mode, cloud deployment as MUST, reserved plan and usage structures, 68–89 h) versus P0-Lite | Revision 2 and 2.1 versus the master prompt §3 | The prompt states that Revision 2 is authoritative "subject to the final implementation scope". The items move to S-01, P1-05, S-02 and P1-04; none are removed | Resolved by the source hierarchy |
| C-04 | Official requirements for subscription plans, usage limits and premium templates are not in the demonstration | The official statement versus the P0-Lite restrictions | Deferred to P1-04, not removed; stated openly in the demonstration | **Open for Heloavy's acceptance** (Q-08, Q-12) |
| C-05 | Revision 2.1 froze a list of columns and tables reserved in the first migration (GST, logo, archive, cancelled status, plans and usage) | Revision 2.1 frozen decisions versus the prompt ("do not create unnecessary database tables") | P0-Lite migrations leave them out; P1 migrations add them (06 §13). **A deliberate change to a frozen Revision 2.1 decision** | Resolved toward the prompt; flagged |
| C-06 | The deployment section lists "Managed PostgreSQL", but the guaranteed demonstration uses PostgreSQL in Docker | The master prompt §4 versus the solo plan | Managed PostgreSQL applies to deployed environments (S-02, P1); the local runtime is the demonstration choice (ADR-12) | Resolved; needs acceptance (Q-14) |
| C-07 | Revision 2.1 treated the DigitalOcean deployment as part of the demonstration path; P0-Lite makes it stretch (S-02, 90-minute time-box) | Revision 2.1 §4 hosting versus 10 §8 | Local runtime is MUST; cloud is stretch | **Open** (Q-14) |
| C-08 | Salary slips are an official requirement but scheduled for P2 | The official statement versus A-14 | Kept in the specification as P2-01 with privacy controls | **Open** (Q-06, Q-22) |
| C-09 | The title says "Point of Sale", but the scope excludes checkout, inventory and barcode scanning | The official title versus the restated requirements and the prompt's restrictions | Documented as Q-01; P1-16 only with written confirmation | **Open** (Q-01) |
| C-10 | The approved stack lists no test tooling; the documents add pytest, hypothesis, httpx, ruff, mypy and ESLint (and Playwright as stretch) | The master prompt §4 versus 05 §2 and 11 | Treated as development tooling, not product stack. No frontend unit-test runner is added because the SPA has no business logic | Resolved; flagged |
| C-11 | Revision 2.1 listed one `DATABASE_URL`, but its frozen rule that the app role can only SELECT and INSERT snapshots and audit events needs a separate owner role for migrations | Revision 2.1 errata versus 06 §11 | Added `MIGRATION_DATABASE_URL`, plus `APP_ENV`, `CLIENT_IP_HEADER`, `S3_ADDRESSING_STYLE` and `LOG_LEVEL` (05 §9) | Resolved as clarification; flagged |
| C-12 | Revision 2.1 says the template `content_sha256` is checked at startup without saying where the expected value lives | Revision 2.1 versus 06 §3.7 and 09 §11 | The expected hash lives in the code registry (`rendering/registry.py`), not in the `templates` table, so it changes only with the files | Resolved as clarification; flagged |

## 5. Decisions that need Heloavy's approval

1. The product name (Q-21) and branding (Q-20).
2. The meaning of POS and the optional Quick Counter Bill (Q-01).
3. The target segment and pilot customers (Q-02, Q-09).
4. The P1 composition and order, including salary-slip timing and the meaning of "bills" (Q-06, Q-13, Q-22).
5. Pricing, plans, limits and the payment provider (Q-08).
6. Hosting ownership, providers, data residency and encryption (Q-04, Q-05).
7. Engaging a CA and the approval process for GST, rounding, numbering and retention (Q-03, Q-16, Q-17, Q-18).
8. The demonstration format (Q-14) and acceptance criteria (Q-12).
9. Maintenance responsibilities and production security requirements (Q-10, Q-11).
10. Template ownership (Q-07); code and IP ownership (Q-19).
11. Acceptance of the deliberate deviations C-04, C-05, C-07 and C-08.

## 6. Change control and decision log

**Process for any change** to scope, stack, architecture or a frozen decision:

1. Write an entry below: date, change, reason, requester, effect on plan and documents.
2. Get approval: the developer for P0-Lite internals; Heloavy for scope, P1 and P2.
3. Update every affected document in the same commit and re-run the consistency audit.

Claude Code never makes such changes on its own (15, rules 3, 4 and 15).

| # | Date | Change | Reason | Approved by | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | 23 Nov 2026 | Scope re-baselined from the Revision 2 P0 to the solo-developer P0-Lite | One developer; about 19 h available | Team, through the master documentation prompt | Accepted |
| 2 | 23 Nov 2026 | Local storage MinIO → SeaweedFS (carried over from Revision 2.1) | MinIO community images no longer reliable (verify) | Team | Accepted (decided in #8) |
| 3 | 23 Nov 2026 | Reserved P1 columns and tables removed from the P0-Lite migrations | "No unnecessary tables" | Team | Accepted; flagged (C-05) |
| 4 | 23 Nov 2026 | Cloud deployment moved from the demonstration path to stretch (S-02) | Solo capacity; demonstration risk | Team | Pending Heloavy (Q-14) |
| 5 | 23 Nov 2026 | Research provenance corrected: the Perplexity, Grok and Gemini reports were independently reviewed and the accepted decisions consolidated; Q-24, C-02 and RK-12 withdrawn | Independent review of version 1.0 | Team | Accepted |
| 6 | 23 Nov 2026 | Retention wording: finalised documents are immutable while retained; retention duration and deletion follow the Heloavy-approved policy and the law | Independent review of version 1.0 | Team | Accepted |
| 7 | 23 Nov 2026 | P0-Lite estimate labelled aggressive and conditional; checkpoint-based reductions made explicit; no completion guarantee | Independent review of version 1.0 | Team | Accepted |
| 8 | 23 Nov 2026 | SeaweedFS retained for local storage, subject to the M0 verification gate (05 §14.1) | Independent review of version 1.0 | Team | Accepted |
| 9 | 23 Nov 2026 | API contract (documentation 1.2): an unsupported method on an existing route returns 405 `method_not_allowed` (problem+json) with an `Allow` header listing every method of the path; a path that matches no route stays 404. Error catalogue 24 → 25 codes. Documents updated: 07 §1.10, §1.12, §1.13; 08 §21; 11 IT-GEN-01 | RFC 9110 §15.5.6. The documents were silent on 405, and the M0 build had answered it as 404; the developer's M0 review rejected that mapping | Developer | Accepted |
| 10 | 23 Nov 2026 | API contract (documentation 1.2): every GET resource also answers HEAD with the GET status and header fields and no body; the endpoint runs once without side effects (for example no `document.pdf_downloaded` event for E-22); `Allow` lists HEAD wherever it lists GET. Unsupported methods stay 405 and unknown resources stay 404. Documents updated: 07 §1.13, §1.14, §2; 11 IT-GEN-01 | RFC 9110 §9.1 (general-purpose servers support GET and HEAD) and RFC 9110 §9.3.2 (HEAD is GET without content). The M0 build answered HEAD on its GET routes with 405; the developer's final M0 review required HEAD support | Developer | Accepted |

## 7. Research provenance and source packaging

The Perplexity, Grok and Gemini research reports were independently reviewed, their relevant recommendations were audited, and the accepted decisions are consolidated in this package. The original full reports are not bundled in the ZIP.

| Source | How it was used | In the ZIP |
| --- | --- | --- |
| Official PS5 problem statement (as restated in the master documentation prompt) | Scope authority for the client's requirements | No |
| Original research blueprint | Market, regulatory and technical research; first architecture | No |
| Revision 2 and the Revision 2.1 errata | Technical baseline and frozen decisions | No (separate documents) |
| Perplexity research report | Independently reviewed; relevant recommendations audited; accepted corrections (Revision 2, A–F) consolidated in this package | No |
| Grok and Gemini research reports | Independently reviewed; relevant recommendations audited; accepted decisions consolidated in this package | No |
| Master documentation prompt (23 November 2026) | Final scope, constraints and mandatory decisions | No |

The package is self-contained for implementation: everything Claude Code needs is in `docs/00`–`docs/15`. The source reports are references, not build inputs.
