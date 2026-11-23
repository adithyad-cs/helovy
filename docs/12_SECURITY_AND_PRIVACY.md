# 12 — Security and Privacy

| | |
| --- | --- |
| Document | Security and privacy baseline · version 1.1 · 23 November 2026 |
| Principle | Demonstration convenience must never become an insecure production shortcut. P0-Lite uses the **same** authentication, authorization and integrity code paths that production will use; production adds hardening on top |
| Status | An OWASP ASVS-inspired baseline, not certified. Synthetic data only until §14 is complete |

## 1. Summary: demonstration safeguards versus production hardening

| Area | Demonstration safeguard (P0-Lite, MUST) | Production hardening (P1-14 and later, DEFERRED) |
| --- | --- | --- |
| Accounts | One owner account created by CLI with a strong run-time password; real sign-in | Sign-up with email verification, password reset, MFA for owners (P1-01, P1-14) |
| Passwords | Argon2id (§3) | The same, plus a breached-password check if approved |
| Sessions | Server sessions with a hashed token, HttpOnly, Secure, SameSite=Lax, idle and absolute expiry | Session management UI; notifications of new sign-ins |
| CSRF | HMAC token + Origin check | The same |
| Authorization | Organization from the session; 404 across tenants; composite FKs; IT-TEN | PostgreSQL row-level security (defence in depth) |
| Input | Strict schemas; limits; text normalisation | The same, plus edge rate limiting or a web application firewall |
| Files | No uploads at all | PNG-only logo upload with server re-encoding (P1-03) |
| PDFs | Private bucket; proxied, hash-verified downloads | Document encryption (§8); access logging |
| Rendering | Restricted fetcher, isolated workers, bundled assets, no network | The same; prompt patching of WeasyPrint |
| Secrets | Environment variables; nothing committed | A managed secret store; a rotation schedule |
| Logging | JSON logs without secrets or personal data | Central logging, alerting, retention policy |
| Audit | 12 append-only event types | Retention, export, optional tamper-evidence (hash chain) |
| Backups | Database dump plus storage copy before the freeze, tested on the backup machine | Managed backups with point-in-time recovery, restore drills |
| Privacy | Synthetic data only | DPDP compliance programme (§13, §14) |

## 2. Authentication security

### 2.1 Demonstration authentication path (P0-Lite)

1. **Account creation:** `python -m app.cli create-demo-account` (05 §8). The password comes from `DEMO_ACCOUNT_PASSWORD`, set only for that one command, or from a hidden prompt. It must be at least 12 characters and is never printed or logged.
2. **Sign-in:** through the real E-03 endpoint, with Argon2id verification, a new server session and an audit event.
3. **Sharing the password:** only with the presenter, through a private channel. It never appears in documents, slides, the repository, screenshots or chat logs.
4. **After the evaluation:** deactivate the account (`users.is_active = false`) or delete the demonstration data (§16).

**Forbidden shortcuts:**

- hard-coded or seeded credentials in code or migrations;
- a sign-up page in P0-Lite;
- auto-login;
- `?demo=true` or similar bypass flags;
- disabling CSRF or cookie flags "for the demo";
- tokens in `localStorage`;
- running the demonstration with `APP_ENV=development` (which exposes the API docs UI);
- a shared password written on a slide.

### 2.2 Sign-in protections

- **One generic failure message:** 401 `invalid_credentials` for an unknown email, a wrong password or an inactive user.
- **Timing:** for unknown emails, a dummy Argon2 verification against a fixed hash keeps response times similar.
- **Throttling:** after 5 failures in 15 minutes, further attempts get 429 with `Retry-After`. Failures are counted per email and per client IP, from `audit_events`.
  - The email is stored only as `subject_hash` = HMAC-SHA256(`CSRF_SECRET`, `"login:" + normalised email`).
  - Throttled attempts are recorded too (`reason: "throttled"`).
  - Client IP is the socket address, or the header named in `CLIENT_IP_HEADER` behind the cloud proxy (V-11). `X-Forwarded-For` is never trusted otherwise.
- **Session fixation:** every successful sign-in creates a new session and revokes any session presented with the request.

## 3. Password hashing

