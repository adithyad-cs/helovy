# PROGRESS — HIVE DOCS P0-Lite

## Current status

- Active milestone: **M5 complete; M6 next** (autonomous run M1–M8 authorised by the developer's master directive of 24 Nov; see "Autonomous run checkpoint").
- Last updated: 2026-11-24 02:57 IST
- M0: acceptance still **conditional** on the outstanding Docker verification (unchanged; see "M0 acceptance status"). It is not marked accepted.
- Checkpoints: CP1 (Mon 22:30 IST) was missed; M1 finished at 01:52 IST Tuesday, M2 at 02:07 IST M3 at 02:25 IST (CP2 target met ahead of Tue 13:00) M4 at 02:40 IST (CP3 target met ahead of Tue 17:30) and M5 at 02:57 IST (CP4 target, finalise → stored PDF → download with IT-FIN and IT-PDF green, met ahead of Tue 21:00). No reduction rule has been applied (applying one is the developer's decision, 10 §9).
- Environment for this run: the **cloud development container** (Linux) with the Compose `db` (PostgreSQL 16.16) and `storage` (SeaweedFS 4.54) services. The developer's Windows laptop is not attached to this session (no shared folder), so the native Windows PostgreSQL and SeaweedFS were **not** reached or tested; every result below is cloud-container evidence unless marked otherwise.

## Autonomous run checkpoint (for restart recovery)

| Item | State |
| --- | --- |
| Branch / last commit | `claude/busy-bell-14l7rh`; M1 = `0d934ae`, M2 = `b6a97bf`, M3 = `552412a`, M4 = `68e5728`; M5 commit follows it |
| Databases (cloud container) | `ps5_test`: recreated and migrated to head by every test run. `ps5` (development): not migrated yet (migrated in M8 for the demonstration data) |
| Services | `docker compose` services `db` and `storage` healthy. The old `app` container still runs the `5402bf9` sandbox image on port 8000; browser checks use a host uvicorn on port 8001 against `ps5_test` |
| Browser test account | Created in `ps5_test` only (wiped by the next test run); its random password lives in the session scratchpad, never in the repository |
| Next concrete action | M6: E-16 history list (status filter, prefix search on number and customer, cursor pagination), history page, dashboard recent invoices |

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
| M1 | **Done** (cloud container) | 24 Nov 01:30 | 24 Nov 01:52 | Backend 266/266 (UT-SEC-01/02, DB-01, DB-07, DB-08 part, IT-AUTH-01..06 all automated) · FE-01..FE-03 3/3 · browser sign-in/out flow in headless Chromium | Migration `0001_identity`; Argon2id; hashed session tokens with 24 h idle / 7 day absolute expiry; CSRF HMAC + Origin middleware before routing; DB-backed throttling; E-03..E-05; `create-demo-account`; login page, guard, shell, drawer, user menu, 404 |
| M2 | **Done** (cloud container) | 24 Nov 01:53 | 24 Nov 02:07 | Backend 322/322 (IT-BIZ-01..03, IT-CUS-01..02, IT-TEN-01..03 for business and customer endpoints, DB-01/DB-08 extended) · FE-01..FE-03 · browser flow | Migration `0002_parties`; E-06..E-12 with 09 §4 validation, ETags, If-Match, signed cursors, prefix search; profile and customer screens with error summary, 412 dialog and leave guard |
| M3 | **Done** (cloud container) | 24 Nov 02:08 | 24 Nov 02:25 | Backend 420/420 (UT-CALC-01..09 incl. 300-example property test, IT-DOC-01..03, DB-02, DB-03, DB-04, E-13, IT-TEN-01 incl. E-14, E-15, E-17..E-19) · FE-01..FE-03 · browser DC-07..DC-10 | `calc-1.0.0`; migration `0003_documents` with both guard triggers; E-13..E-15, E-17..E-19; in-memory limiter (E-14 60/min); editor with live server totals, validation, save, delete, leave guard, quick-create customer |
| M4 | **Done** (cloud container) | 24 Nov 02:26 | 24 Nov 02:40 | Backend 472/472 (UT-FMT-01, UT-SEC-03, IT-DOC-04, IT-PDF-05, registry, readiness template check) · FE-01..FE-03 · browser: preview in the in-app iframe (full Chromium 153), Templates page | `classic@1` registered (hash `3dba1d0e1295…`); Jinja2 autoescape + StrictUndefined; restricted fetcher; 2 spawn workers with 20 s kill; E-20; `template-hash` CLI; `/readyz` templates |
| M5 | **Done** (cloud container) | 24 Nov 02:41 | 24 Nov 02:57 | Backend 524/524 (UT-NUM-01/02, UT-SNAP-01..03, IT-FIN-01..07 incl. 10-thread concurrency, IT-PDF-01..04, DB-04..06, DB-08 complete, DB-09, V-14) · FE-01..FE-03 · browser DC-12, DC-13, DC-14, DC-16 (API), DC-18 with SeaweedFS really stopped and restarted | Migration `0004_issuance`; finalisation exactly per 09 §8; post-commit render → private S3 → `stored_files` + `ready`; E-21..E-23; finalise dialog with idempotency key and automatic same-key retries; details view with polling, verified download, retry, integrity |
| M6 | Not started | | | | |
| M7 | Not started | | | | |
| M8 | Not started | | | | |

## Features

| ID | Status (Not started / In progress / Done / Deferred) | Evidence (tests, DC) | Notes |
| --- | --- | --- | --- |
| L-01 | Not started | — | M0 has an honest placeholder page at `/` (replaced in M7) |
| L-02 | **Done** | IT-AUTH-01..06, UT-SEC-01/02, CLI tests; browser: guard redirect, wrong-password message, sign-in, cookie flags, sign-out, Back → /login | No sign-up, no default credentials, no auto-login |
| L-03 | **Done** | Browser: nav with `aria-current`, focus to `h1` on navigation, 360 px drawer, unknown `/app/...` → 404 page, `next` return after sign-in | Business, Customers, Invoices and Templates show an honest "not available in this build yet" page until M2–M6 replace them |
| L-04 | **Done** | IT-BIZ-01..03; browser: create with invalid PIN → field error and focus, create, edit phone with toast, leave guard | DC-15 (issued invoices unchanged) is checked once finalisation exists (M5) |
| L-05 | **Done** | IT-CUS-01..02, IT-TEN-01/02; browser: create 3, prefix search `Harb` (URL `?q=`), edit city, empty search state, 404 state, 360 px cards | |
| L-06 | **Done** | IT-DOC-01/02; browser: create for a customer, add/remove lines, save, reload (DC-10), delete with confirmation, leave guard, 412 dialog wired | Quick-create customer dialog and the in-app route blocker are both implemented (R5 not needed) |
| L-07 | **Done** | UT-CALC-01..09, IT-DOC-03; browser DC-07 (₹1,800.00 / ₹900.00 / ₹2,700.00 from E-14), DC-08 (₹1.01), DC-09 messages | Strings-only money end to end; the SPA formats server strings without `Number` |
| L-08 | **Done** | UT-FMT-01, template-level tests (title "Invoice", exact SPECIMEN, no forbidden words, GSTIN only as a label), 45-line render: header repeats, rows unsplit, "Page X of Y"; registry hash checked by `/readyz` | Rendered on the cloud container host (WeasyPrint 70.0); the image path was proven by Spike A in M0 |
| L-09 | **Done** | IT-DOC-04, rate limit, HEAD, 503 on timeout; browser: Preview saves first, then shows the watermarked PDF in the dialog (full Chromium), "Open preview" below 768 px | Nothing stored; no audit event |
| L-10 | **Done** | IT-FIN-01..07; DB-03..DB-05; browser DC-12 (INV/26-27/00001, India date), DC-13 (double-click → one number) | Lock order idempotency → document → number series; `lock_timeout` 5 s |
| L-11 | **Done** | IT-PDF-01..04, DB-06; browser DC-14 (downloaded file's SHA-256 equals the details page), DC-18 (storage stopped → Failed → started → Retry → Ready, number kept) | Object key `orgs/{org}/documents/{doc}/final-{artifact}.pdf`; anonymous GET refused (403) |
| L-12 | Not started | — | M6 |
| L-13 | Not started | — | M6 |
| L-14 | In progress | IT-TEN-01..03 for E-07..E-15, E-17..E-23 (`tests/integration/test_tenancy.py`) | E-16 joins the suite in M6 |
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
| 24 Nov 01:35 | **Autonomous M1–M8 run** under the developer's master directive (24 Nov), which is the go-ahead naming the milestones (15 §4). Milestones are committed and pushed one at a time; M0 stays conditionally accepted | 15 §3, §4 | Developer (directive) |
| 24 Nov 01:40 | Constraints that 06 describes without a name are named `<table>_<column>_ck` / `_fk` (for example `users_email_ck`, `memberships_org_fk`, `audit_events_event_type_ck`); every name 06 gives is exact (DB-01 checks them through `pg_catalog`). Trigger function `audit_events_append_only()` | 06 §14 rule 2 | Claude Code (naming detail) |
| 24 Nov 01:45 | The app role needs **no** sequence grant for the `audit_events` identity column (verified by a test inserting as `ps5_app`) | 06 §11 "verify whether it is needed" | — (verified) |
| 24 Nov 01:50 | Module boundaries (04 §3): auth resolves the session and stores a `Tenant` on `request.state`; tenant modules read it through `tenancy.current_tenant` and never import auth. E-05's `business` summary is provided by the businesses module through an application-factory hook | 04 §3 | Claude Code |
| 24 Nov 01:50 | CSRF check (owned by auth, placed after the body limit and before routing): finds the session row by token hash **whatever its state**, so a revoked cookie with its own token reaches the session dependency and gets 401 (IT-AUTH-04); a missing cookie or wrong token → 403. Unsafe = every method except GET, HEAD, OPTIONS, TRACE | 07 §1.3, §1.13; 12 §4.2 | Claude Code |
| 24 Nov 01:55 | Throttling counts `auth.login_failed` events with reason `invalid_credentials` or `inactive`; refused (`throttled`) attempts are recorded but **not counted**, so a lock-out ends 15 minutes after the fifth real failure. `Retry-After` = seconds until fewer than 5 counted failures remain in the window | 12 §2.2; 07 §1.9 | Claude Code (detail not specified) |
| 24 Nov 01:55 | Sign-in failures are audited with `org_id` and `actor_user_id` NULL and the `subject_hash`; the email itself is never stored. An inactive user is verified first (same timing), then refused with reason `inactive` | 06 §3.15, §9; 12 §2.2 | Claude Code |
| 24 Nov 01:55 | CSRF token = base64url without padding of HMAC-SHA256(CSRF_SECRET key bytes, the session UUID's canonical text) | 12 §4.2 | Claude Code (encoding detail) |
| 24 Nov 02:00 | One injectable clock (`app.state.clock`): session times, audit times and throttling windows use it, so tests freeze time (IT-AUTH-03, IT-AUTH-05) | 04 §5; 11 §1 | Claude Code |
| 24 Nov 02:00 | `create-demo-account` connects as the app role (`DATABASE_URL`), the least privilege that can insert the account rows; it validates email, name (1–120), organization (1–200) and password (12–1024) before connecting | 05 §8; 06 §11 | Claude Code |
| 24 Nov 02:00 | Request bodies must be `application/json` (router dependency `require_json_body`, 400 otherwise); custom validators raise Pydantic errors whose type is the documented field code; `string_type` maps to `must_be_string` | 07 §1.1, §1.5 | Claude Code |
| 24 Nov 02:05 | **Tests updated, none weakened:** 41 earlier routing cases (405 and 404 with POST, PUT, PATCH or DELETE in test_conventions, test_spa, test_head) now send a valid session, CSRF token and Origin, as recorded in M0's known issues; 8 new cases assert that the CSRF check returns 403 before routing would give 405 or 404. Test fixtures moved to `tests/services.py` (shared by `tests/db` and `tests/integration`); the suite now resets `ps5_test` and migrates it to head once per run and truncates tables before each test | 07 §1.13; 11 §1 | Claude Code |
| 24 Nov 02:05 | E-09 cursors are opaque base64url JSON `{t, id, sig}` where `sig` is a truncated HMAC (key: CSRF_SECRET key bytes) over the list scope (`customers:{business_id}`) and position, so a tampered or another list's cursor gives 422 at `/cursor` | 07 §1.8 | Claude Code |
| 24 Nov 02:05 | GSTIN input is upper-cased before validation (users often type lower case); the stored value always matches the 06 pattern. `state_mismatch` is reported at `/gstin`, checked against the stored state when a PATCH changes only one of them | 09 §4.2; 07 E-06, E-10 | Claude Code |
| 24 Nov 02:05 | A PATCH whose values equal the stored ones changes nothing: 200, same ETag, no audit event. Audit `details.fields` lists the changed (or, on create, the provided) field names only | 06 §9; 07 §1.6 | Claude Code |
| 24 Nov 02:05 | Customer search `q`: trimmed; empty means no search; LIKE wildcards in `q` are escaped (prefix match only); case folding with Python `lower()` | 07 E-09; 09 §4.3 | Claude Code |
| 24 Nov 02:05 | If-Match must be a strong version ETag (`"4"`); anything else is 400 `malformed_request` ("bad header format", 07 §1.12); missing → 428 | 07 §1.6 | Claude Code |
| 24 Nov 02:05 | **Defect found and fixed:** `HeadAwareRoute` answered HEAD through the route's own app, which in FastAPI 0.165 skips the include-level dependencies of included routers (the session dependency added in `main.py`). HEAD on tenant endpoints failed closed with 401 (no data exposed). HEAD now runs through FastAPI's effective route context (the same app GET uses); regression test `test_head_runs_include_level_dependencies` | 07 §1.14 | Claude Code (fix within the approved HEAD contract) |
| 24 Nov 02:05 | Ruff: `E501` (line length) is not enforced in `tests/**`, so case tables and URLs stay readable; the formatter still runs | 11 §6 (ruff clean) | Claude Code |
| 24 Nov 02:15 | `calc` input codes: a plain decimal with too many decimals → `too_many_decimals`; a plain decimal outside the range (including too many integer digits, for example quantity `12345678`) → `out_of_range`; anything else (sign, exponent, spaces, grouping, leading zeros, `1.`, `.5`) → `invalid_decimal`; a non-string → `must_be_string`. `exceeds_gross` is reported at `/lines/{i}/discount_value` with the gross in the message; `total_too_large` and `too_many_lines` at `/lines` | 09 §4.1, §4.3; 07 §1.5 | Claude Code (precedence detail) |
| 24 Nov 02:15 | Line `discount_type` defaults to `none` when absent; `discount_value` must be absent or null for `none` (`invalid_choice`) and is `required` for percent and amount | 09 §4.1; 06 §3.10 | Claude Code |
| 24 Nov 02:15 | Saving a draft (E-15, E-18) also refuses `total_too_large`, so a stored draft can always be displayed and finalised within the limit. Every successful PATCH increments `version` (09 §12) | 09 §3 step 7, §12 | Claude Code |
| 24 Nov 02:15 | E-14 counts a request toward the 60/min limit after body validation and the business lookup (a 422 or 404 is not counted) | 07 §1.9 | Claude Code |
| 24 Nov 02:20 | Editor live totals: blank new rows (no description and no price) are not sent to E-14 and show "—"; server field messages from E-14 are shown under the matching inputs; amounts are dimmed while a newer calculation is pending. Line grid: one DOM structure, a table-like grid with column headers from 768 px (horizontal scroll inside its frame if needed, as FE-05 allows) and labelled stacked cards below | 08 §15.3, §6; 11 FE-05 | Claude Code |
| 24 Nov 02:20 | `/app/invoices` shows only a "New invoice" action and an honest "not available yet" line until the history list (M6) | 08 §18 | Claude Code |
| 24 Nov 02:35 | Render pool: persistent `spawn` worker processes (at most `RENDER_WORKERS`), started lazily; each job waits up to `RENDER_TIMEOUT_S` for its result, after which the worker is killed and replaced (`render_timeout`). Workers receive plain payloads and return bytes; a final render re-checks the snapshot hash in the worker (`snapshot_integrity`) | 04 §11; 12 §9; ADR-09 | Claude Code |
| 24 Nov 02:35 | The template CSS is inlined into the HTML by Jinja (`{% include %}`), so the restricted fetcher only ever serves the bundled font files; the SPECIMEN constant is injected into the `@page` footer from `rendering/constants.py`, the single source also copied into `labels.specimen_text` | 09 §13; 12 §9 | Claude Code |
| 24 Nov 02:35 | E-20 renders for HEAD as well (status parity, 07 §1.14) and counts toward the same 20/min limit; the limit is counted after the draft checks (404, 409, 422). A render timeout or no free worker → 503 `dependency_unavailable`; another render failure → 500 `internal_error` (logged) | 07 E-20, §1.9, §1.14 | Claude Code |
| 24 Nov 02:35 | Every render verifies the template files against the registry hash (also in development); `/readyz` reports `warn` in development and `error` in demo/production on a mismatch. `classic@1` is now registered and frozen (any change becomes `classic@2`) | 09 §11; 07 E-02 | Claude Code |
| 24 Nov 02:38 | **Defect found and fixed:** centred dialogs combined Tailwind 4's `translate` utilities with a `transform` keyframe, doubling the offset; the large preview dialog's close button was off-screen. Keyframes now animate opacity and `scale` only | 08 §7 | Claude Code |
| 24 Nov 02:50 | **API addition (needs the developer's confirmation):** the finalised representation of E-17/E-21 also carries the snapshot's `seller` and `buyer` objects (drafts carry `null`). 08 §19 requires "read-only seller and buyer blocks … all from the snapshot", and 07 §3.3 says a finalised document comes from the snapshot, but its example lists only `customer.display_name`. Additive; no existing field changed | 08 §19 vs 07 §3.3; 15 §7.4 | Claude Code (open question for the developer) |
| 24 Nov 02:50 | Finalisation takes `finalized_at` from the database `now()` inside the transaction (step 4) through the clock abstraction (`transaction_now`), so the frozen test clock can stand in for it; issue date = its Asia/Kolkata date | 09 §7, §8 step 4; 11 IT-FIN-01 | Claude Code |
| 24 Nov 02:50 | Lock-timeout mapping: waiting on another request's idempotency record → 409 `idempotency_in_progress`; on the document or number series → 503 `dependency_unavailable`. A replay returns the stored status and body with `Idempotent-Replayed: true` and the stored version's ETag | 09 §8; 04 §10 | — (as documented) |
| 24 Nov 02:50 | Render attempts: the post-commit task claims attempt 1 (`attempts` 0 → 1) before rendering; E-23's claim increments `attempts` and the render reuses that number. Artifact and stored-file timestamps come from the application clock, so the 120 s retry rule can be tested with the frozen clock | 06 §3.12; 07 E-23; 11 IT-PDF-04 | Claude Code |
| 24 Nov 02:50 | E-22 reads the current object (not the recorded version ID), so an overwritten object is detected (IT-PDF-02); a missing object is also `integrity_check_failed`; unreachable storage is 503. E-23's 1-per-10-s limit is checked after the 404 and 409 checks | 09 §11; 07 E-22, E-23 | Claude Code |
| 24 Nov 02:55 | **Defect found and fixed:** the S3 client from M0 allowed a single attempt, so a pooled keep-alive connection that SeaweedFS had closed made a PDF upload fail (`ConnectionClosedError`). The client now uses botocore's standard retry mode with 3 attempts; every call is idempotent | 04 §12 | Claude Code |
| 24 Nov 02:55 | **Defect found and fixed:** after "Reload" in the 412 dialog the editor kept the stale values; it now resets to the refetched version whenever a newer ETag arrives and the form is not being edited | 08 §9 | Claude Code |

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
| V-12 | Pass (Chromium, cloud container) | Headless Chromium kept the `Secure` `ps5_session` cookie on `http://localhost:8001` (HttpOnly, Secure, SameSite=Lax, Path=/, host-only). To re-check in the presenter's Chrome in M8 (DC-04) |
| V-13 | Pass | argon2-cffi 25.1.0 defaults: Argon2id, m = 65,536 KiB (64 MiB), t = 3, p = 4, above the OWASP minimum (19 MiB, t = 2, p = 1); asserted by UT-SEC-01 |
| V-15 | Partial pass (preview) | Full Chromium 153 (new headless) shows the preview PDF in the in-app `blob:` iframe with no CSP console messages. The rest of V-15 (Radix dialogs, whole built SPA) is checked in M7 |
| V-14 | Pass | PostgreSQL 16.16 accepts the generated columns `buyer_name` (`payload #>> '{buyer,display_name}'`) and `grand_total` (`::numeric(16,2)`); verified by migration and `test_v14_generated_columns_and_ut_snap_02_round_trip` |
| V-10, V-11, V-17 | Not run | Not in scope (S-02, before P1) |
| Clean image build and Compose verification (M0 exit criteria 1 and 8) | **BLOCKED / UNVERIFIED** in both environments | **Windows laptop:** Docker Desktop cannot run (hardware virtualization disabled; BIOS access blocked by an unknown administrator password; no further BIOS attempt), so the build was not attempted there. **Cloud container:** `docker build -t hive-docs:local .` on the unmodified, committed Dockerfile (unchanged since `5402bf9`, also at `0ea973c`) failed in 9 s with exit code 1: in the build's `RUN` containers `apt-get update` reports `Could not resolve 'deb.debian.org'` (no DNS or direct egress for containers in the cloud container's sandbox; `npm ci` was cancelled with it). Diagnostic with CLI flags only (`--network host` plus proxy build arguments, separate tag; no Dockerfile change, no TLS bypass): apt's plain-HTTP Debian sources get `405 Method Not Allowed` from the sandbox proxy, which tunnels HTTPS only, and HTTPS downloads would require trusting the proxy's interception CA inside the build. Both causes are environmental. `hive-docs:local` was not changed (still image `7d9bafcb…`, built earlier through the sandbox-derived Dockerfile from commit `5402bf9` code). **Not run, because the clean image does not exist:** Compose with that image, `/healthz`, `/readyz`, SPA load, storage |

## Known issues

| Severity (S1–S4) | Description | Status |
| --- | --- | --- |
| S3 | SeaweedFS's internal ports (master 9333, volume 8080, filer 8888/18888, including an unauthenticated filer IAM gRPC service) are reachable inside the compose network. They are not published to the host; only the app and database containers share the network. Local development only (the cloud uses Spaces). Possible mitigation: JWT keys in a SeaweedFS `security.toml` | Open (accepted for local) |
| S3 | **The clean build of the committed Dockerfile and the Compose verification are BLOCKED / UNVERIFIED in both available environments:** the cloud container (no DNS or egress for build containers; HTTPS-only intercepting proxy) and the developer's Windows laptop (Docker Desktop unavailable: hardware virtualization disabled, BIOS access blocked, no further BIOS attempt). They need a Docker-capable machine with virtualization enabled and normal network access: `docker build -t hive-docs:local .`, `docker compose up -d`, then checks of `/healthz`, `/readyz`, the SPA and storage | Open (needs another machine) |
| S2 | **Demonstration runtime risk:** the documented demonstration runtime is the local Docker stack on the presenter laptop (D-1, MUST COMPLETE; 10 §7, §8; DC-01, DC-17). If the developer's Windows laptop is the intended presenter laptop, it cannot run that stack. A Docker-capable presenter or backup machine is needed by M8, or a decision through 14 §6 | Open (risk; developer decision before M8) |
| S3 | Native Windows: the developer reports PostgreSQL 16.16 installed natively with `ps5`, `ps5_test` and both roles (init script run; role logins verified by the developer) and a native SeaweedFS `weed.exe` on 127.0.0.1:8333 refusing anonymous requests. Not verified from this session (the laptop is not attached). Still to verify natively: an authenticated PUT/GET round trip with the new `.env.test` keys, bucket scoping and `init-dev-storage` (the gate checks V-07, V-08, V-18, V-19), then `uv run pytest` | Open (developer to run natively) |
| S4 | The `hive-docs:local` image in the cloud container (and its running `app` container) is the earlier build from the sandbox-derived Dockerfile at commit `5402bf9`; it contains **neither** the 405 nor the HEAD correction. The corrected code was verified with the test suite and with a host uvicorn over real HTTP (raw sockets: 0 body bytes for HEAD), not in a container | Open (resolved by the clean build) |
| — | ~~`HEAD` on GET routes returned 405~~: resolved at 19:30, every GET resource answers HEAD (07 §1.14) | Closed |
| — | ~~`docs/14` §6 had no decision entry for the HEAD rule~~: resolved in the final documentation cleanup, decision #10 | Closed |
| — | ~~HEAD on E-20/E-22~~: done; E-20 renders for HEAD (status parity), E-22 verifies but records no download event (`test_head_download_records_nothing`) | Closed |
| — | ~~405 tests with unsafe methods needed a session once the CSRF middleware existed~~: done in M1 (see decisions, 24 Nov 02:05) | Closed |
| S4 | Pre-existing in the 1.1 documents, not changed by this revision: README, 00, 01 and PROJECT_SUMMARY still say no source code exists; 08 §15.3 paraphrases the SPECIMEN label in dialog copy (recorded in CONSISTENCY_AUDIT §2.1) | Open (documentation; not in scope) |
| S4 | `document_lines_discount_ck` exactly as documented (06 §3.10) lets a NULL `discount_value` through for `percent` and `amount` (CHECK treats `NULL > 0` as unknown, which passes). The API always rejects it (`required`), so only direct SQL could store such a row. A stricter check (`discount_value IS NOT NULL`) would be a schema change needing approval (15 §7) | Open (developer decision) |
| S4 | On the cloud container host (not the image), WeasyPrint warns that HarfBuzz-Subset will be required by future versions; the Docker image installs `libharfbuzz-subset0` (M0). No effect on WeasyPrint 70.0 | Open (host only) |
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

- **M6 (next):** E-16 history list, history page, dashboard recent invoices (tests IT-DOC-05, IT-TEN-02).
- Then M7 and M8 in order (10 §3), each committed and pushed when its tests pass.
- Developer (open question): confirm the additive `seller`/`buyer` fields on finalised documents (see decisions, 24 Nov 02:50).
- Developer (outstanding from M0): the Docker verification on a Docker-capable machine (`docker build -t hive-docs:local .`, `docker compose up -d`, `/healthz`, `/readyz`, SPA, storage). Not possible on the current Windows laptop; no further BIOS attempt.
- Developer (native Windows): run the storage gate and the backend suite natively once the native SeaweedFS identity matches `.env.test` (see Known issues).
