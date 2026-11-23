# PROGRESS — HIVE DOCS P0-Lite

## Current status

- Active milestone: **M0, implemented and corrected, committed and pushed; acceptance conditional on the outstanding Docker verification** (see "M0 acceptance status"). M1 has not started.
- Last updated: 2026-11-23 22:55 IST (reconciled with the actual repository state)
- Checkpoints: **CP1 (Mon 22:30 IST) missed**: M0 is complete apart from the Docker verification, and M1 has not started. Documented response (10 §6.1): stop for the night, finish M1 first thing Tuesday, apply R5. Applying a reduction rule is the developer's decision (10 §9); R5 is not applied.
- Git (verified 22:52 IST): branch `claude/busy-bell-14l7rh` at `0ea973c` "M0: HTTP 405 and HEAD corrections", parent `5402bf9` "M0: foundation and risk spikes". Both commits are pushed to `origin` (github.com/adithyad-cs/helovy); the branch is synchronized (0 ahead, 0 behind); the working tree was clean before this reconciliation; no tags. The developer verified the local Windows checkout against GitHub. This reconciliation of PROGRESS.md is an uncommitted change awaiting developer approval.
- Environments: automated evidence in this file comes from the **cloud development container** (Linux) unless marked **native Windows**; see "Verification evidence by environment".

## M0 acceptance status

| Item | Status |
| --- | --- |
| Implementation | Complete: `5402bf9` (M0.1–M0.6) and `0ea973c` (405 and HEAD review corrections), both committed and pushed |
| Automated evidence (cloud container) | Backend 180/180, including the SeaweedFS gate 6/6; ruff, format and mypy `--strict` clean; FE-01, FE-02, FE-03 pass; documentation consistency checks 15/15 |
| Outstanding | **Clean Docker build of the committed Dockerfile, and Compose verification of the current code: BLOCKED / UNVERIFIED** in both available environments (see "Verification items") |
| Acceptance | **Conditional.** Every M0 exit criterion is met except the Docker verification (criteria 1 and 8 below). Formal M0 approval is not recorded |

| # | M0 exit criterion | Status | Evidence and environment |
| --- | --- | --- | --- |
| 1 | `docker compose up` starts the documented stack | Partial | Cloud container: stack healthy with the image built through the sandbox-derived Dockerfile from `5402bf9` code. Not verified with an image of the committed Dockerfile, nor with the `0ea973c` code |
| 2 | `/healthz` returns 200 | Pass | Cloud container: the app container (`5402bf9` image) and a host uvicorn running the current code |
| 3 | `/readyz` returns 200 | Pass | Cloud container: same as criterion 2 |
| 4 | The SPA loads | Pass | Cloud container: app container, host uvicorn and headless Chromium (no CSP violations, fonts loaded) |
| 5 | Risk spike A (WeasyPrint) passes | Pass | Cloud container image (V-06, V-16). Native Windows smoke test also passed (developer-reported, informational) |
| 6 | SeaweedFS verification gate passes | Pass | Cloud container (V-07, V-08, V-18, V-19; 6/6 automated) |
| 7 | Required M0 tests pass | Pass | Cloud container: IT-HLT-01 (partial), FE-01 to FE-03; full backend suite 180/180 |
| 8 | The local Docker image works | **Outstanding (BLOCKED)** | Only the sandbox-derived image was built and run. The committed Dockerfile has never been built: blocked in the cloud container (no DNS or egress for build containers) and on the Windows laptop (Docker Desktop unavailable) |
| 9 | PROGRESS.md updated with evidence | Pass | This file (this reconciliation awaits approval) |
| 10 | Final diff reviewed | Pass | Reviewed before `5402bf9` and before `0ea973c` |

## Verification evidence by environment

