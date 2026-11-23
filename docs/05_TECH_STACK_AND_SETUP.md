# 05 — Technology Stack and Setup

| | |
| --- | --- |
| Document | Stack, setup, commands · version 1.1 · 23 November 2026 |
| Rule | The stack below is frozen (mandatory). Exact patch versions are chosen in M0, recorded in lockfiles and in PROGRESS.md, and checked against §14 |
| Marker | **(verify)** means the item must be confirmed in the real development environment before being relied on. Nothing marked (verify) was tested while writing this document |

## 1. Approved stack

| Layer | Technology | Version constraint | Responsibility | Why selected |
| --- | --- | --- | --- | --- |
| Frontend | React | 18.x, pinned explicitly (latest 18.x patch; verify, V-03) | UI components | Approved stack; mature ecosystem |
| Frontend | TypeScript | Current 5.x (verify) | Static typing for the SPA | Catches contract mismatches early |
| Frontend | Vite | Current major compatible with React 18 and the chosen Node LTS (verify, V-02) | Dev server, production build | Fast builds; simple static output |
| Frontend | React Router | Current major supporting React 18 (verify, V-04) | Client-side routing | Approved stack |
| Frontend | TanStack Query | v5 (verify) | Server state, caching, polling | Fits a REST API with ETags |
| Frontend | React Hook Form | v7 (verify) | Form state | Performant forms with many line rows |
| Frontend | Zod (+ `@hookform/resolvers`) | Current major supported by the resolver (verify, V-04) | Client-side validation mirroring 09 §4 | Shared schema style across forms |
| Frontend | Tailwind CSS | Current major with its Vite integration (verify) | Styling with design tokens | Consistent spacing and colour system |
| Frontend | Radix UI primitives | Current (verify) | Accessible dialog, dropdown, select, toast, tooltip | Accessibility built in |
| Backend | Python | 3.12 | Runtime | Approved; `Decimal` in the standard library |
| Backend | FastAPI | Current release (verify) | HTTP API, dependency injection | Approved stack |
| Backend | Pydantic | v2 (+ `pydantic-settings`) | Request and response schemas (strict), settings | Strict typing; environment-based configuration |
| Backend | SQLAlchemy | `>=2.0,<2.1` | ORM, transactions | Approved; explicit transaction control |
| Backend | psycopg | 3.x (`psycopg[binary]`) | PostgreSQL driver | Approved |
| Backend | Alembic | Current 1.x (verify) | Schema migrations | Approved |
| Backend | argon2-cffi | Current (verify) | Argon2id password hashing | Mandated algorithm |
| Backend | uvicorn | Current (verify) | ASGI server, **one worker process** | The in-memory limiter and render pool assume a single process |
| Database | PostgreSQL | 16 (image `postgres:16`, pinned by digest, V-05) | Durable data, constraints, triggers | Approved; NUMERIC, JSONB, generated columns |
| Financial engine | Python `decimal` | Standard library | Exact money arithmetic, ROUND_HALF_UP | Mandated; no floats |
| PDF | Jinja2 | 3.1.x (verify) | HTML templating, autoescape on | Approved |
| PDF | WeasyPrint | `>=70.0,<71`; the exact tested patch is locked (V-06) | HTML/CSS → PDF | Approved; server-side and offline |
| PDF | Fonts: Noto Sans, Noto Sans Devanagari | Latest releases (OFL 1.1) | PDF text, including ₹ and Devanagari names | Bundled; no network fonts |
| Storage | boto3 | Current (verify) | S3 API client | The single storage implementation |
| Storage | SeaweedFS (local) | `chrislusf/seaweedfs`, pinned by tag and digest; must pass the M0 verification gate (§14.1) | Local S3-compatible storage | Retained by team decision; replaces MinIO (ADR-13, C-01) |
| Storage | DigitalOcean Spaces (cloud reference) | — | Durable private PDF storage | Same region as the database (BLR1) |
| Runtime | Docker Engine + Compose v2 | Current (verify) | Local stack; image build | Mandated |
| UI fonts | Inter, Source Serif 4 | Latest releases (OFL 1.1) | UI and display type | Self-hosted; no third-party font requests |