- argon2-cffi `PasswordHasher` with its default parameters (the RFC 9106 low-memory profile). These must be verified to meet or exceed the OWASP minimum for Argon2id: memory 19 MiB or more, 2 or more iterations, parallelism 1 (V-13).
- `check_needs_rehash` runs on successful sign-in, and the stored hash is upgraded if the parameters change.
- Length is 12–1024 characters for accounts created by the CLI; the upper bound limits denial-of-service. There are no composition rules.
- Passwords are never logged, returned or stored in plain text anywhere, including test fixtures (tests generate random passwords).

## 4. Session security, CSRF and browser protections

### 4.1 Sessions

| Property | Value |
| --- | --- |
| Token | 256-bit random (`secrets.token_urlsafe(32)`) in cookie `ps5_session` |
| Storage | Only the SHA-256 of the token (`sessions.token_hash`). A database leak does not reveal usable tokens |
| Cookie attributes | HttpOnly; Secure; SameSite=Lax; Path=/; host-only (no Domain); Max-Age 7 days |
| Expiry | 24 h idle (`last_seen_at`, refreshed at most once a minute); 7 days absolute (`expires_at`) |
| Revocation | Sign-out sets `revoked_at`; revoked or expired sessions are rejected |
| Local HTTP | Browsers treat `http://localhost` as a secure context, so Secure cookies work for the local demonstration (verify in the demonstration browser, V-12) |

### 4.2 CSRF

- **Token:** base64url(HMAC-SHA256(`CSRF_SECRET`, `sessions.id`)), returned in the JSON of E-03 and E-05. The SPA keeps it in memory and sends it as `X-CSRF-Token`. It is checked with `hmac.compare_digest`.
- **Origin:** every POST, PATCH and DELETE must also carry `Origin` equal to `APP_ORIGIN`. Sign-in has no session yet, so it checks `Origin` only; that blocks login CSRF.
- **Defence in depth:** SameSite=Lax on the cookie.
- **Lifetime:** the token is stable for the life of a session. Rotating `CSRF_SECRET` invalidates all tokens; the SPA recovers by refetching E-05.

### 4.3 Security headers (all responses)

| Header | Value |
| --- | --- |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src blob:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `same-origin` |
| `Cross-Origin-Opener-Policy` | `same-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=()` |
| `X-Frame-Options` | `DENY` |
| `Strict-Transport-Security` | `max-age=31536000` only when `APP_ORIGIN` uses HTTPS (cloud); never on localhost |

Notes on the policy:

- `'unsafe-inline'` for styles is a deliberate, low-risk trade-off: Radix's scroll lock injects a `<style>` element, and scripts stay strictly `'self'`.
- `frame-src blob:` allows the in-app PDF preview.
- Verify the policy against the built SPA, Radix dialogs and the preview iframe in M7 (V-15).
- The FastAPI docs UI loads CDN assets, which is a further reason it is disabled outside development.

## 5. Authorization and tenant isolation

- **Identity:** the organization comes only from the session (mandatory decision 3). Request bodies never include `org_id`; unknown fields are rejected.
- **Role check:** every tenant endpoint requires membership role `owner`, the only P0-Lite role.
- **Scoped lookups:** every ID is resolved inside the session's organization, with nested IDs inside their parent. Missing and foreign records both return **404**, so the existence of other tenants' records is never revealed. Malformed IDs in paths also return 404.
- **Database relationships:** composite foreign keys (06 §4) and the `stored_files.object_key` prefix check.
- **Unguessable IDs:** random UUIDs (`gen_random_uuid()`). Isolation never depends on IDs being secret; the checks above enforce it.
- **Tests:** IT-TEN-01 to IT-TEN-03 on every build; DC-19 before the demonstration.
- **Production:** row-level security policies keyed on a transaction-local `app.current_org` setting (P1-14).

## 6. Input validation and output encoding

- Pydantic v2 strict models with `extra="forbid"`. Money and quantity values arrive as strings and are checked against the patterns in 09 §4. The body limit is 256 KiB.
- Text is normalised (trimmed, CRLF converted to LF), NUL and control characters are rejected, and lengths are enforced on the server and in the database `CHECK` constraints.
- The API accepts plain text only, never HTML. React escapes text by default; `dangerouslySetInnerHTML` is forbidden. Jinja2 autoescaping covers PDFs.
- SQL goes through SQLAlchemy with bound parameters only. The few raw SQL statements (numbering, the artifact claim) also use bound parameters; string-built SQL is forbidden.
- Redirects: the sign-in `next` parameter accepts only same-origin paths beginning with `/app`, which prevents open redirects.

