# HIVE DOCS — PS5 Point of Sale and Smart Document Generation Platform

> **Working name:** HIVE DOCS is provisional and needs Heloavy's approval (question Q-21 in `docs/14_OPEN_QUESTIONS_AND_ASSUMPTIONS.md`).
> **Official project title:** Point of Sale (POS) and Smart Document Generation Platform · Project ID PS5 · Group 6 · HIVE Hub / Heloavy.

HIVE DOCS is a web application that lets small Indian service businesses create, finalise, store and re-download professional business documents. The first document type is the invoice. It is built to grow into a commercial product, not as a disposable prototype.

## Status on 23 November 2026

| Item | Status |
| --- | --- |
| Research and architecture | Complete: Revision 2 baseline plus Revision 2.1 errata |
| This documentation package | Version 1.1, approved as the working baseline for P0-Lite |
| Source code | None written yet |
| Next milestone | Demonstration on Wednesday 25 November 2026, afternoon (exact time to be confirmed) |
| Development capacity | One developer, assisted by Claude Code |

## What the 25 November demonstration is planned to cover (P0-Lite)

```
Landing page → ENTER THE SYSTEM → secure demo sign-in → business profile → customer
→ invoice draft with several lines and discounts → server-calculated totals
→ watermarked draft PDF preview → finalise → PDF stored privately with SHA-256
→ document history → reopen and download the same PDF
```

- Every PDF carries the text **"SPECIMEN — demonstration document, not a tax invoice."**
- P0-Lite has **no GST calculation** and makes **no compliance claims**.
- The full Revision 2 P0 (68–89 person-hours) is **not achievable by one developer** before 25 November. P0-Lite is the honest subset, and even its 16.5–22-hour estimate against about 19 focused hours is **aggressive and conditional**: fixed checkpoints decide what is reduced or deferred, and completion of every P0-Lite item is not guaranteed.
- Calculation correctness, tenant isolation, finalisation integrity and data and PDF persistence are never weakened to meet the date. See `docs/10_IMPLEMENTATION_PLAN.md`.

## Documentation map

| File | Purpose | Main readers |
| --- | --- | --- |
| [`docs/00_START_HERE.md`](docs/00_START_HERE.md) | Orientation: what, why, scope, how to read the rest | Everyone |
| [`docs/01_PROJECT_CHARTER.md`](docs/01_PROJECT_CHARTER.md) | Identity, objectives, stakeholders, constraints, risks | Team, Heloavy |
| [`docs/02_PRD.md`](docs/02_PRD.md) | Personas, user stories, requirements, business rules, lifecycle | Developer, reviewers |
| [`docs/03_SCOPE_AND_FEATURES.md`](docs/03_SCOPE_AND_FEATURES.md) | Feature inventory: P0-Lite, stretch, P1, P2, excluded | Everyone |
| [`docs/04_ARCHITECTURE.md`](docs/04_ARCHITECTURE.md) | System design, flows, finalisation, storage, deployment, decisions | Developer, Claude Code |
| [`docs/05_TECH_STACK_AND_SETUP.md`](docs/05_TECH_STACK_AND_SETUP.md) | Technologies, versions, setup, commands, environment variables | Developer, Claude Code |
| [`docs/06_DATABASE_SCHEMA.md`](docs/06_DATABASE_SCHEMA.md) | The 15 P0-Lite tables, constraints, indexes, triggers, migrations | Developer, Claude Code |
| [`docs/07_API_SPEC.md`](docs/07_API_SPEC.md) | The 23 P0-Lite endpoints with examples and errors | Developer, Claude Code |
| [`docs/08_UI_UX_SPEC.md`](docs/08_UI_UX_SPEC.md) | Design system and every P0-Lite screen | Developer, presenters |
| [`docs/09_FINANCIAL_AND_DOCUMENT_RULES.md`](docs/09_FINANCIAL_AND_DOCUMENT_RULES.md) | Calculations, rounding, numbering, snapshots, SPECIMEN rules | Developer, reviewers |
| [`docs/10_IMPLEMENTATION_PLAN.md`](docs/10_IMPLEMENTATION_PLAN.md) | Single-developer milestones, estimates, checkpoints, fallback | Developer, team lead |
| [`docs/11_QA_AND_ACCEPTANCE.md`](docs/11_QA_AND_ACCEPTANCE.md) | Test specification and the mandatory demonstration checks | Developer, reviewers |
| [`docs/12_SECURITY_AND_PRIVACY.md`](docs/12_SECURITY_AND_PRIVACY.md) | Demonstration safeguards versus production hardening | Developer, reviewers |
| [`docs/13_TEAM_HANDOFF.md`](docs/13_TEAM_HANDOFF.md) | Plain-language explanation for HIVE Hub teammates | Teammates, presenters |
| [`docs/14_OPEN_QUESTIONS_AND_ASSUMPTIONS.md`](docs/14_OPEN_QUESTIONS_AND_ASSUMPTIONS.md) | Questions for Heloavy, assumptions, upstream contradictions | Team lead, Heloavy |
| [`docs/15_CLAUDE_CODE_INSTRUCTIONS.md`](docs/15_CLAUDE_CODE_INSTRUCTIONS.md) | Binding rules and workflow for the development agent | Claude Code, developer |
| [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md) | Two-page summary to share with teammates | Teammates |
| [`CONSISTENCY_AUDIT.md`](CONSISTENCY_AUDIT.md) | Cross-document consistency audit and the remaining upstream contradictions | Team lead, reviewers |