## 2. Development tooling (supporting, not product stack)

These tools are development-only. They do not change the product architecture.

| Tool | Purpose | Notes |
| --- | --- | --- |
| uv | Python environment and lockfile (`uv.lock`) | `uv sync --frozen` in Docker |
| npm | Frontend packages and lockfile (`package-lock.json`) | `npm ci` in Docker |
| pytest, hypothesis, httpx | Unit, property and API tests | `httpx` drives FastAPI's test client |
| ruff, mypy | Python lint, format, type checks | |
| ESLint (+ typescript-eslint, React Hooks plugin), `tsc` | Frontend lint and type checks | |
| Playwright | End-to-end automation | **STRETCH only (S-03)** |

No frontend unit-test runner is added: the SPA holds no business logic in P0-Lite (C-10, 14 §4).

## 3. Allowed dependencies

Anything not on this list needs the developer's explicit approval, recorded in PROGRESS.md (15, rule 4).

- **Backend runtime:** fastapi, `uvicorn[standard]`, pydantic, pydantic-settings, `sqlalchemy>=2.0,<2.1`, `psycopg[binary]`, alembic, argon2-cffi, jinja2, `weasyprint>=70.0,<71`, boto3.
- **Backend development:** pytest, hypothesis, httpx, ruff, mypy.
- **Frontend runtime:** react@18, react-dom@18, react-router, @tanstack/react-query, react-hook-form, @hookform/resolvers, zod, Radix UI primitives (the umbrella `radix-ui` package or individual `@radix-ui/react-*` packages; choose one in M0).
- **Frontend development:** typescript, vite, @vitejs/plugin-react, tailwindcss and its Vite plugin, eslint, typescript-eslint, eslint-plugin-react-hooks, @types/react@18, @types/react-dom@18; @playwright/test only for S-03.
- **Not allowed:** animation libraries (the landing animation is CSS and SVG), chart libraries, state-management libraries, UI kits beyond Radix, ORMs other than SQLAlchemy, task queues, Redis, any CDN-hosted asset.

## 4. Repository layout

```text
hive-docs/
├── CLAUDE.md                     # agent entry point → docs/15
├── README.md
├── PROJECT_SUMMARY.md
├── PROGRESS.md                   # maintained by Claude Code (15 §5)
├── docs/                         # this package (00–15)
├── .env.example                  # placeholders only; .env is git-ignored
├── .env.test.example             # test database and bucket; .env.test is git-ignored
├── .gitignore
├── Dockerfile                    # multi-stage: frontend build → Python runtime
├── docker-compose.yml            # app, db, storage
├── deploy/
│   ├── postgres/init/            # local-only role and database creation script
│   └── seaweedfs/
│       ├── s3.example.json       # identities with placeholder keys
│       └── s3.json               # git-ignored, real local keys
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py                # uses MIGRATION_DATABASE_URL
│   │   └── versions/             # 0001 … 0004 (06 §14)
│   ├── app/
│   │   ├── main.py               # create_app()
│   │   ├── cli.py                # create-demo-account, init-dev-storage, template-hash
│   │   ├── core/                 # config, db, errors, logging, middleware, ratelimit, clock
│   │   ├── modules/
│   │   │   ├── audit/
│   │   │   ├── tenancy/
│   │   │   ├── auth/
│   │   │   ├── businesses/
│   │   │   ├── customers/
│   │   │   ├── calc/             # pure functions only
│   │   │   ├── rendering/
│   │   │   │   ├── registry.py   # template id → expected SHA-256
│   │   │   │   ├── fetcher.py    # restricted URL fetcher
│   │   │   │   ├── pool.py       # worker processes, timeout
│   │   │   │   ├── templates/invoice/classic/v1/   # template.html, styles.css
│   │   │   │   └── assets/fonts/ # Noto Sans, Noto Sans Devanagari + OFL.txt
│   │   │   ├── storage/
│   │   │   ├── documents/        # drafts, numbering, finalize, snapshot, idempotency, artifacts
│   │   │   └── health/
│   │   └── static/               # built SPA copied here at image build time (git-ignored)
│   └── tests/
│       ├── conftest.py
│       ├── fixtures/             # invoice_fixture.json (09 §15)
│       ├── unit/                 # calc, numbering, snapshot, security, formatting
│       ├── db/                   # constraints, triggers, grants
│       └── integration/          # auth, businesses, customers, documents, finalize, pdf, tenancy, health
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── tsconfig.json
    ├── vite.config.ts            # dev proxy /api, /healthz, /readyz → :8000
    ├── eslint.config.js
    ├── index.html
    └── src/
        ├── main.tsx
        ├── app/                  # router, providers, route guard
        ├── api/                  # http client, problem parsing, query keys, endpoints
        ├── features/             # landing, auth, dashboard, business, customers, invoices, templates
        ├── components/ui/        # Radix wrappers: Button, Field, Dialog, AlertDialog, Toast, Select, Table, EmptyState, ErrorState, Skeleton
        ├── lib/                  # money.ts, dates.ts, schemas.ts, idempotency.ts
        ├── styles/               # index.css (Tailwind + tokens)
        └── assets/fonts/         # Inter, Source Serif 4 + licences
```

