# PROGRESS — HIVE DOCS P0-Lite

## Current status

- Active milestone: **M0 complete, awaiting developer review**. M1 has not started.
- Last updated: 2026-11-23 19:00 IST
- Checkpoints: CP1 pending (target Mon 22:30 IST: M0 and M1 done, sign-in works, UT-SEC and IT-AUTH green)

## Milestones

| Milestone | Status | Started | Finished | Tests (pass/total) | Notes |
| --- | --- | --- | --- | --- | --- |
| M0 | Done (pending developer review) | 23 Nov 17:12 | 23 Nov 19:00 | Backend 111/111 · FE-01..FE-03 3/3 | WeasyPrint 70.0 locked; SeaweedFS 4.54 verification gate passed (V-07, V-08, V-18, V-19). Two worker restarts during the session (Docker daemon restarted, no data lost) |
| M1 | Not started | | | | |
| M2 | Not started | | | | |
| M3 | Not started | | | | |
| M4 | Not started | | | | |
| M5 | Not started | | | | |
| M6 | Not started | | | | |
| M7 | Not started | | | | |
| M8 | Not started | | | | |

## Features

| ID | Status (Not started / In progress / Done / Deferred) | Evidence (tests, DC) | Notes |
| --- | --- | --- | --- |
| L-01 | Not started | — | M0 has an honest placeholder page at `/` (replaced in M7) |
| L-02 | Not started | — | M1 |
| L-03 | Not started | — | M1 (the 08 §22 not-found page exists; signed-in links arrive with sessions) |
| L-04 | Not started | — | M2 |
| L-05 | Not started | — | M2 |
| L-06 | Not started | — | M3 |
| L-07 | Not started | — | M3 |
| L-08 | Not started | — | M4 (Spike A proved WeasyPrint + bundled fonts + ₹ in the container) |
| L-09 | Not started | — | M4 |
| L-10 | Not started | — | M5 |
| L-11 | Not started | — | M5 (the SeaweedFS gate proved private storage and authenticated round trips) |
| L-12 | Not started | — | M6 |
| L-13 | Not started | — | M6 |
| L-14 | Not started | — | M1–M6 |
| L-15 | In progress | FE-01..FE-03 | Design tokens, fonts, breakpoints and the reduced-motion base rule are in place; pages arrive M1–M7 |
| L-16 | In progress | IT-HLT-01 (partial), compose stack healthy | Compose with named volumes and 127.0.0.1 ports, E-01/E-02, no committed secrets. DC-17 (persistence across `down`/`up`) is verified in M8 |

## Reduction rules applied

| Rule | Applied at | Reason | Effect on acceptance and demo script |
| --- | --- | --- | --- |
| — | — | None applied | — |

## Decisions and deviations