| Environment | What was verified | Result | Source |
| --- | --- | --- | --- |
| Cloud development container (Linux; Docker 29.10 with Compose; Python 3.12.3 on the host, 3.12.16 in the image; Node 22.23.5) | Backend 180/180 including the SeaweedFS gate 6/6; ruff, format, mypy `--strict`; FE-01 to FE-03; documentation checks 15/15; Spike A inside the image; the SeaweedFS gate against the Compose service; live HTTP checks with uvicorn. The image was built only through the sandbox-derived Dockerfile | Pass, except the clean build (BLOCKED) | Claude Code session runs recorded in this file |
| Native Windows laptop | The local Git checkout matches GitHub (`0ea973c`, clean, synchronized) | Pass | Developer-reported, 23 Nov |
| Native Windows laptop | WeasyPrint 70.0 installed under Python 3.12.10; a generated PDF opened correctly. Does not by itself establish rendering with the bundled Noto fonts and ₹, or the restricted fetcher (V-06 covers those for the container image; native rendering of the project templates starts in M4) | Pass (smoke test) | Developer-reported, 23 Nov |
| Native Windows laptop | Docker Desktop reports hardware virtualization disabled; BIOS access is blocked by an unknown administrator password; no further BIOS attempt | Docker unavailable | Developer-reported, 23 Nov |
| Native Windows laptop | Not run natively yet: the backend test suite (needs PostgreSQL 16 and an S3-compatible endpoint), FE-01 to FE-03 | Not run | — |
| Both environments | Clean Docker build of the committed Dockerfile; Compose with that image | **BLOCKED / UNVERIFIED** | — |

## Temporary native-Windows development arrangement (approved by the developer, 23 Nov)

- **Reason:** Docker Desktop cannot run on the developer's Windows laptop (hardware virtualization disabled; BIOS access blocked by an unknown administrator password). No further BIOS attempt will be made.
- **Arrangement:** development may continue natively on that laptop (Python 3.12.10; WeasyPrint 70.0 verified by a native smoke test).
- **Unchanged:** the approved product architecture (04), the approved stack and dependencies (05 §1, §3), the Dockerfile and docker-compose.yml. Docker Compose remains the documented local runtime (05 §7) and the demonstration runtime (D-1, 10 §8).
- **Evidence rule:** results obtained natively on Windows are recorded separately from cloud-container results. Neither replaces the clean Docker build and Compose verification, which stay outstanding.
- **Not yet recorded (needed before M1 runs natively):** how a PostgreSQL 16 server with `ps5`, `ps5_test`, `ps5_migrator` and `ps5_app` (06 §11; the role and grant model of `deploy/postgres/init`) and a SeaweedFS S3 endpoint (ADR-13) are provided without Docker. The documented setup starts both with Docker Compose (05 §6.2, §10). Until the developer records a choice, the cloud container remains the environment where the full backend suite runs.

## Final M0 documentation cleanup (23 Nov, 19:45 IST)