## 7. File uploads

- **P0-Lite accepts no file uploads.** No endpoint takes multipart data; every body is JSON.
- **P1-03 logo upload rules (for later):**
  - PNG only, at most 1 MB and 2000 × 2000 px;
  - decoded and re-encoded on the server, which strips metadata (the imaging library must be approved as a new dependency);
  - stored privately under `orgs/{org_id}/logos/`;
  - embedded in PDFs only through the restricted fetcher.
- **Never accepted:** SVG, EPS, PDF, HTML or CSS uploads.

## 8. PDF access and storage security

- **Access:**
  - private bucket with no public ACLs and no presigned URLs in P0-Lite;
  - downloads only through E-22, after authentication, the tenant check and SHA-256 verification;
  - responses carry `Content-Disposition: attachment`, `nosniff` and `Cache-Control: no-store`.
- **Credentials:** separate per environment, limited to the one bucket. Locally, SeaweedFS identities refuse anonymous requests (IT-PDF-01).
- **Integrity:** SHA-256 recorded and verified (09 §11); bucket versioning in the cloud.
- **Encryption:** DigitalOcean Spaces offers only customer-provided keys (SSE-C; verify), so **P0 stores synthetic data only**. For production (P1-14, Q-05), choose either application-level envelope encryption (AES-256-GCM with keys from a managed secret store) or a provider with managed-key server-side encryption. Locally there is no encryption at rest; this is acceptable only because the data is synthetic.

## 9. Template rendering restrictions

- Jinja2 with `autoescape=True` and `StrictUndefined`. Templates load only from the registered template directory, and their hash is checked against the registry (09 §11).
- **No user-supplied templates, HTML, CSS, SVG or EPS. Ever.**
- WeasyPrint gets a custom `url_fetcher` that serves only files inside the bundled assets directory and rejects every other scheme and path (UT-SEC-03).
- Rendering:
  - runs in separate worker processes, at most 2 at a time, terminated after 20 s;
  - makes no network calls;
  - has presentational hints off and no attachments.
- WeasyPrint is pinned to `>=70.0,<71` with the exact patch locked, and is updated for security advisories.
- The image contains no Ghostscript.

## 10. Logging and error handling

- **Format:** JSON lines with `ts`, `level`, `request_id`, `user_id`, `org_id`, `route`, `status` and `duration_ms`.
- **Never logged:** passwords, cookies, session tokens or IDs, CSRF tokens, idempotency keys, request bodies, emails (only the hash), addresses, phone numbers, line contents, PDF bytes.
- **Errors:** problem+json with `code`, `detail` and `request_id` only (07 §1.5). Stack traces, SQL and hostnames are logged server-side, never returned. Integrity failures, render failures and unexpected exceptions are logged at ERROR.
- **Retention:** local logs are container logs (ephemeral). Production needs central logging with a retention policy (Q-18) and scrubbing of personal data.

## 11. Secrets

- All secrets come from environment variables (05 §9). `.env`, `.env.test` and `deploy/seaweedfs/s3.json` are git-ignored; the committed examples contain placeholders only.
- Generate `CSRF_SECRET` with, for example, `python -c "import secrets; print(secrets.token_hex(32))"`.
- Different secrets per environment. Database role passwords are long and random.
- In the cloud, secrets are encrypted App Platform environment values. They never go into images, logs, documents, slides or chat.
- If the repository is on GitHub, enable secret scanning and push protection if available (verify).
- **Suspected leak:** rotate the secret. For the demonstration account, create a new account with the CLI and deactivate the old one.

## 12. Audit trails

- The 12 event types and their non-sensitive `details` are listed in 06 §9.
- **Append-only:** the app role has only SELECT and INSERT, and `trg_audit_events_append_only` blocks changes.
- Each event records the actor, organization, subject, IP and request ID.
- Audit events also drive sign-in throttling.
- **Production:** a retention period (Q-18), export for investigations, and optional hash-chaining for tamper evidence (P1-14).

## 13. Privacy limitations

**P0-Lite processes synthetic data only and is not ready for real personal data.** It has:

- no privacy notice or terms;
- no consent records;
- no tooling for data-principal rights (access, correction, erasure);
- no breach-notification process;
- no data processing agreements with hosting providers;
- no encryption at rest for local storage;
- no retention or deletion jobs.

When real data is processed (P1), the product will hold business contact details and customer names, addresses, emails and phone numbers, some of whom may be individuals. India's Digital Personal Data Protection Act 2023 and the DPDP Rules 2025 then apply. The Rules phase in most data-fiduciary obligations around 18 months after notification, around May 2027 (re-verify the dates). Those obligations cover notice, a lawful basis or consent, reasonable security safeguards, breach notification, retention limits and grievance handling. Legal review is required before production (Q-11).

**Payroll data (P2-01)** covers salary, bank details and tax identifiers, the most sensitive data the product would hold. It will need:

- a separate module and schema with restricted grants;
- field-level encryption;
- access restricted to authorised roles, with access auditing;
- minimal retention and an employee-facing notice.

None of it is built until Q-22 is answered.

## 14. Production hardening (P1-14 checklist; needs Heloavy's decisions and budget)

1. PostgreSQL row-level security on all tenant tables.
2. MFA for owners; session management UI.
3. Document encryption (§8); encrypted backups.
4. Managed backups with point-in-time recovery; a quarterly restore drill (§15).
5. Monitoring and alerts: uptime, error rate, render failures, storage errors, database capacity.
6. A durable job queue for renders (replacing in-process background tasks).
7. Dependency and image vulnerability scanning in CI (tools to be approved).
8. Edge rate limiting or a web application firewall.
9. Secret rotation schedule; least-privilege cloud access.
10. Incident response runbook; a penetration test before go-live.
11. DPDP compliance review, privacy notice, data processing agreements (§13).
12. Audit log retention and export; administrative tooling with its own audit.

## 15. Backups

| Context | Procedure |
| --- | --- |
| Demonstration (M8) | With the app stopped, take a consistent pair: a `pg_dump -Fc` of `ps5` and an archive of the SeaweedFS named volume (for example with a temporary container that archives the volume; verify the commands). Also `docker save` the image. Restore all three on the backup machine and run DC-01, DC-14 and DC-17 there (10 §7) |
| Cloud reference (S-02) | Managed PostgreSQL daily backups (verify retention); Spaces versioning |
| Production (P1-14) | Point-in-time recovery; encrypted, versioned object storage with lifecycle rules; an optional cross-region copy (Q-05); recovery point and recovery time objectives agreed with Heloavy (Q-11); quarterly restore drills |

## 16. Data retention

Immutability and retention are separate. Finalised documents remain immutable while they are retained; how long they are retained, and how they are deleted, follows the retention policy Heloavy approves and the applicable legal requirements. Retention-based deletion is not part of P0-Lite. Once the policy exists (Q-18), it will be designed as a separate, audited administrative process outside the application role, which cannot delete finalised records.

| Data | P0-Lite | Production (to decide, Q-18) |
| --- | --- | --- |
| Demonstration data | Deleted after Heloavy's evaluation: remove the volumes; keep the tagged image and the documentation | — |
| Issued documents and PDFs | Kept for the demonstration | The statutory period, reportedly 72 months from the annual-return due date under CGST Act section 36 (verify with a CA) |
| Audit events | Kept | A policy period; export before purge |
| Sessions | Kept (small) | Purge 30 days after expiry |
| Idempotency keys | Kept (small) | Purge after 24 h (P1 job) |
| Erasure requests versus statutory retention | Not applicable | Resolved per legal advice |

## 17. Security testing and incident basics

- **Automated:** UT-SEC-01 to UT-SEC-03, IT-AUTH-01 to IT-AUTH-06, IT-TEN-01 to IT-TEN-03, IT-PDF-01, IT-PDF-02, IT-PDF-05, DB-03 to DB-08, IT-GEN-01 (11 §2).
- **Manual (M7, M8):** cookie attributes and response headers in DevTools; no CSP violations in the console; `/docs` returns 404 with `APP_ENV=demo`; `.env` absent from the image (`docker run --rm hive-docs:local ls -a`; verify the path); `git log` contains no secrets.
- **Demonstration-day incident:** if anything suggests a leak, stop and revoke all sessions (`UPDATE sessions SET revoked_at = now()`), rotate the affected secret and use the fallback machine (10 §7).