| Date-time | Decision | Document reference | Approved by |
| --- | --- | --- | --- |
| 23 Nov 17:20 | Documentation baseline copied verbatim from `hive-docs-documentation-v1.1.zip` (20 files, SHA-256 verified). The separate `CONSISTENCY_AUDIT.md` is byte-identical to the one in the ZIP | 15 §1 | — (no change) |
| 23 Nov 17:35 | SeaweedFS pinned to **4.54** (tag + digest), not 4.55, which was published the same morning; one week of release exposure is preferred | 05 §1, V-07 | Claude Code (implementation detail; developer to confirm) |
| 23 Nov 17:40 | SeaweedFS flags: `-s3.autoCreateBucket=false` (buckets exist only through `init-dev-storage`, as on Spaces); `-s3.iam=false` (embedded IAM API not needed); `-master.telemetry=false` (the image phones home by default; the local stack makes no outbound calls); `-ip=storage -ip.bind=0.0.0.0` (stable identity across restarts) | 05 §7.2 ("along the lines of"), 04 §1, 05 §13.1 | Claude Code (developer to confirm) |
| 23 Nov 17:40 | Two S3 identities, one per bucket: `ps5-dev` → `ps5-documents-dev`, `ps5-test` → `ps5-documents-test`, each with bucket-scoped Admin/Read/Write/List only | 12 §8 ("separate per environment, limited to the one bucket") | Claude Code (developer to confirm) |
| 23 Nov 17:45 | `deploy/seaweedfs/s3.json` must be readable by the container's `seaweed` user (uid 1000): mode 0644, which is what the documented `cp` produces | 05 §6.2 | Claude Code |
| 23 Nov 17:50 | `.env` targets host-run tools (`localhost`); `docker-compose.yml` overrides `DATABASE_URL`, `MIGRATION_DATABASE_URL` and `S3_ENDPOINT_URL` for the `app` container (hosts `db` and `storage`), built from the same `.env` passwords | 05 §7.2, §9, §10 | Claude Code (developer to confirm) |
| 23 Nov 18:00 | Settings: a repository-root `.env` is read as a fallback for host-run tools; real environment variables always win; the image contains no `.env`. `CSRF_SECRET` length is measured on the decoded key when the value is hex (64 hex characters = 32 bytes), otherwise on its UTF-8 bytes; the same key bytes will key the HMAC in M1 | 05 §9, 12 §4.2 | Claude Code (developer to confirm) |
| 23 Nov 18:00 | **Open question:** the documents define no code for 405 Method Not Allowed. Interim: answered as problem+json **404 `not_found`** (an existing catalogue pair) | 07 §1.5, §1.12 | **Needs developer confirmation** |
| 23 Nov 18:05 | SPA serving: `/`, `/login`, `/app/...` → `index.html` 200; other non-API paths → `index.html` with HTTP **404** (the SPA renders its not-found page; `/docs` is 404 outside development, 12 §17); unknown `/api/...` → problem+json 404 | 04 §2, 08 §12.1, §22 | Claude Code |
| 23 Nov 18:05 | `/readyz` reports `database` and `storage` in M0; the `templates` check is added with the template registry in M4 | 10 §3 M0.3, 07 E-02 | — (as documented) |
| 23 Nov 18:05 | `Cache-Control: no-store` on every response except `/assets/*` (`public, max-age=31536000, immutable`) | 07 §1.10, 04 §2 | Claude Code |
| 23 Nov 18:05 | Middleware: one outer ASGI middleware sets the request ID, security headers and Cache-Control, and turns unhandled exceptions into a 500 problem response (so it carries the headers too); then the 256 KiB body limit. The Origin/CSRF check slots in between in M1 | 04 §5 | Claude Code |
| 23 Nov 18:20 | Node.js **22 LTS** (22.23.5, same as this host's toolchain) for the image's build stage | 05 §7.1, V-02 | Claude Code (developer to confirm) |
| 23 Nov 18:20 | Frontend versions: react-router **7.18.6** (8.x requires React 19); TypeScript **5.9.3** (typescript-eslint needs `<6.1`; docs say 5.x); Radix as the umbrella `radix-ui` package (05 §3: "choose one in M0") | 05 §1, §3, V-04 | Claude Code |
| 23 Nov 18:25 | The frontend was written by hand instead of trimming the `create-vite` template, which installs React 19, TypeScript 7, oxlint and `@types/node` (none approved) | 05 §3, V-03 | Claude Code |
| 23 Nov 18:45 | **`@hookform/resolvers` pinned to 5.2.2 instead of 7.0.8.** Releases from 5.9 onwards declare about 20 optional peers including `ajv ^8`; next to ESLint's `ajv@6`, npm 10.9.9 writes a lockfile that its own `npm ci` rejects (EUSAGE), which broke the image build. 5.2.2 declares only `react-hook-form ^7.55.0`, ships the zod entry point, and `zodResolver` type-checks with zod 4.6.7. The alternative was `legacy-peer-deps=true` (disables peer checks for the whole project) | 05 §2 (`npm ci` in Docker), §3, V-04 | **Needs developer acknowledgement** |
| 23 Nov 18:25 | ESLint enforces two 15 §8 constraints: no `localStorage`/`sessionStorage`, no `dangerouslySetInnerHTML` | 15 §8 | Claude Code |
| 23 Nov 18:25 | Tailwind theme exposes only the 08 §4 colour tokens (default palette removed); breakpoints `md` 768 px and `lg` 1280 px | 08 §4, §6 | Claude Code |
| 23 Nov 18:50 | Dockerfile: `uv sync --no-cache` (keeps uv's download cache out of the image: 696 MB → 476 MB); `XDG_CACHE_HOME=/tmp/.cache` set after the build steps (fontconfig needs a writable cache for the home-less runtime user); `uvicorn --no-proxy-headers` | 05 §7.1, 12 §2.2 | Claude Code |
| 23 Nov 18:15 | Fonts downloaded from the official repositories (Noto project, rsms/inter, adobe-fonts/source-serif) through raw.githubusercontent.com; provenance, versions and SHA-256 in each `FONTS.md` | 05 §5, V-16 | Claude Code |
| 23 Nov 18:30 | Spike A tooling kept at `backend/scripts/spike_weasyprint.py` (not part of 05 §4; excluded from the image by `.dockerignore`) | 10 §3 M0.4 | Claude Code |
| 23 Nov 17:40 | Compose project name `ps5` so the volume names (`ps5_pgdata`, `ps5_seaweed_data`) do not depend on the checkout folder's name (backups in M8) | 05 §7.2, 10 §7 | Claude Code |
| 23 Nov 18:55 | Cloud environment `helovy` (personal) created for this repository, allowing `deb.debian.org` (the default environment's proxy refused it, blocking the image's apt step), with a setup script that runs `uv sync --frozen` and `npm ci` | — (development environment, not product) | Developer (approval card) |

## Dependencies added (with approval)

All packages are on the approved list in docs/05 §3; no package outside it was added.

| Package | Version | Reason | Approved by |
| --- | --- | --- | --- |
| fastapi | 0.165.0 | Backend runtime | docs/05 §3 |
| uvicorn[standard] | 0.54.0 | Backend runtime (one worker) | docs/05 §3 |
| pydantic / pydantic-settings | 2.14.4 / 2.16.3 | Schemas, settings | docs/05 §3 |
| sqlalchemy | 2.0.58 | ORM (`>=2.0,<2.1`) | docs/05 §3 |
| psycopg[binary] | 3.3.9 | PostgreSQL driver | docs/05 §3 |
| alembic | 1.20.1 | Migrations (from M1) | docs/05 §3 |
| argon2-cffi | 25.1.0 | Password hashing (from M1) | docs/05 §3 |
| jinja2 | 3.1.6 | Templates (from M4) | docs/05 §3 |
| weasyprint | 70.0 | PDF (`>=70.0,<71`; exact patch locked, V-06) | docs/05 §3 |
| boto3 | 1.44.9 | S3 client | docs/05 §3 |
| pytest / hypothesis / httpx / ruff / mypy | 9.2.0 / 6.170.17 / 0.28.1 / 0.17.6 / 2.4.1 | Backend development | docs/05 §2–§3 |
| react / react-dom | 18.3.1 / 18.3.1 | Frontend runtime (pinned, V-03) | docs/05 §3 |
| react-router | 7.18.6 | Routing (React 18 compatible, V-04) | docs/05 §3 |
| @tanstack/react-query | 5.108.3 | Server state | docs/05 §3 |
| react-hook-form / @hookform/resolvers / zod | 7.92.0 / 5.2.2 / 4.6.7 | Forms (from M1) | docs/05 §3 (resolver version: see decisions) |
| radix-ui | 1.8.1 | Accessible primitives (umbrella package) | docs/05 §3 |
| typescript / vite / @vitejs/plugin-react | 5.9.3 / 8.3.8 / 6.3.0 | Frontend development | docs/05 §3 |
| tailwindcss / @tailwindcss/vite | 4.3.5 / 4.3.5 | Styling | docs/05 §3 |
| eslint / typescript-eslint / eslint-plugin-react-hooks | 10.15.0 / 8.73.0 / 7.1.1 | Linting | docs/05 §3 |
| @types/react / @types/react-dom | 18.3.31 / 18.3.7 | Types | docs/05 §3 |
| Images | `postgres:16@sha256:3950ad7c…` (16.16) · `chrislusf/seaweedfs:4.54@sha256:4b42c212…` · `python:3.12-slim@sha256:5e2bdb1b…` (3.12.16, Debian 13) · `node:22-slim@sha256:e9f565d3…` (22.23.5) | Runtime and build | docs/05 §1, §7 |
| uv | 0.11.32 | Image build only (removed from the image) | docs/05 §2 |
| Fonts | Noto Sans 2.015, Noto Sans Devanagari 2.007, Inter 4.001, Source Serif 4 4.005 (all OFL 1.1) | PDF and UI fonts | docs/05 §1 |

## Verification items (V-xx)

| ID | Result | Notes |
| --- | --- | --- |
| V-01 | Pass | uv 0.11.32: `uv init --app --python 3.12`, `uv add`, `uv add --dev`, `uv sync --frozen` work as documented |
| V-02 | Pass | Node 22.23.5 (LTS) satisfies Vite 8.3.8 `engines` (`^20.19.0 \|\| >=22.12.0`); `node:22-slim` pinned by digest |
| V-03 | Pass (confirmed) | `npm create vite` (react-ts) installs React 19 (`^19.3.1`), TypeScript 7 and oxlint. The project pins react, react-dom 18.3.1 and @types/react(-dom) 18.x |
| V-04 | Pass | One `react@18.3.1` in the whole tree; no invalid or unmet non-optional peers (`npm ls --all`). react-router 8 needs React 19 → 7.18.6; resolver pin, see decisions |
| V-05 | Pass | `postgres:16@sha256:3950ad7c3148ca2175ef1b6c36c9efbf78957ae8fbe8b3a5d7c35af50500382f` = PostgreSQL 16.16 (Debian 13) |
| V-06 | Pass | WeasyPrint 70.0, Pango 1.56.3, on `python:3.12-slim` (Debian 13) with `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0` (WeasyPrint 70 guide, Debian ≥ 11, wheels); no Ghostscript. In the image, with `--network none`: 1-page A4 PDF-1.7 (12,003 bytes, SHA-256 `3169df59…752d`); embedded fonts are only Noto Sans Regular/Bold and Noto Sans Devanagari; ₹ present 6× and visible in the rendered page; exact SPECIMEN text in the footer; no stderr output |
| V-07 | **Pass (gate 1)** | `chrislusf/seaweedfs:4.54@sha256:4b42c212543a0acd4c0e675215ecdcaf62a186ef98def76c7e12701871222d15` (`weed` 4.54 5ef99c1d8). The configured command starts healthy as user `seaweed`; S3 on 8333, published on 127.0.0.1 only; data survives a container restart (object SHA-256 equal). It fails closed (fatal, exit 255) if `s3.json` is unreadable or is a directory |
| V-08 | **Pass (gate 4)** | Unauthenticated requests refused with 403 `AccessDenied`: GET and PUT of an existing object (the object stays unchanged), ListBuckets, ListObjects, CreateBucket, DeleteBucket; an unsigned boto3 client gets `AccessDenied`. Versioning **is** supported locally (Enabled on both buckets) |
| V-09 | Pass (local part) | Path-style addressing works with SeaweedFS using boto3 1.44.9 defaults (including its default checksums). The Spaces part belongs to S-02 |
| V-16 | Pass | OFL 1.1 texts next to every bundled font (`OFL.txt`, `OFL-NotoSansDevanagari.txt`, `Inter-LICENSE.txt`, `SourceSerif4-LICENSE.md`); provenance and SHA-256 in `FONTS.md` |
| V-18 | **Pass (gate 2)** | `init-dev-storage` created `ps5-documents-dev` (`.env`) and `ps5-documents-test` (`.env.test`) with versioning Enabled; second runs say "already exists (left unchanged)", exit 0; also from inside the app container; refuses `APP_ENV=production` (exit 2, before contacting storage). Automated: `test_v18_*` (recreates the test bucket on every run) |
| V-19 | **Pass (gate 3)** | With the app's credentials and `create_s3_client`: PUT/GET of 256 KiB byte-identical, SHA-256 equal, HeadBucket OK, for both identities. Each identity is refused (403) on the other's bucket. Automated: `test_v19_*`, `test_credentials_are_limited_to_their_own_bucket` |
| V-10–V-15, V-17 | Not run | Not in M0 scope (S-02, M1, M5, M7, before P1) |

## Known issues

| Severity (S1–S4) | Description | Status |
| --- | --- | --- |
| S3 | SeaweedFS's internal ports (master 9333, volume 8080, filer 8888/18888, including an unauthenticated filer IAM gRPC service) are reachable inside the compose network. They are not published to the host; only the app and database containers share the network. Local development only (the cloud uses Spaces). Possible mitigation: JWT keys in a SeaweedFS `security.toml` | Open (accepted for local) |
| S4 | The image was built in this sandbox through a derived Dockerfile that adds proxy/CA plumbing to 3 `RUN` lines (bind mounts only; verified no residue in the image). **The committed `Dockerfile` still needs one build on the developer machine** | Open (developer action) |
| S4 | Starlette deprecates `httpx` for `TestClient` in favour of `httpx2` (one warning per test run). `httpx` is the approved package (05 §2) | Open; no change without approval |
| S4 | In development, the FastAPI docs UI cannot load its CDN assets because of the CSP (12 §4.3); `/openapi.json` works. The docs UI is off in demo and production | Open (by design) |
| S4 | Access log labels FastAPI's dev-only `/docs` routes as `unmatched` | Open (cosmetic) |
| S4 | Image size 476 MB (Pango, HarfBuzz and the Python dependencies) | Open |
| S4 | The `helovy` cloud environment's setup script is unproven until a fresh session starts on it | Open |

## Demonstration checks (filled in M8)

| DC | Pass / Fail / Deferred | Notes |
| --- | --- | --- |
| DC-01 to DC-20 | Not run | M8 |

## Next steps

- Developer: review the M0 report and this file; confirm the two flagged decisions (405 → 404; `@hookform/resolvers` 5.2.2).
- Developer: run `docker build -t hive-docs:local .` and `docker compose up -d` once on the presenter laptop (no sandbox plumbing there).
- Developer: authorise a push of branch `claude/busy-bell-14l7rh` if wanted (this cloud container is ephemeral; the M0 commit is local only).
- M1 (database, authentication, app shell) when authorised: migration `0001_identity`, Argon2id, sessions, CSRF, E-03 to E-05, `create-demo-account`, login page, shell.