## 5. Prerequisites (developer machine)

| Requirement | Check command | Notes |
| --- | --- | --- |
| Git | `git --version` | |
| Docker Engine with Compose v2 | `docker --version`, `docker compose version` | Docker Desktop on macOS or Windows (WSL2 on Windows; verify) |
| Python 3.12 | `python3.12 --version` | uv can provide it: `uv python install 3.12` (verify) |
| uv | `uv --version` | Install per uv's official instructions (verify, V-01) |
| Node.js LTS + npm | `node --version`, `npm --version` | Version must satisfy Vite's `engines` field (V-02) |
| Fonts | — | Download Noto Sans, Noto Sans Devanagari, Inter and Source Serif 4 from their official repositories; keep each OFL licence next to the files (V-16) |

## 6. Installation

### 6.1 One-time scaffolding (M0, run once)

These are typical commands. Check their flags against current tool documentation before running them (verify).

```bash
# Backend project
uv init --app --python 3.12 backend
cd backend
uv add fastapi "uvicorn[standard]" pydantic pydantic-settings "sqlalchemy>=2.0,<2.1" \
       "psycopg[binary]" alembic argon2-cffi jinja2 "weasyprint>=70.0,<71" boto3
uv add --dev pytest hypothesis httpx ruff mypy
cd ..

# Frontend project (the Vite template may install React 19: pin React 18 explicitly, V-03)
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install react@18 react-dom@18
npm install -D @types/react@18 @types/react-dom@18
npm install react-router @tanstack/react-query react-hook-form @hookform/resolvers zod
npm install tailwindcss @tailwindcss/vite        # Tailwind v4 integration (verify)
npm install radix-ui                             # or individual @radix-ui/react-* packages (verify)
cd ..
```

After installation, check peer-dependency warnings: every package must accept React 18 (V-04).

### 6.2 Setting up a working copy

```bash
git clone <repository-url> hive-docs && cd hive-docs
cp .env.example .env                       # fill in local values; never commit .env
cp .env.test.example .env.test
cp deploy/seaweedfs/s3.example.json deploy/seaweedfs/s3.json   # set local keys
docker compose up -d db storage
cd backend && uv sync && cd ..
cd frontend && npm ci && cd ..
cd backend
uv run alembic upgrade head                      # uses MIGRATION_DATABASE_URL
uv run python -m app.cli init-dev-storage        # creates S3_BUCKET locally
DEMO_ACCOUNT_PASSWORD='<at least 12 characters>' \
  uv run python -m app.cli create-demo-account --email owner@demo.invalid \
  --name "Demo Owner" --org "Demo Studio"
```

Use a reserved, non-routable domain such as `.invalid` for demonstration emails.

## 7. Docker setup

### 7.1 Image (Dockerfile, multi-stage)

