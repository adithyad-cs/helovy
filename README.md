# HIVE DOCS — PS5 Point of Sale and Smart Document Generation Platform

> **Working name:** HIVE DOCS is provisional and needs Heloavy's approval (question Q-21 in `docs/14_OPEN_QUESTIONS_AND_ASSUMPTIONS.md`).
> **Official project title:** Point of Sale (POS) and Smart Document Generation Platform · Project ID PS5 · Group 6 · HIVE Hub / Heloavy.

HIVE DOCS is a web application that lets small Indian service businesses create, finalise, store and re-download professional business documents. The first document type is the invoice. It is built to grow into a commercial product, not as a disposable prototype.

## Status on 24 November 2026

| Item | Status |
| --- | --- |
| Documentation package | Version 1.2 (unchanged since the M0 review) |
| Source code | P0-Lite milestones M0 to M8 implemented on branch `claude/busy-bell-14l7rh`. Milestone history, evidence and open questions are in [`PROGRESS.md`](PROGRESS.md) |
| Automated checks | Backend 616 tests pass; ruff, ruff format and mypy `--strict` clean; FE-01 to FE-03 pass. Run in the **cloud development container** (Linux), not on the presenter laptop |
| Demonstration checks | DC-01 to DC-20 rehearsed in the cloud container: 18 pass, 2 partial (DC-01 and DC-17: the application image of the current code could not be built there). **Not yet run on the presenter machine** |
| Docker | Clean build of the committed Dockerfile and Compose with the current code: **BLOCKED / UNVERIFIED** (see [Known limitations](#known-limitations)). M0 acceptance stays conditional on it |
| Render staging | **Prepared, not deployed:** `render.yaml` and [`docs/DEPLOYMENT_RENDER.md`](docs/DEPLOYMENT_RENDER.md). Creating it needs paid Render resources and the developer's go-ahead |
| Demonstration | Wednesday 25 November 2026, 1:00 PM IST |
| Development capacity | One developer, assisted by Claude Code |

## What the demonstration covers (P0-Lite)

```
Landing page → ENTER THE SYSTEM → secure demo sign-in → business profile → customer
→ invoice draft with several lines and discounts → server-calculated totals
→ watermarked draft PDF preview → finalise → PDF stored privately with SHA-256
→ document history → reopen and download the same PDF
```

- Every PDF carries the text **"SPECIMEN — demonstration document, not a tax invoice."**
- P0-Lite has **no GST calculation** and makes **no compliance claims**.
- The server recalculates every amount with `Decimal` (`calc-1.0.0`); the browser only displays the server's figures.
- A finalised invoice gets its number once, in one transaction, and is immutable: its snapshot, its stored PDF and its audit events cannot be changed, by the API or by the application's database role.
- Each organization sees only its own data. Another organization's records answer 404.

The five-minute script, the prepared data and the presenter checklist are in [`DEMO_CHECKLIST.md`](DEMO_CHECKLIST.md).

## Setting up and running

Three ways to run HIVE DOCS locally. All use the same configuration files and the same PostgreSQL 16 and SeaweedFS services.

| Way | Where it was verified | Use it for |
| --- | --- | --- |
| **A. Backing services in Docker, application on the host** (`uvicorn`) | Cloud development container (Linux): the whole M1–M8 test and DC rehearsal ran this way | Development; the presenter laptop if it can run Docker |
| **B. Everything in Docker Compose** (the documented demonstration runtime, 05 §7, D-1) | **Not verified with the current code**: the committed Dockerfile could not be built in either available environment | The demonstration, once a Docker-capable machine has built the image |
| **C. Native Windows, no Docker** (temporary arrangement approved on 23 Nov) | **Not verified**: Claude Code has no access to the Windows laptop | Only if the presenter laptop cannot run Docker |

### Prerequisites

| Requirement | Check | Notes |
| --- | --- | --- |
| Git | `git --version` | |
| Docker Engine with Compose v2 | `docker compose version` | Ways A and B |
| Python 3.12 and uv | `uv --version` | `uv python install 3.12` if needed |
| Node.js 22.12 or later with npm | `node --version` | The `engines` field of `frontend/package.json` |
| A Chromium-based browser | — | The demonstration uses Chrome at 100 % zoom |

### Configuration (all ways)

```bash
cp .env.example .env                 # development database ps5, bucket ps5-documents-dev
cp .env.test.example .env.test       # test database ps5_test, bucket ps5-documents-test
cp deploy/seaweedfs/s3.example.json deploy/seaweedfs/s3.json
```

Fill in every `<placeholder>`. `.env.example` shows how to generate each value. The S3 key pairs in `.env` and `.env.test` must match identities in `deploy/seaweedfs/s3.json`. `.env`, `.env.test` and `s3.json` are git-ignored: **never commit them, and never put the demonstration password in any file.**

### Way A: services in Docker, application on the host (verified)

```bash
docker compose up -d db storage                  # PostgreSQL 16 and SeaweedFS 4.54 on 127.0.0.1
cd backend && uv sync && cd ..
cd frontend && npm ci && npm run build && cd ..  # → frontend/dist
rm -rf backend/app/static && cp -r frontend/dist backend/app/static   # git-ignored copy served by the backend
cd backend
uv run alembic upgrade head                      # as ps5_migrator (MIGRATION_DATABASE_URL)
uv run python -m app.cli init-dev-storage        # creates the private, versioned bucket; safe to re-run
uv run uvicorn app.main:app --port 8000          # open http://localhost:8000
```

On first start, `deploy/postgres/init` creates the databases `ps5` and `ps5_test` and the roles `ps5_migrator` and `ps5_app`. It runs only while the `pgdata` volume is empty. Check health with `curl http://localhost:8000/healthz` and `curl http://localhost:8000/readyz`; `readyz` reports `database`, `storage` and `templates`.

For frontend work, `cd frontend && npm run dev` serves the SPA at `http://localhost:5173` and proxies `/api` to port 8000. Set `APP_ORIGIN=http://localhost:5173` while you do this.

### Way B: everything in Docker Compose (documented, not yet verified)

```bash
docker compose up -d --build                     # builds hive-docs:local, starts db, storage and app
docker compose run --rm app alembic upgrade head # the image ships alembic.ini and the migrations
docker compose run --rm app python -m app.cli init-dev-storage
```

Open `http://localhost:8000`. **Status:** the committed Dockerfile has never been built successfully. In the cloud container, build containers have no DNS or direct internet access. On the developer's Windows laptop, Docker Desktop cannot run (hardware virtualization is disabled). On a Docker-capable machine with normal internet access, run the three commands above and then DC-01 and DC-17 before relying on this way.

### Way C: native Windows without Docker (not verified)

Use this only if the presenter laptop cannot run Docker. It keeps the approved stack: PostgreSQL 16 and SeaweedFS run as local programs instead of containers. No storage or database substitute is allowed.

1. **PostgreSQL 16:** you need the databases `ps5` and `ps5_test` and the roles `ps5_migrator` and `ps5_app`, set up exactly as `deploy/postgres/init/10-ps5-roles-and-databases.sh` describes. The developer reports these already exist natively (PostgreSQL 16.16). **Do not recreate roles, drop databases or re-run the script.** Check the state first with `uv run alembic current` from `backend`.
2. **SeaweedFS 4.54:** the developer reports a native `weed.exe` on 127.0.0.1:8333 that refuses anonymous requests. Its identities must match the keys in `.env` and `.env.test`. Run it with the flags from `docker-compose.yml`, adapted to the host: `weed server -dir=<data folder> -ip=127.0.0.1 -ip.bind=127.0.0.1 -master.telemetry=false -s3 -s3.port=8333 -s3.config=deploy\seaweedfs\s3.json -s3.autoCreateBucket=false -s3.iam=false`. The bucket stays private, and authentication stays on.
3. **WeasyPrint 70** needs its native libraries (Pango) on Windows. A smoke test passed natively on 23 Nov; the project templates have not been rendered natively yet.
4. Run the commands of way A from PowerShell, skipping `docker compose`. To copy the SPA build, use `Remove-Item -Recurse -Force backend\app\static -ErrorAction SilentlyContinue; Copy-Item -Recurse frontend\dist backend\app\static`.
5. Run the storage gate checks and `uv run pytest` natively first. The SeaweedFS gate tests are part of the suite and need `.env.test`'s keys to match `s3.json`.
6. Before the demonstration, run DC-01 to DC-20 on this machine and record the results in `PROGRESS.md` as native-Windows evidence.

## Demonstration account and data

There is no public sign-up. The account is created only with the CLI (02 FR-06, 12 §3):

```bash
cd backend
uv run python -m app.cli create-demo-account --email owner@demo.invalid --name "Demo Owner" --org "Demo Studio"
```

The command asks for the password at a hidden prompt (at least 12 characters). It never prints it. You may instead set `DEMO_ACCOUNT_PASSWORD` for that single command. **Never write the password in this repository, in `.env` or in any document.** For the isolation check (DC-19), create a second account the same way: `--email auditor@demo.invalid --name "Isolation Auditor" --org "Isolation Check Org"`.

Enter the demonstration data set (11 §5) either by typing it in the browser (values in `DEMO_CHECKLIST.md`), or with the helper, which uses only the public API and asks for the password:

```bash
cd backend
uv run python scripts/enter_demo_data.py --base-url http://localhost:8000
```

The helper creates the business profile, two customers, finalised invoice `INV/26-27/00001` (₹2,700.00, with its PDF ready) and one draft. It refuses to run when the organization already has invoices. `--base-url` must equal `APP_ORIGIN`. `--email` fills another account created with the CLI, such as the rehearsal account suggested in `DEMO_CHECKLIST.md`.

## Tests

```bash
cd backend && uv run pytest                      # all suites (db and storage running, .env.test present)
cd backend && uv run pytest tests/unit           # pure unit tests, no services
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app
cd frontend && npx tsc --noEmit && npm run lint && npm run build   # FE-01..FE-03
```

Test runs use `.env.test` only: they recreate the `ps5_test` database schema and use the `ps5-documents-test` bucket. They never touch `ps5` or the development bucket. There is no frontend unit-test runner (05 §2). The browser checks (DC-02 to DC-20, FE-05) were scripted with the container's Playwright outside the repository. The Playwright suite in the repository is stretch item S-03 and was not started.

## Known limitations

- **Docker is unverified.** The committed Dockerfile has not been built successfully, and Compose has not run the current code (way B). The documented demonstration runtime is the Docker stack on the presenter laptop (D-1). The developer's Windows laptop cannot run Docker, and the native fallback (way C) is untested. **A presenter machine must be chosen and DC-01 to DC-20 run on it before the demonstration** (10 M8.3).
- **P0-Lite scope only** (03 §2). No GST, sign-up, email, payments, receipts, payment requests, salary slips, plans, logo upload or second template. One user, one business and one template (`classic@1`) per organization. Deferred work is listed in 03 §4–§5 and 10 §10.
- **Specimen documents.** Every PDF says "SPECIMEN — demonstration document, not a tax invoice." The data is synthetic (11 §5). Delete it after Heloavy's evaluation (12 §16).
- **Single process.** The rate limits (calculate, preview, PDF retry) are kept in memory and reset when the server restarts. Fine for one local server, not for several replicas.
- **One JavaScript bundle** (about 650 kB before compression; Vite warns above 500 kB). Fine on localhost; code splitting is future work.
- **Open questions for the developer** (details in `PROGRESS.md`): the landing button label ("ENTER THE SYSTEM" per 08 §10.1, "ENTER" in the directive); the additive `seller`/`buyer` fields on finalised documents; the PDF metadata title "Invoice INV/26-27/00001" (the printed title is "Invoice"); and the `document_lines_discount_ck` gap (a schema change needs approval).

## Deployment

| Target | Status |
| --- | --- |
| Local demonstration (05 §13.1, MUST) | Way B on a Docker-capable laptop with a backup machine. Freeze per 10 M8.4: tag `v0.1.0-demo`, `docker save` the image, `pg_dump` plus a copy of the SeaweedFS volume, export sample PDFs. **Not done:** the freeze belongs on the demonstration machine after its DC run |
| Render staging (developer request, 24 Nov) | Prepared, not deployed: `render.yaml` (Singapore; Postgres 16 `ps5`; private SeaweedFS 4.54 with a disk; web service with `/readyz` health check and pre-deploy migrations) and [`docs/DEPLOYMENT_RENDER.md`](docs/DEPLOYMENT_RENDER.md). Paid resources; nothing created |
| Cloud reference (05 §13.2, stretch S-02, DigitalOcean) | Not started |
| Production (05 §13.3, P1-14) | Deferred: backups with tested restore, monitoring, row-level security, MFA, document encryption, DPDP review |

## Repository layout

```
├── CLAUDE.md, README.md, PROJECT_SUMMARY.md, CONSISTENCY_AUDIT.md
├── PROGRESS.md            # milestone log, evidence by environment, decisions, open questions
├── DEMO_CHECKLIST.md      # presenter checklist, prepared data, 5-minute script, fallbacks
├── render.yaml            # Render staging Blueprint (docs/DEPLOYMENT_RENDER.md); no secrets
├── docs/                  # the specification package (00–15)
├── backend/
│   ├── app/core/          # config, db, clock, errors, HTTP helpers, CSRF-before-routing middleware
│   ├── app/modules/       # auth, tenancy, audit, businesses, customers, calc, documents,
│   │                      #   rendering (classic@1 template, worker pool), storage, health
│   ├── app/cli.py         # create-demo-account, init-dev-storage, template-hash, check-storage
│   ├── alembic/versions/  # 0001_identity … 0005_app_role_privileges (hand-written SQL)
│   ├── scripts/           # tooling, excluded from the image (spike A, enter_demo_data)
│   └── tests/             # unit, db, integration (616 tests)
├── frontend/src/          # api, app shell, components/ui, features (landing, auth, business,
│                          #   customers, invoices, templates, dashboard), lib, styles
├── deploy/                # postgres init script; SeaweedFS identities example;
│                          #   render/seaweedfs: the Render storage image and identities example
├── Dockerfile             # one image: built SPA + backend
├── docker-compose.yml     # db, storage, app; named volumes; ports on 127.0.0.1
└── .env.example, .env.test.example
```

## Working with Claude Code

`CLAUDE.md` at the root points every session to `docs/15_CLAUDE_CODE_INSTRUCTIONS.md` (binding rules) and to `PROGRESS.md` (current state). Work proceeds one milestone at a time: Inspect → Plan → Implement → Test → Review → Report.

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
| [`docs/DEPLOYMENT_RENDER.md`](docs/DEPLOYMENT_RENDER.md) | Render staging: services, credentials, storage provisioning, migrations, backups, rollback, verification | Developer, operators |
| [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md) | Two-page summary to share with teammates | Teammates |
| [`CONSISTENCY_AUDIT.md`](CONSISTENCY_AUDIT.md) | Cross-document consistency audit and the remaining upstream contradictions | Team lead, reviewers |
| [`PROGRESS.md`](PROGRESS.md) | Milestone log, verification evidence by environment, decisions and open questions | Developer, reviewers |
| [`DEMO_CHECKLIST.md`](DEMO_CHECKLIST.md) | Presenter checklist, prepared data and the five-minute script | Presenters |

## Source-of-truth order

1. The official PS5 problem statement (client requirements).
2. Revision 2 with the Revision 2.1 errata (technical baseline).
3. Accepted recommendations from the independent Perplexity, Grok and Gemini research reports. All three were independently reviewed, their relevant recommendations were audited, and the accepted decisions are consolidated in this package. The original full reports are not bundled in this ZIP.
4. The decisions in the master documentation prompt of 23 November 2026.

This package consolidates all four sources. Every place where they disagree is listed in `docs/14_OPEN_QUESTIONS_AND_ASSUMPTIONS.md` §4, together with how this package resolves it.

## Version history

| Version | Date | Changes |
| --- | --- | --- |
| 1.2 | 23 Nov 2026 | HTTP method corrections from the developer's review of M0 (RFC 9110). **405:** an unsupported method on an existing route returns 405 `method_not_allowed` (problem+json) with an `Allow` header listing every method of the path; a path that matches no route stays 404; error catalogue 24 → 25 codes. **HEAD:** every GET resource also answers HEAD with the GET status and header fields and no body, and `Allow` lists HEAD wherever it lists GET (07 §1.14). Documents changed: 07, 08 (405 only), 11 and 14 (decisions #9 for 405 and #10 for HEAD), now at version 1.2; all other documents are unchanged at version 1.1. Full list in `CONSISTENCY_AUDIT.md` §3 |
| 1.1 | 23 Nov 2026 | Approved as the working baseline after independent review. Research provenance corrected (Perplexity, Grok and Gemini reviewed; Q-24, C-02 and RK-12 withdrawn); retention wording separated from immutability; P0-Lite schedule labelled aggressive and conditional, with explicit checkpoint reductions; SeaweedFS retained behind an M0 verification gate. Full list in `CONSISTENCY_AUDIT.md` §3 |
| 1.0 | 23 Nov 2026 | First complete package |