| Item | Status | Evidence |
| --- | --- | --- |
| 14 §6 decision #10 (GET/HEAD contract, RFC 9110 §9.1 and §9.3.2) | Done | Row added after #9; no other change to 14 |
| Consistent record of the 1.2 HEAD correction | Done | README version history (14: decisions #9 and #10); CONSISTENCY_AUDIT §2.1 HEAD row and §3.1 (reason and 14 row); this file. 07 §1.13, §1.14, §2 and 11 IT-GEN-01 already recorded it and needed no change |
| Documentation consistency checks | Pass | 15/15 on the final package (cloud container) |
| Git diff review, `git diff --check`, secret scan | Done | All 18 files, uncommitted at the time (16 modified, 2 new); committed later as `0ea973c` |
| `5402bf9` unmodified | Verified | At 19:45 HEAD was still `5402bf9`, with no commit, push, tag, reset, amend or rebase. `0ea973c` was committed on top of it at 19:52 and pushed, as authorised by the developer |

## Final M0 review: HEAD support (23 Nov, 19:28–19:40 IST)

| Item | Status | Evidence |
| --- | --- | --- |
| 1. HEAD on every GET resource | Done | `/healthz`, `/readyz`, SPA pages, root files, static assets, development docs. Same status and headers as GET, no body (0 bytes on the wire with uvicorn), endpoint runs once, `Allow` lists `GET, HEAD` |
| 2. Documentation 1.2 | Done | 07 §1.13 examples, new §1.14, §2 note; 11 IT-GEN-01; README 1.2 row; CONSISTENCY_AUDIT §1, §2.1, §3.1. 08: no change required. 14 §6: decision #10 added in the final documentation cleanup (see below) |
| 3. Regression | Pass | Cloud container: backend 180/180 (155 previous + 25 HEAD; gate 6/6); ruff, format, mypy `--strict` clean; FE-01, FE-02, FE-03 pass; documentation checks 15/15 |
| 4. Docker | **BLOCKED** (unchanged) | Not retried, as instructed; the Dockerfile is unchanged |
| 5. Git safety | Done | During this review `5402bf9` stayed untouched, with no commit, push or tag; the corrections were committed later as `0ea973c` and pushed |

## M0 review corrections, first round (23 Nov, 19:05–19:25 IST)

| Item | Status | Evidence |
| --- | --- | --- |
| 1. HTTP 405 | Done | 405 `method_not_allowed` with `Allow` (problem+json); documentation 1.2; tests below |
| 2. `@hookform/resolvers` 5.2.2 | Accepted by the developer | Lockfile unchanged (`git diff` empty); `npm ci` clean |
| 3. Clean `docker build -t hive-docs:local .` | **BLOCKED** (environment) | Exact reasons in "Verification items"; the Compose check with a clean image is therefore NOT RUN |
| 4. Regression | Pass | Cloud container: backend 155/155 (gate 6/6); ruff, format, mypy `--strict` clean; FE-01, FE-02, FE-03 pass |
| 5. Git safety | Done | During this review `5402bf9` stayed untouched, with no new commit, push or tag; the corrections were committed later as `0ea973c` and pushed |

## API contract changes

| Date-time | Change | Before | After | Reason | Documents | Approved by |
| --- | --- | --- | --- | --- | --- | --- |
| 23 Nov 19:10 | Unsupported methods | The documents were silent; the M0 build answered a known path with an unsupported method as 404 `not_found` | **405 `method_not_allowed`** (RFC 9457 problem+json) with an **`Allow`** header listing every method of the path across all its routes (for example `Allow: GET` on `/healthz`; `Allow: GET, HEAD` on `/assets/...`). Decided from the route and method alone, before any session, tenant or record lookup, so the response is the same for every ID. A path that matches no route stays 404 for every method; missing and foreign records stay 404. Body limit (413) and, from M1, Origin/CSRF (403) still come first | RFC 9110 §15.5.6; developer's M0 review rejected the 404 mapping | Documentation 1.2: 07 §1.10, §1.12, §1.13; 08 §21; 11 IT-GEN-01; 14 §6 #9; README version history; CONSISTENCY_AUDIT §2.1, §3.1. Error catalogue 24 → 25 codes | Developer (review instruction) |
| 23 Nov 19:30 | HEAD requests | FastAPI routes answered HEAD with 405 `Allow: GET` (only static assets and the docs routes answered HEAD) | **Every GET resource answers HEAD**: same status and header fields as GET (`Content-Type`, `Content-Length`, `ETag`, `Last-Modified`, `Cache-Control`, security headers, `X-Request-ID`), no body. Same middleware, authentication, scoping and lookups as GET; the endpoint runs once, with no side effects (for example no `document.pdf_downloaded` event for E-22 in M5); HEAD counts toward the GET rate limits; no CSRF token. `Allow` lists HEAD wherever it lists GET (`Allow: GET, HEAD` on `/healthz`; `GET, HEAD, PATCH` on a path with GET and PATCH routes). Unknown resources keep 404; unsupported methods keep 405 | RFC 9110 §9.1 (general-purpose servers support GET and HEAD) and §9.3.2; developer's final M0 review | Documentation 1.2: 07 §1.13 (examples), new §1.14, §2 note; 11 IT-GEN-01; README version history; CONSISTENCY_AUDIT §1, §2.1, §3.1. 08 unchanged (SPA sends no HEAD). 14 §6 decision #10 (added in the final documentation cleanup) | Developer (review instruction) |

## Milestones

| Milestone | Status | Started | Finished | Tests (pass/total) | Notes |
| --- | --- | --- | --- | --- | --- |
| M0 | Implemented and corrected; committed and pushed (`5402bf9`, `0ea973c`); acceptance conditional: Docker verification outstanding | 23 Nov 17:12 | 23 Nov 19:00 (corrections committed 19:52) | Backend 180/180 · FE-01..FE-03 3/3 (cloud container) | WeasyPrint 70.0 locked; SeaweedFS 4.54 verification gate passed (V-07, V-08, V-18, V-19). Reviews: 405 and HEAD contracts added (docs 1.2). The clean build of the committed Dockerfile and the Compose verification are BLOCKED in the cloud container and cannot run on the developer's Windows laptop. Two worker restarts during the session (Docker daemon restarted, no data lost) |
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
| L-08 | Not started | — | M4 (Spike A proved WeasyPrint + bundled fonts + ₹ in the cloud container image; a native Windows WeasyPrint smoke test also passed, developer-reported) |
| L-09 | Not started | — | M4 |
| L-10 | Not started | — | M5 |
| L-11 | Not started | — | M5 (the SeaweedFS gate proved private storage and authenticated round trips) |
| L-12 | Not started | — | M6 |
| L-13 | Not started | — | M6 |
| L-14 | Not started | — | M1–M6 |
| L-15 | In progress | FE-01..FE-03 | Design tokens, fonts, breakpoints and the reduced-motion base rule are in place; pages arrive M1–M7 |
| L-16 | In progress | IT-HLT-01 (partial); Compose stack healthy in the cloud container with the sandbox-derived image of `5402bf9` code | Compose with named volumes and 127.0.0.1 ports, E-01/E-02, no committed secrets. The clean build of the committed Dockerfile and Compose with the current code are outstanding (BLOCKED). DC-17 (persistence across `down`/`up`) is verified in M8 |

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
| 23 Nov 18:00 | ~~Open question: 405 answered as 404 `not_found`~~ **Superseded at 19:10** by the 405 correction below (rejected in the developer's M0 review) | 07 §1.5, §1.12 | Rejected by the developer |
| 23 Nov 19:10 | **405 correction:** unsupported method on an existing route → 405 `method_not_allowed` with `Allow` (union of the methods of every route serving the path, computed in `app/core/errors.py`, because Starlette reports only the first matching route); problem+json; new catalogue code. See "API contract changes" | RFC 9110 §15.5.6; 07 §1.13 (docs 1.2) | Developer (review instruction) |
| 23 Nov 19:10 | **SPA catch-all route removed.** A `GET /{path}` catch-all made every unknown path "exist", so `POST /unknown` or `DELETE /api/v1/nope` would have become 405 instead of 404. Now: explicit GET routes for `/`, `/login`, `/app`, `/app/{rest}` and the build's root files; a 404 handler serves the SPA's `index.html` with status 404 for a GET of any other non-API, non-asset path; everything else that matches no route → problem+json 404 | 04 §2, 07 §1.13, 08 §12.1, §22 | Claude Code (implements the developer's instruction to preserve 404) |
| 23 Nov 19:10 | **Two tests replaced, none weakened or skipped:** `test_method_not_allowed_is_answered_as_not_found` asserted the rejected 405→404 mapping and is replaced by tests asserting 405 + `Allow`; `test_catalogue_has_the_24_documented_codes` becomes `..._25_...` for the documented 25-code catalogue. 45 test cases added, so 111 → 155 net (405 on health and SPA routes, assets `Allow: GET, HEAD`, union `Allow` across two routes, same 405 for every ID while a missing record stays 404, 404 for unknown paths on every method) | 15 §8 (tests), 11 IT-GEN-01 (docs 1.2) | Developer (review instruction) |
| 23 Nov 19:30 | **HEAD implementation:** `app/core/routing.py` `HeadAwareRoute` (used by the app router and every module router) matches HEAD wherever it matches GET and runs the GET endpoint **once** with `request.method == "HEAD"`, so endpoints can skip side effects; the routes still declare only GET, so OpenAPI lists no duplicate HEAD operations. `RequestContextMiddleware` (outermost) drops every HEAD response body, including error responses, and keeps the GET status and headers; `Content-Length` stays the GET value. The SPA not-found page answers HEAD like GET | 07 §1.14; RFC 9110 §9.1, §9.3.2 | Developer (review instruction) |
| 23 Nov 19:32 | **Latent 405 bug found and fixed:** FastAPI 0.165 keeps included routers as a single internal `_IncludedRouter` route, so the first-round `Allow` union missed every route inside included routers (`/healthz` fell back to Starlette's single-route header; module routers from M1 would have been wrong). `Allow` is now computed by probing each standard method through the public `matches()` interface of every top-level route, so it lists exactly what the router serves, nested routers included. Static mounts keep their explicit GET/HEAD rule | 07 §1.13 | Claude Code (fix within the approved 405 contract) |
| 23 Nov 19:35 | **Tests for HEAD:** 25 cases added (`tests/integration/test_head.py`). The expected `Allow` value changed from `GET` to `GET, HEAD` (and `GET, PATCH` to `GET, HEAD, PATCH`) in 27 earlier cases of 4 functions, as the new requirement demands; test function names unchanged. The 2 parametrized CSRF-secret cases got fixed IDs (`hex-31-bytes`, `text-31-bytes`) because their IDs embedded a random value and changed every run; assertions unchanged. Nothing removed, skipped or weakened | 11 IT-GEN-01; 15 §8 | Developer (review instruction) |
| 23 Nov 18:05 | SPA serving: `/`, `/login`, `/app/...` → `index.html` 200; other non-API paths → `index.html` with HTTP **404** (the SPA renders its not-found page; `/docs` is 404 outside development, 12 §17); unknown `/api/...` → problem+json 404. (Implementation changed at 19:10: no catch-all route; see above) | 04 §2, 08 §12.1, §22 | Claude Code |
| 23 Nov 18:05 | `/readyz` reports `database` and `storage` in M0; the `templates` check is added with the template registry in M4 | 10 §3 M0.3, 07 E-02 | — (as documented) |
| 23 Nov 18:05 | `Cache-Control: no-store` on every response except `/assets/*` (`public, max-age=31536000, immutable`) | 07 §1.10, 04 §2 | Claude Code |
| 23 Nov 18:05 | Middleware: one outer ASGI middleware sets the request ID, security headers and Cache-Control, and turns unhandled exceptions into a 500 problem response (so it carries the headers too); then the 256 KiB body limit. The Origin/CSRF check slots in between in M1 | 04 §5 | Claude Code |
| 23 Nov 18:20 | Node.js **22 LTS** (22.23.5, same as this host's toolchain) for the image's build stage | 05 §7.1, V-02 | Claude Code (developer to confirm) |
| 23 Nov 18:20 | Frontend versions: react-router **7.18.6** (8.x requires React 19); TypeScript **5.9.3** (typescript-eslint needs `<6.1`; docs say 5.x); Radix as the umbrella `radix-ui` package (05 §3: "choose one in M0") | 05 §1, §3, V-04 | Claude Code |
| 23 Nov 18:25 | The frontend was written by hand instead of trimming the `create-vite` template, which installs React 19, TypeScript 7, oxlint and `@types/node` (none approved) | 05 §3, V-03 | Claude Code |
| 23 Nov 18:45 | **`@hookform/resolvers` pinned to 5.2.2 instead of 7.0.8.** Releases from 5.9 onwards declare about 20 optional peers including `ajv ^8`; next to ESLint's `ajv@6`, npm 10.9.9 writes a lockfile that its own `npm ci` rejects (EUSAGE), which broke the image build. 5.2.2 declares only `react-hook-form ^7.55.0`, ships the zod entry point, and `zodResolver` type-checks with zod 4.6.7. The alternative was `legacy-peer-deps=true` (disables peer checks for the whole project) | 05 §2 (`npm ci` in Docker), §3, V-04 | **Accepted by the developer for M0** (M0 review, 23 Nov). Lockfile kept unchanged; no upgrade |
| 23 Nov 18:25 | ESLint enforces two 15 §8 constraints: no `localStorage`/`sessionStorage`, no `dangerouslySetInnerHTML` | 15 §8 | Claude Code |
| 23 Nov 18:25 | Tailwind theme exposes only the 08 §4 colour tokens (default palette removed); breakpoints `md` 768 px and `lg` 1280 px | 08 §4, §6 | Claude Code |
| 23 Nov 18:50 | Dockerfile: `uv sync --no-cache` (keeps uv's download cache out of the image: 696 MB → 476 MB); `XDG_CACHE_HOME=/tmp/.cache` set after the build steps (fontconfig needs a writable cache for the home-less runtime user); `uvicorn --no-proxy-headers` | 05 §7.1, 12 §2.2 | Claude Code |
| 23 Nov 18:15 | Fonts downloaded from the official repositories (Noto project, rsms/inter, adobe-fonts/source-serif) through raw.githubusercontent.com; provenance, versions and SHA-256 in each `FONTS.md` | 05 §5, V-16 | Claude Code |
| 23 Nov 18:30 | Spike A tooling kept at `backend/scripts/spike_weasyprint.py` (not part of 05 §4; excluded from the image by `.dockerignore`) | 10 §3 M0.4 | Claude Code |
| 23 Nov 17:40 | Compose project name `ps5` so the volume names (`ps5_pgdata`, `ps5_seaweed_data`) do not depend on the checkout folder's name (backups in M8) | 05 §7.2, 10 §7 | Claude Code |
| 23 Nov 18:55 | Cloud environment `helovy` (personal) created for this repository, allowing `deb.debian.org` (the default environment's proxy refused it, blocking the image's apt step), with a setup script that runs `uv sync --frozen` and `npm ci` | — (development environment, not product) | Developer (approval card) |
| 23 Nov 19:52 | The reviewed corrections were committed as `0ea973c` "M0: HTTP 405 and HEAD corrections" (18 files; parent `5402bf9`), and branch `claude/busy-bell-14l7rh` was pushed to `origin` with upstream tracking. No force push; nothing on `main`. The repository had no branches before, so GitHub made this branch its default branch | 15 §4 | Developer (authorisation after review) |
| 23 Nov 22:55 (recorded) | **Temporary native-Windows development arrangement:** development may continue natively on the developer's Windows laptop while Docker cannot run there. The product architecture, stack, Dockerfile and docker-compose.yml are unchanged; native results are recorded separately from cloud-container results (see the section near the top of this file) | — (development environment, not product; 04 and 05 unchanged) | Developer |
| 23 Nov 22:55 (recorded) | Docker is unavailable on the developer's Windows laptop (hardware virtualization disabled; BIOS access blocked by an unknown administrator password; no further BIOS attempt). The clean Docker build and the Compose verification remain BLOCKED / UNVERIFIED and are not marked as passed | 10 §8 (D-1), 05 §7 | Developer (reported) |

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
| react-hook-form / @hookform/resolvers / zod | 7.92.0 / 5.2.2 / 4.6.7 | Forms (from M1). Resolver 5.2.2: the only release line whose peer set lets npm 10's lockfile pass `npm ci` next to ESLint's `ajv@6` | docs/05 §3; resolver 5.2.2 **accepted by the developer** (M0 review, 23 Nov) |
| radix-ui | 1.8.1 | Accessible primitives (umbrella package) | docs/05 §3 |
| typescript / vite / @vitejs/plugin-react | 5.9.3 / 8.3.8 / 6.3.0 | Frontend development | docs/05 §3 |
| tailwindcss / @tailwindcss/vite | 4.3.5 / 4.3.5 | Styling | docs/05 §3 |
| eslint / typescript-eslint / eslint-plugin-react-hooks | 10.15.0 / 8.73.0 / 7.1.1 | Linting | docs/05 §3 |
| @types/react / @types/react-dom | 18.3.31 / 18.3.7 | Types | docs/05 §3 |
| Images | `postgres:16@sha256:3950ad7c…` (16.16) · `chrislusf/seaweedfs:4.54@sha256:4b42c212…` · `python:3.12-slim@sha256:5e2bdb1b…` (3.12.16, Debian 13) · `node:22-slim@sha256:e9f565d3…` (22.23.5) | Runtime and build | docs/05 §1, §7 |
| uv | 0.11.32 | Image build only (removed from the image) | docs/05 §2 |
| Fonts | Noto Sans 2.015, Noto Sans Devanagari 2.007, Inter 4.001, Source Serif 4 4.005 (all OFL 1.1) | PDF and UI fonts | docs/05 §1 |

## Verification items (V-xx)

All results below were obtained in the cloud development container (Linux) unless stated otherwise. Native Windows evidence is listed under "Verification evidence by environment".

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
| Clean image build and Compose verification (M0 exit criteria 1 and 8) | **BLOCKED / UNVERIFIED** in both environments | **Windows laptop:** Docker Desktop cannot run (hardware virtualization disabled; BIOS access blocked by an unknown administrator password; no further BIOS attempt), so the build was not attempted there. **Cloud container:** `docker build -t hive-docs:local .` on the unmodified, committed Dockerfile (unchanged since `5402bf9`, also at `0ea973c`) failed in 9 s with exit code 1: in the build's `RUN` containers `apt-get update` reports `Could not resolve 'deb.debian.org'` (no DNS or direct egress for containers in the cloud container's sandbox; `npm ci` was cancelled with it). Diagnostic with CLI flags only (`--network host` plus proxy build arguments, separate tag; no Dockerfile change, no TLS bypass): apt's plain-HTTP Debian sources get `405 Method Not Allowed` from the sandbox proxy, which tunnels HTTPS only, and HTTPS downloads would require trusting the proxy's interception CA inside the build. Both causes are environmental. `hive-docs:local` was not changed (still image `7d9bafcb…`, built earlier through the sandbox-derived Dockerfile from commit `5402bf9` code). **Not run, because the clean image does not exist:** Compose with that image, `/healthz`, `/readyz`, SPA load, storage |

## Known issues

| Severity (S1–S4) | Description | Status |
| --- | --- | --- |
| S3 | SeaweedFS's internal ports (master 9333, volume 8080, filer 8888/18888, including an unauthenticated filer IAM gRPC service) are reachable inside the compose network. They are not published to the host; only the app and database containers share the network. Local development only (the cloud uses Spaces). Possible mitigation: JWT keys in a SeaweedFS `security.toml` | Open (accepted for local) |
| S3 | **The clean build of the committed Dockerfile and the Compose verification are BLOCKED / UNVERIFIED in both available environments:** the cloud container (no DNS or egress for build containers; HTTPS-only intercepting proxy) and the developer's Windows laptop (Docker Desktop unavailable: hardware virtualization disabled, BIOS access blocked, no further BIOS attempt). They need a Docker-capable machine with virtualization enabled and normal network access: `docker build -t hive-docs:local .`, `docker compose up -d`, then checks of `/healthz`, `/readyz`, the SPA and storage | Open (needs another machine) |
| S2 | **Demonstration runtime risk:** the documented demonstration runtime is the local Docker stack on the presenter laptop (D-1, MUST COMPLETE; 10 §7, §8; DC-01, DC-17). If the developer's Windows laptop is the intended presenter laptop, it cannot run that stack. A Docker-capable presenter or backup machine is needed by M8, or a decision through 14 §6 | Open (risk; developer decision before M8) |
| S3 | Native Windows has no PostgreSQL 16 or SeaweedFS yet: the documented setup starts both with Docker Compose (05 §6.2, §10), so the backend integration suite cannot run natively until the developer records how they are provided (see the native-Windows arrangement) | Open (M1 prerequisite) |
| S4 | The `hive-docs:local` image in the cloud container (and its running `app` container) is the earlier build from the sandbox-derived Dockerfile at commit `5402bf9`; it contains **neither** the 405 nor the HEAD correction. The corrected code was verified with the test suite and with a host uvicorn over real HTTP (raw sockets: 0 body bytes for HEAD), not in a container | Open (resolved by the clean build) |
| — | ~~`HEAD` on GET routes returned 405~~: resolved at 19:30, every GET resource answers HEAD (07 §1.14) | Closed |
| — | ~~`docs/14` §6 had no decision entry for the HEAD rule~~: resolved in the final documentation cleanup, decision #10 | Closed |
| S4 | M4 and M5 (E-20 preview, E-22 download): HEAD must run the same checks as GET without recording `document.pdf_downloaded`; header fields known only after generating the content may be omitted (07 §1.14) | Open (M4/M5 note) |
| S4 | From M1, the Origin/CSRF middleware runs before routing (07 §1.13), so an unsafe request without a valid session token gets 403 before any 405. M1 must update the 405 tests that use POST, PATCH or DELETE to send a valid session, CSRF token and Origin | Open (M1 note) |
| S4 | Pre-existing in the 1.1 documents, not changed by this revision: README, 00, 01 and PROJECT_SUMMARY still say no source code exists; 08 §15.3 paraphrases the SPECIMEN label in dialog copy (recorded in CONSISTENCY_AUDIT §2.1) | Open (documentation; not in scope) |
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

- Developer: review and approve this PROGRESS.md reconciliation. It is an uncommitted change; committing it is the developer's decision.
- Developer: decide on M0 acceptance with the outstanding Docker verification (exit criterion 8 open, criterion 1 only partly verified; see "M0 acceptance status").
- Developer: CP1 response (10 §6.1). CP1 (Mon 22:30 IST) was missed. The documented response is to stop for the night, finish M1 first thing Tuesday and apply R5. Whether to apply R5 is the developer's decision (10 §9); if it is applied, record it under "Reduction rules applied" with the time.
- Docker verification (outstanding): on a Docker-capable machine with hardware virtualization enabled and normal network access, run `docker build -t hive-docs:local .` and `docker compose up -d`, then check `/healthz`, `/readyz`, the SPA and storage. This cannot be done on the current Windows laptop, and no further BIOS attempt will be made. It is needed for D-1 by M8 at the latest (10 §8; DC-01, DC-17).
- **Next milestone: M1, Database, authentication, app shell** (10 §3; estimate 2.5–3 h). Tasks M1.1 to M1.5: Alembic with `MIGRATION_DATABASE_URL` and migration `0001_identity` (including `trg_audit_events_append_only` and grants); Argon2id; sessions (`token_hash`, idle and absolute expiry) and cookie attributes; E-03, E-04, E-05; the CSRF HMAC and Origin middleware; login throttling from `audit_events`; CLI `create-demo-account`; frontend login page, route guard, app shell, sign-out and 404 page. Tests: UT-SEC-01, UT-SEC-02, IT-AUTH-01 to IT-AUTH-06, DB-01, DB-07. Exit: sign in and out in the browser; tests green.
- **M1 prerequisites:**
  1. The developer's explicit go-ahead naming M1 (15 §4), after the M0 acceptance decision.
  2. A PostgreSQL 16 server providing `ps5` and `ps5_test`, the owner role `ps5_migrator` and the restricted role `ps5_app` (06 §11): the cloud container's Compose stack, or a native Windows setup recorded by the developer under the native-Windows arrangement.
  3. A SeaweedFS S3 endpoint (ADR-13) for the existing integration suite (readiness, conventions, SPA, HEAD, storage gate), because every milestone runs the whole backend suite (15 §2, rule 7): the cloud container's Compose service, or a native setup recorded by the developer.
  4. `.env` and `.env.test` for that environment, including `MIGRATION_DATABASE_URL` (05 §9), which Alembic needs from M1.
  5. M1 verification items: V-12 (the demonstration browser keeps `Secure` cookies on `http://localhost`) and V-13 (argon2-cffi defaults meet the OWASP minimum for Argon2id).
  6. Carry-over: once the CSRF middleware exists, the 405 tests that use POST, PATCH or DELETE must send a valid session, CSRF token and Origin (see "Known issues").