| Stage | Base | Steps |
| --- | --- | --- |
| `frontend-build` | Node LTS image, pinned by digest (V-02) | `npm ci` → `npm run build` → `frontend/dist` |
| `runtime` | `python:3.12-slim` (Debian-based), pinned by digest | Install WeasyPrint's system libraries as listed in its installation guide for the chosen Debian release (Pango and HarfBuzz; verify, V-06). Do **not** install Ghostscript. Copy `backend/`; `uv sync --frozen --no-dev`; copy `frontend/dist` → `backend/app/static`; create a non-root user; `EXPOSE 8000`; start uvicorn with **one** worker on `0.0.0.0:8000` inside the container |

The image contains no `.env` file, no test data and no secrets.

### 7.2 Compose services (local)

| Service | Image | Ports (host side) | Volumes | Notes |
| --- | --- | --- | --- | --- |
| `app` | Built from the Dockerfile | `127.0.0.1:8000:8000` | none | `env_file: .env`; depends on `db` and `storage`; healthcheck on `/readyz` |
| `db` | `postgres:16@<digest>` | `127.0.0.1:5432:5432` (for developer tools; optional) | `pgdata:/var/lib/postgresql/data`, `./deploy/postgres/init:/docker-entrypoint-initdb.d:ro` | The init script creates databases `ps5` and `ps5_test`, roles `ps5_migrator` (owner) and `ps5_app` (restricted), with passwords from compose environment variables |
| `storage` | `chrislusf/seaweedfs@<digest>` | `127.0.0.1:8333:8333` | `seaweed_data:/data`, `./deploy/seaweedfs/s3.json:/etc/seaweedfs/s3.json:ro` | Command along the lines of `server -s3 -dir=/data -s3.config=/etc/seaweedfs/s3.json` (exact flags: verify, V-07). Anonymous access must be refused (V-08). The configuration must pass the M0 verification gate (§14.1) |

Run migrations against the compose database with `docker compose run --rm app alembic upgrade head`. The container has `MIGRATION_DATABASE_URL` from `.env`, and inside the compose network the hosts are `db` and `storage`.

Never use `docker compose down -v` on the demonstration machine: it deletes the volumes (DC-17).

## 8. Application CLI commands (implemented in M0, M1 and M4)

| Command | Milestone | Behaviour |
| --- | --- | --- |
| `python -m app.cli init-dev-storage` | M0 | Creates `S3_BUCKET` if it is missing and enables versioning if the server supports it. Safe to re-run: an existing bucket is left unchanged and reported as ready (V-18). Refuses to run when `APP_ENV=production` |
| `python -m app.cli create-demo-account --email <e> --name <n> --org <o>` | M1 | Creates one organization, one user and an owner membership in one transaction. The password comes from `DEMO_ACCOUNT_PASSWORD` or a hidden interactive prompt and must be at least 12 characters. Refuses an existing email. Writes the audit event `account.created`. Never prints the password |
| `python -m app.cli template-hash <template_id>` | M4 | Prints the SHA-256 over the template's files (sorted relative paths + contents; 09 §11), for the template registry |

## 9. Environment variables