## How to begin development with Claude Code

1. Put this folder at the root of the project repository. Keep `CLAUDE.md` at the root: Claude Code reads it at the start of every session, and it points to `docs/15_CLAUDE_CODE_INSTRUCTIONS.md`.
2. Start the first session with:
   > Read CLAUDE.md and every file in docs/ before writing code. PROGRESS.md does not exist yet: create it in M0 using the format in docs/15 §5. Then implement milestone M0 exactly as specified in docs/10 §3, following the workflow in docs/15 §3 (Inspect → Plan → Implement → Test → Review → Report). Stop when M0's exit criteria are met and report.

   Later sessions use the prompt in docs/10 §9, which also reads PROGRESS.md.
3. Run one milestone per session. Review the report and the test results before starting the next milestone.
4. Claude Code keeps `PROGRESS.md` at the repository root up to date (format in `docs/15_CLAUDE_CODE_INSTRUCTIONS.md`).

## Target repository layout

```
hive-docs/
├── CLAUDE.md                  # agent entry point (exists now)
├── README.md                  # this file (exists now)
├── PROJECT_SUMMARY.md         # team summary (exists now)
├── PROGRESS.md                # created and maintained by Claude Code from M0
├── docs/                      # this documentation package (exists now)
├── backend/                   # FastAPI modular monolith (created in M0)
├── frontend/                  # React + TypeScript + Vite SPA (created in M0)
├── deploy/                    # local PostgreSQL init script, SeaweedFS identities example (created in M0)
├── Dockerfile                 # one image: built SPA + backend (created in M0)
├── docker-compose.yml         # local PostgreSQL 16 + SeaweedFS (created in M0)
├── .env.example               # documented variables, no secrets (created in M0)
└── .env.test.example          # test database and bucket, no secrets (created in M0)
```

The full folder layout is in `docs/05_TECH_STACK_AND_SETUP.md` §4; module boundaries are in `docs/04_ARCHITECTURE.md` §3 (backend) and §4 (frontend).

## Source-of-truth order

1. The official PS5 problem statement (client requirements).
2. Revision 2 with the Revision 2.1 errata (technical baseline).
3. Accepted recommendations from the independent Perplexity, Grok and Gemini research reports. All three were independently reviewed, their relevant recommendations were audited, and the accepted decisions are consolidated in this package. The original full reports are not bundled in this ZIP.
4. The decisions in the master documentation prompt of 23 November 2026.

This package consolidates all four sources. Every place where they disagree is listed in `docs/14_OPEN_QUESTIONS_AND_ASSUMPTIONS.md` §4, together with how this package resolves it.

## Version history

| Version | Date | Changes |
| --- | --- | --- |
| 1.1 | 23 Nov 2026 | Approved as the working baseline after independent review. Research provenance corrected (Perplexity, Grok and Gemini reviewed; Q-24, C-02 and RK-12 withdrawn); retention wording separated from immutability; P0-Lite schedule labelled aggressive and conditional, with explicit checkpoint reductions; SeaweedFS retained behind an M0 verification gate. Full list in `CONSISTENCY_AUDIT.md` §3 |
| 1.0 | 23 Nov 2026 | First complete package |