| Variable | Required | Example (placeholder) | Used by | Notes |
| --- | --- | --- | --- | --- |
| `APP_ENV` | Yes | `development` \| `demo` \| `production` | app | `demo` and `production` turn off the API docs UI and enforce the template hash |
| `APP_ORIGIN` | Yes | `http://localhost:8000` | app | Exact origin for CSRF and Origin checks (`http://localhost:5173` while using the Vite dev server) |
| `DATABASE_URL` | Yes | `postgresql+psycopg://ps5_app:<password>@db:5432/ps5` | app | Restricted runtime role (06 §11); add `?sslmode=require` in the cloud |
| `MIGRATION_DATABASE_URL` | Yes (migrations) | `postgresql+psycopg://ps5_migrator:<password>@db:5432/ps5` | Alembic, CLI | Owner role; not needed by the running server |
| `S3_ENDPOINT_URL` | Yes | `http://storage:8333` | app | `https://blr1.digitaloceanspaces.com` in the cloud |
| `S3_REGION` | Yes | `us-east-1` (locally, any value; verify) / `blr1` | app | |
| `S3_BUCKET` | Yes | `ps5-documents-dev` / `ps5-documents-prod` | app | |
| `S3_ACCESS_KEY_ID` | Yes (secret) | `<access key>` | app | Must match an identity in `s3.json` locally |
| `S3_SECRET_ACCESS_KEY` | Yes (secret) | `<secret key>` | app | |
| `S3_ADDRESSING_STYLE` | No | `path` (SeaweedFS) / `virtual` (Spaces) | app | Verify per provider (V-09) |
| `CSRF_SECRET` | Yes (secret) | 64 hex characters (32 random bytes) | app | Also keys the login-failure subject hash (12 §2) |
| `RENDER_WORKERS` | No | `2` | app | Maximum concurrent render processes |
| `RENDER_TIMEOUT_S` | No | `20` | app | Render kill timeout in seconds |
| `CLIENT_IP_HEADER` | No | unset locally | app | The platform proxy's client-IP header in the cloud (V-11). Unset means the socket address is used |
| `LOG_LEVEL` | No | `INFO` | app | |
| `DEMO_ACCOUNT_PASSWORD` | No | set only for the CLI call | CLI | Never stored in `.env` permanently; never read by the server |
| `POSTGRES_PASSWORD`, `PS5_MIGRATOR_PASSWORD`, `PS5_APP_PASSWORD` | Local compose only | `<password>` | db init script | Local development only |

The server refuses to start when a required variable is missing, when `CSRF_SECRET` is shorter than 32 bytes, or when `APP_ORIGIN` is not a valid origin.

## 10. Development commands

```bash
docker compose up -d db storage                           # backing services
cd backend && uv run uvicorn app.main:app --reload --port 8000   # API at :8000
cd frontend && npm run dev                                # SPA at :5173, proxies to :8000
cd backend && uv run alembic revision -m "<message>"      # new migration (reviewed by hand)
cd backend && uv run alembic upgrade head
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app
cd frontend && npm run lint && npx tsc --noEmit
```

## 11. Build commands

```bash
cd frontend && npm run build              # → frontend/dist
docker build -t hive-docs:local .         # full image
docker compose up -d --build              # whole stack
docker compose run --rm app alembic upgrade head
```

## 12. Test commands

```bash
cd backend && uv run pytest                     # all backend suites (needs db + storage running, .env.test)
cd backend && uv run pytest tests/unit          # pure unit tests (no services)
cd backend && uv run pytest tests/db tests/integration
cd frontend && npx tsc --noEmit && npm run lint && npm run build   # FE-01..FE-03
cd frontend && npx playwright test              # S-03 only (stretch)
```

Tests use `.env.test`: the same variable names, pointing to database `ps5_test` and bucket `ps5-documents-test`. Each test run truncates tables using the migrator role. Test runs never touch the `ps5` database.

## 13. Deployment requirements

### 13.1 Local demonstration (MUST)

- A laptop with Docker, at least 8 GB RAM recommended and 5 GB free disk (estimate).
- The image built and the stack started at least once before the freeze. The demonstration account created. Synthetic data entered (11 §5).
- Ports bound to 127.0.0.1. No internet required.
- A backup machine with the same image and a `pg_dump` plus a SeaweedFS volume copy (10 §7).

### 13.2 Cloud reference (S-02, time-boxed to 90 minutes; basis for P1)

1. Managed PostgreSQL 16 cluster in BLR1. Create database `ps5` and roles `ps5_migrator` and `ps5_app`, applying the grants from 06 §11. Use `sslmode=require` and trusted sources restricted to the app.
2. Spaces bucket `ps5-documents-prod` in BLR1: private, with versioning enabled through the S3 API (for example with an S3-compatible CLI; verify, V-10).
3. App Platform app from the repository using the Dockerfile:
   - readiness health check on `/readyz` and liveness on `/healthz`;
   - a PRE_DEPLOY job running `alembic upgrade head` with `MIGRATION_DATABASE_URL`;
   - all §9 variables as encrypted environment values;
   - `APP_ORIGIN` set to the app's HTTPS URL;
   - `CLIENT_IP_HEADER` set per platform documentation (V-11).
4. Create the demonstration account with a one-off console command (`python -m app.cli create-demo-account …`).
5. Check `/readyz` returns 200, then run DC-01, DC-12, DC-14 and DC-17 against the URL.
6. Synthetic data only, until P1-14 is complete.

### 13.3 Production (P1-14, after Q-04, Q-05 and Q-11)

Backups with point-in-time recovery and a tested restore, monitoring and alerts, row-level security, MFA, document encryption, dependency scanning, an incident process and a DPDP review (12 §14).

## 14. Items to verify in the real environment

| ID | Item | When |
| --- | --- | --- |
| V-01 | uv installation method and `uv init` / `uv add` flags | M0 |
| V-02 | Node.js LTS version that satisfies the chosen Vite release's `engines` field; Node base image digest | M0 |
| V-03 | `npm create vite` installs React 19 by default: confirm, and pin react, react-dom, @types/react and @types/react-dom to 18.x | M0 |
| V-04 | React Router, TanStack Query, React Hook Form, @hookform/resolvers with Zod, Radix and Tailwind versions accept React 18 (no peer conflicts) | M0 |
| V-05 | `postgres:16` image digest | M0 |
| V-06 | Exact WeasyPrint 70.x patch release; its system packages for the base image; a test PDF renders inside the container with bundled Noto fonts and the ₹ glyph | M0 |
| V-07 | SeaweedFS image and version: tag and digest pinned in `docker-compose.yml`; the configured server command, S3 port and identities-config flag start cleanly | M0 (gate) |
| V-08 | SeaweedFS refuses anonymous S3 requests with the identities config; whether versioning is supported locally (recorded, not required) | M0 (gate) |
| V-09 | boto3 addressing style needed by SeaweedFS (path) and Spaces | M0 / S-02 |
| V-10 | DigitalOcean App Platform spec fields (readiness and liveness checks, PRE_DEPLOY job), managed PostgreSQL 16 and Spaces availability in BLR1, Spaces endpoint and versioning API | S-02 |
| V-11 | The client-IP header that App Platform's proxy sets | S-02 |
| V-12 | The demonstration browser keeps `Secure` cookies on `http://localhost` | M1 |
| V-13 | argon2-cffi default parameters meet or exceed the OWASP minimum for Argon2id | M1 |
| V-14 | PostgreSQL 16 accepts the generated columns on `document_snapshots` (jsonb → text and numeric casts are immutable) | M5 |
| V-15 | The Content-Security-Policy in 12 §4 works with the Vite build and Radix components | M7 |
| V-16 | Font licences (OFL 1.1) are included for all bundled fonts | M0 |
| V-17 | The GST state-code list in 09 §4.4 matches CBIC's current list | Before P1 (P0-Lite uses it for addresses only) |
| V-18 | Bucket initialization: `init-dev-storage` creates the bucket named in `S3_BUCKET` (run once with `.env` and once with `.env.test`), and a second run succeeds without changes | M0 (gate) |
| V-19 | Authenticated PUT and GET: with the application's credentials and boto3 (addressing style per V-09), an object is written and read back byte for byte (equal SHA-256), and HeadBucket succeeds | M0 (gate) |

### 14.1 SeaweedFS verification gate (M0 exit criterion)

SeaweedFS remains the local S3-compatible implementation (team decision, 23 November 2026; C-01). M0 cannot exit until all four gate checks pass, with the results recorded in PROGRESS.md:

1. **Image and version (V-07):** the configured image tag and digest are pinned and start with the configured command and identities file.
2. **Bucket initialization (V-18):** `init-dev-storage` creates the development and test buckets and is safe to re-run.
3. **Authenticated PUT and GET (V-19):** the application's credentials write an object and read it back byte for byte.
4. **Anonymous access refused (V-08):** unauthenticated GET and PUT requests are rejected.

If any check fails, stop and ask the developer (15 §7). Do not switch storage products, add a filesystem fallback or relax authentication to get past the gate.
