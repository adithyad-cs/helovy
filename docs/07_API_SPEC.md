# 07 — API Specification (P0-Lite)

| | |
| --- | --- |
| Document | HTTP API · version 1.1 · 23 November 2026 |
| Endpoints | **23** (E-01 to E-23). There are no other P0-Lite endpoints |
| Normative companions | 06 (schema), 09 (calculation, validation, finalisation) |

## 1. Conventions

### 1.1 Base URL and format

- Application endpoints live under `/api/v1`. Health endpoints (`/healthz`, `/readyz`) have no prefix.
- Request and response bodies are UTF-8 JSON. A request with a body must send `Content-Type: application/json`, otherwise the API returns 400 `malformed_request`.
- Request bodies are limited to 256 KiB (413 `payload_too_large`).
- Example IDs below are fictional UUIDs; hashes are shortened with `…`.

### 1.2 Authentication

- The session cookie `ps5_session` is set by E-03: HttpOnly, Secure, SameSite=Lax, Path=/, with no Domain attribute.
- Every endpoint except E-01, E-02 and E-03 requires a valid session; a missing, expired or revoked session returns 401 `unauthenticated`.
- The organization is always taken from the session. **No request carries `org_id`.**

### 1.3 CSRF and Origin

- Every POST, PATCH and DELETE request needs both:
  - `X-CSRF-Token: <token>`, the token returned by E-03 or E-05;
  - an `Origin` header equal to `APP_ORIGIN`.
- If either is missing or wrong, the API returns 403 `csrf_failed`.
- E-03 (sign-in) checks only `Origin`, because no session exists yet.

### 1.4 JSON conventions

| Item | Rule |
| --- | --- |
| Keys | `snake_case` |
| IDs | UUID strings; template IDs are strings such as `classic@1`. A malformed UUID in a path returns 404 `not_found` (not 422) |
| Dates | `YYYY-MM-DD` (Asia/Kolkata calendar date) |
| Timestamps | RFC 3339 in UTC, for example `2026-11-25T05:42:10Z` |
| Money and quantities | **JSON strings only**. Input is a plain decimal (`"800"`, `"800.5"`, `"2.500"`) with no exponent, sign, spaces or grouping separators. Output is normalised: money and percent to 2 decimals (`"800.00"`), quantity to 3 decimals (`"2.500"`). A JSON number in a money field gives 422 `must_be_string` |
| Absent optional values | `null` |
| Unknown fields | Rejected: 422 `validation_failed` with field code `unknown_field` |
| PATCH semantics | A field that is present replaces the stored value; an absent field is unchanged; `null` clears an optional field; `lines`, when present, replaces the whole line set |

### 1.5 Errors (RFC 9457 problem details)

Errors use `Content-Type: application/problem+json`:

```json
{
  "type": "https://hive-docs.invalid/problems/validation_failed",
  "title": "Some fields are invalid",
  "status": 422,
  "detail": "2 fields need attention.",
  "instance": "/api/v1/businesses/2c4e6a8b-0d1f-4a3c-9e5b-7d9f1b3d5e7a/calculate",
  "code": "validation_failed",
  "request_id": "req_7Hq2c9LmX4",
  "errors": [
    { "pointer": "/lines/1/discount_value", "code": "exceeds_gross",
      "message": "The discount cannot be more than the line amount (₹999.99)." },
    { "pointer": "/lines/0/quantity", "code": "too_many_decimals",
      "message": "Use at most 3 decimal places." }
  ]
}
```

- `type` uses the placeholder domain `hive-docs.invalid` until the product domain is decided (Q-26). Clients must branch on `code`, never on `type` or `title`.
- `errors[]` appears only for 422 responses.
- Bodies never contain stack traces, SQL or internal hostnames.

**Field error codes (`errors[].code`):**

- `required`, `unknown_field`, `not_null`
- `must_be_string`, `invalid_decimal`, `too_many_decimals`
- `out_of_range`, `too_long`, `too_short`, `invalid_format`, `invalid_choice`
- `exceeds_gross`, `state_mismatch`, `not_found`, `inactive`
- `too_many_lines`, `no_lines`, `total_too_large`, `zero_total`, `due_date_before_issue_date`

### 1.6 Concurrency (ETag / If-Match)

- `businesses`, `customers` and `documents` responses carry a strong `ETag: "<version>"`, for example `ETag: "4"`.
- PATCH, DELETE and finalise require `If-Match: "<version>"`:
  - missing → 428 `precondition_required`;
  - different from the current version → 412 `version_mismatch`.
- A successful change increments `version` and returns the new ETag.

### 1.7 Idempotency (finalise only)

- E-21 requires `Idempotency-Key`: 8–128 characters from `[A-Za-z0-9_-]`. The SPA sends `crypto.randomUUID()`.
  - Missing → 400 `idempotency_key_missing`.
  - Badly formed → 400 `malformed_request`.
- Keys are scoped per organization and per operation (`document.finalize`). The request fingerprint is the SHA-256 of method, path, document ID and `If-Match` (09 §8).
- **Same key and same fingerprint, already completed:** the stored status and body are replayed with the header `Idempotent-Replayed: true`. They are not recomputed.
- **Same key, different fingerprint:** 422 `idempotency_key_mismatch`.
- **Same key while the first request is still running:** 409 `idempotency_in_progress` (the lock times out after 5 s). The client retries with the same key.

### 1.8 Pagination

- List endpoints accept `limit` (1–50, default 20) and `cursor` (opaque; take it from `next_cursor`).
- Order is `created_at DESC, id DESC`.
- Response shape: `{ "items": [...], "next_cursor": "eyJ0IjoiMjAyNi0xMS0yNVQwNTo0MjoxMFoiLCJpZCI6IjRlNmEifQ" | null }`.
- A tampered or foreign cursor gives 422 `validation_failed` (pointer `/cursor`).

### 1.9 Rate limits

| Scope | Limit | Key | Storage |
| --- | --- | --- | --- |
| E-03 sign-in | 5 failures in 15 minutes, then 429 | Email hash, and separately client IP | Database (`audit_events`); survives restarts |
| E-14 calculate | 60 requests per minute | Session | In-memory (single process) |
| E-20 preview | 20 requests per minute | Session | In-memory |
| E-23 render retry | 1 request per 10 s | Document | In-memory |

A 429 response includes `Retry-After` in seconds.

### 1.10 Common response headers

- `X-Request-ID` echoes a client value that matches `^[A-Za-z0-9_-]{8,64}$`, or a generated one.
- `Cache-Control: no-store` on every API response, including PDFs.
- The security headers in 12 §4.

### 1.11 Permissions

P0-Lite has one role, `owner`. Every tenant endpoint checks that the session's membership role is `owner`; otherwise it returns 403 `forbidden_role`. That error cannot happen in P0-Lite, because every member is an owner; it becomes meaningful with P1-02.

### 1.12 Error code catalogue

| HTTP | `code` | When | SPA behaviour (copy in 08 §21) |
| --- | --- | --- | --- |
| 400 | `malformed_request` | Invalid JSON, wrong content type, bad header format | Generic error toast |
| 400 | `idempotency_key_missing` | E-21 without `Idempotency-Key` | Bug; generic error |
| 401 | `unauthenticated` | No valid session | Redirect to `/login?next=` |
| 401 | `invalid_credentials` | Wrong email or password, or inactive user | "Email or password is incorrect." |
| 403 | `csrf_failed` | Missing or bad CSRF token or Origin | Refetch `me`, then ask the user to retry |
| 403 | `forbidden_role` | Role not allowed (P1) | Not reachable in P0-Lite |
| 404 | `not_found` | Missing, or belongs to another organization | Not-found state |
| 409 | `business_already_exists` | E-06 when a business exists | Redirect to the profile |
| 409 | `document_not_draft` | Edit, delete, preview or finalise on a finalised document | Reload the document (read-only) |
| 409 | `document_not_finalized` | Download or retry on a draft | Reload |
| 409 | `pdf_not_ready` | Download while the PDF is `pending` or `failed` | Show the PDF status and Retry |
| 409 | `pdf_render_in_progress` | Retry while `pending` for less than 120 s | "Still generating…" |
| 409 | `number_series_exhausted` | Sequence past 999,999 for the year | Error; contact support |
| 409 | `idempotency_in_progress` | Concurrent request with the same key | Retry with the same key after 2 s |
| 412 | `version_mismatch` | Stale `If-Match` | Offer to reload |
| 413 | `payload_too_large` | Body over 256 KiB | Error toast |
| 422 | `validation_failed` | Field errors (`errors[]`) | Map onto fields |
| 422 | `finalization_blocked` | Preconditions in 09 §8 not met (`errors[]`) | List the reasons in the dialog |
| 422 | `idempotency_key_mismatch` | Key reused for a different request | Bug; generic error |
| 428 | `precondition_required` | Missing `If-Match` | Bug; generic error |
| 429 | `rate_limited` | Limits in §1.9 | Show the wait time |
| 500 | `internal_error` | Unexpected error | Generic error with request ID |
| 500 | `integrity_check_failed` | The stored PDF does not match its SHA-256 | Error with request ID; the file is not served |
| 503 | `dependency_unavailable` | Database, storage or renderer unavailable, or a lock timeout outside idempotency | "Service temporarily unavailable" with Retry |

## 2. Endpoint index

| ID | Method | Path | Session | CSRF | Milestone |
| --- | --- | --- | --- | --- | --- |
| E-01 | GET | `/healthz` | No | No | M0 |
| E-02 | GET | `/readyz` | No | No | M0 (template check in M4) |
| E-03 | POST | `/api/v1/auth/login` | No | Origin only | M1 |
| E-04 | POST | `/api/v1/auth/logout` | Yes | Yes | M1 |
| E-05 | GET | `/api/v1/auth/me` | Yes | No | M1 |
| E-06 | POST | `/api/v1/businesses` | Yes | Yes | M2 |
| E-07 | GET | `/api/v1/businesses/{business_id}` | Yes | No | M2 |
| E-08 | PATCH | `/api/v1/businesses/{business_id}` | Yes | Yes | M2 |
| E-09 | GET | `/api/v1/businesses/{business_id}/customers` | Yes | No | M2 |
| E-10 | POST | `/api/v1/businesses/{business_id}/customers` | Yes | Yes | M2 |
| E-11 | GET | `/api/v1/businesses/{business_id}/customers/{customer_id}` | Yes | No | M2 |
| E-12 | PATCH | `/api/v1/businesses/{business_id}/customers/{customer_id}` | Yes | Yes | M2 |
| E-13 | GET | `/api/v1/templates?doc_type=invoice` | Yes | No | M3 |
| E-14 | POST | `/api/v1/businesses/{business_id}/calculate` | Yes | Yes | M3 |
| E-15 | POST | `/api/v1/businesses/{business_id}/documents` | Yes | Yes | M3 |
| E-16 | GET | `/api/v1/businesses/{business_id}/documents` | Yes | No | M6 |
| E-17 | GET | `/api/v1/documents/{document_id}` | Yes | No | M3 |
| E-18 | PATCH | `/api/v1/documents/{document_id}` | Yes | Yes | M3 |
| E-19 | DELETE | `/api/v1/documents/{document_id}` | Yes | Yes | M3 |
| E-20 | GET | `/api/v1/documents/{document_id}/preview.pdf` | Yes | No | M4 |
| E-21 | POST | `/api/v1/documents/{document_id}/finalize` | Yes | Yes | M5 |
| E-22 | GET | `/api/v1/documents/{document_id}/pdf` | Yes | No | M5 |
| E-23 | POST | `/api/v1/documents/{document_id}/pdf/render` | Yes | Yes | M5 |

## 3. Resource representations

### 3.1 Business

```json
{
  "id": "2c4e6a8b-0d1f-4a3c-9e5b-7d9f1b3d5e7a",
  "legal_name": "Lotus Lane Design Studio (Demo)",
  "trade_name": null,
  "address_line1": "12 Example Road",
  "address_line2": "Indiranagar",
  "city": "Bengaluru",
  "state_code": "29",
  "state_name": "Karnataka",
  "postal_code": "560038",
  "country_code": "IN",
  "phone": "+91 80 0000 0000",
  "email": "accounts@demo.invalid",
  "gstin": null,
  "version": 1,
  "created_at": "2026-11-24T04:10:00Z",
  "updated_at": "2026-11-24T04:10:00Z"
}
```

`state_name` is derived for display from the state list in 09 §4. It is not stored.

### 3.2 Customer

```json
{
  "id": "3d5f7b9c-1e2a-4b4d-8f6c-8e0a2c4e6f8b",
  "display_name": "Riverstone Consulting (Demo)",
  "contact_name": "A. Kumar",
  "email": "ap@riverstone.invalid",
  "phone": null,
  "address_line1": "4th Floor, Sample Towers",
  "address_line2": null,
  "city": "Pune",
  "state_code": "27",
  "state_name": "Maharashtra",
  "postal_code": "411001",
  "country_code": "IN",
  "gstin": null,
  "version": 1,
  "created_at": "2026-11-24T04:15:00Z",
  "updated_at": "2026-11-24T04:15:00Z"
}
```

List items (E-09) use a summary: `id`, `display_name`, `contact_name`, `email`, `city`, `created_at`.

### 3.3 Document (draft and finalised)

Lines in requests contain only inputs: `description`, `quantity`, `unit`, `unit_price`, `discount_type`, `discount_value`. Position comes from the array order. Responses add `position` and the computed values.

```json
{
  "id": "4e6a8c0d-2f3b-4c5e-9a7d-9f1b3d5f7a9c",
  "business_id": "2c4e6a8b-0d1f-4a3c-9e5b-7d9f1b3d5e7a",
  "doc_type": "invoice",
  "status": "finalized",
  "tax_mode": "no_tax",
  "template_id": "classic@1",
  "currency": "INR",
  "customer": { "id": "3d5f7b9c-1e2a-4b4d-8f6c-8e0a2c4e6f8b",
                "display_name": "Riverstone Consulting (Demo)" },
  "number": "INV/26-27/00001",
  "issue_date": "2026-11-25",
  "due_date": "2026-12-10",
  "reference": "PO-4471",
  "notes": "Thank you for your business.",
  "terms": "Payment within 15 days of the invoice date.",
  "lines": [
    { "position": 1, "description": "Brand identity consultation",
      "quantity": "2.500", "unit": "hrs", "unit_price": "800.00",
      "discount_type": "percent", "discount_value": "10.00",
      "gross": "2000.00", "discount": "200.00", "line_total": "1800.00" },
    { "position": 2, "description": "Website support hours",
      "quantity": "3.000", "unit": "hrs", "unit_price": "333.33",
      "discount_type": "amount", "discount_value": "99.99",
      "gross": "999.99", "discount": "99.99", "line_total": "900.00" }
  ],
  "totals": { "gross_total": "2999.99", "discount_total": "299.99", "grand_total": "2700.00" },
  "calc_version": "calc-1.0.0",
  "finalized_at": "2026-11-25T05:42:10Z",
  "snapshot_sha256": "a3f5c9…",
  "pdf": { "status": "ready", "sha256": "7be21d…", "size_bytes": 48213,
           "rendered_at": "2026-11-25T05:42:13Z", "attempts": 1,
           "last_error_code": null, "retry_available": false },
  "version": 4,
  "created_at": "2026-11-24T06:00:00Z",
  "updated_at": "2026-11-25T05:42:10Z"
}
```

- **Draft:** `status` is `"draft"`; `number`, `issue_date`, `finalized_at`, `snapshot_sha256` and `pdf` are `null`. Lines and totals are computed from the stored inputs on every read. `customer.display_name` is the current customer name.
- **Finalised:** everything comes from the snapshot, including the buyer name as issued, except `pdf` and `version`.
- **`pdf.retry_available`** is `true` when `status` is `failed`, or `pending` for more than 120 s.
- **Field mapping:** the API field `number` is the column `documents.document_number`; `snapshot_sha256` is `document_snapshots.canonical_sha256`; `pdf.sha256` and `pdf.size_bytes` come from `stored_files`.

### 3.4 Document list item (E-16)

```json
{
  "id": "4e6a8c0d-2f3b-4c5e-9a7d-9f1b3d5f7a9c",
  "status": "finalized",
  "number": "INV/26-27/00001",
  "customer_name": "Riverstone Consulting (Demo)",
  "issue_date": "2026-11-25",
  "grand_total": "2700.00",
  "pdf_status": "ready",
  "created_at": "2026-11-24T06:00:00Z",
  "updated_at": "2026-11-25T05:42:10Z"
}
```

For drafts, `number`, `issue_date`, `grand_total` and `pdf_status` are `null`, and `customer_name` is the current customer name. Drafts store no totals (09 §9).

## 4. Endpoints

Every tenant endpoint below:

- requires the session and role `owner` (§1.11);
- resolves every path ID inside the session's organization, with nested IDs inside their parent;
- returns 404 `not_found` for anything outside that scope;
- may return 401, 403 `csrf_failed` (unsafe methods), 413, 429 (where limited), 500 and 503, which are not repeated in each entry.

### E-01 `GET /healthz`

- **Purpose:** liveness. **Authentication:** none. **Tenant scope:** none.
- **Response 200:** `{"status": "ok"}`. It never touches the database or storage.

### E-02 `GET /readyz`

- **Purpose:** readiness for traffic. **Authentication:** none.
- **Checks:**
  - database: `SELECT 1` with the app role;
  - storage: HeadBucket on `S3_BUCKET`;
  - templates: the registry hashes match the files on disk. With `APP_ENV=development` a mismatch reports `"warn"`; with `demo` or `production` it fails.
- **Response 200:** `{"status": "ready", "checks": {"database": "ok", "storage": "ok", "templates": "ok"}}`.
- **Response 503:** `{"status": "not_ready", "checks": {"database": "ok", "storage": "error", "templates": "ok"}}`, with no error details.

### E-03 `POST /api/v1/auth/login`

- **Purpose:** sign in. **Authentication:** none; `Origin` must equal `APP_ORIGIN`.
- **Request:** `{"email": "owner@demo.invalid", "password": "••••••••••••"}`.
- **Validation:** email of 3–254 characters, trimmed and lower-cased; password of 1–1024 characters.
- **Behaviour:**
  1. Apply throttling (§1.9).
  2. Look up the user and verify Argon2id. For an unknown email, a dummy verification keeps the timing similar.
  3. On success, revoke any session already presented in the cookie, then create a new session (prevents session fixation).
  4. Audit `auth.login_succeeded` or `auth.login_failed`.
- **Response 200**, with `Set-Cookie: ps5_session=<token>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=604800`:

  ```json
  {
    "user": { "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d", "email": "owner@demo.invalid", "display_name": "Demo Owner" },
    "organization": { "id": "0b7e2f4a-1c3d-4e5f-8a9b-0c1d2e3f4a5b", "name": "Demo Studio" },
    "role": "owner",
    "business": null,
    "csrf_token": "3q2-7wEXAMPLEtokenbase64url",
    "session_expires_at": "2026-12-01T04:00:00Z"
  }
  ```

- **Errors:**
  - 400 `malformed_request`;
  - 401 `invalid_credentials` (identical for unknown email, wrong password and inactive user);
  - 403 `csrf_failed` (bad `Origin`);
  - 422 `validation_failed`;
  - 429 `rate_limited`.
- **Idempotency and concurrency:** not idempotent; each success creates a new session.

### E-04 `POST /api/v1/auth/logout`

- **Purpose:** sign out. **Authentication:** session + CSRF. **Request:** no body.
- **Response 204.** It sets `revoked_at`, clears the cookie (`Max-Age=0`) and audits `auth.logout`.
- **Errors:** 401, 403 `csrf_failed`.
- **Idempotency:** a second call with the same, now revoked, cookie returns 401.

### E-05 `GET /api/v1/auth/me`

- **Purpose:** the current session context, used by the route guard and on page load.
- **Response 200:** the same body as E-03 (with a non-null `business` once one exists: `{"id": "…", "legal_name": "…"}`). No cookie is set.
- **Errors:** 401 `unauthenticated`.

### E-06 `POST /api/v1/businesses`

- **Purpose:** create the organization's single business (L-04).
- **Request:** the Business fields from §3.1, without `id`, `state_name`, `version` or timestamps. `legal_name`, `address_line1`, `city`, `state_code` and `postal_code` are required.
- **Validation:** 09 §4: lengths, state code in the list, PIN code pattern, phone pattern, email format, and the GSTIN pattern with its first two digits equal to `state_code`.
- **Response 201:** Business, plus `ETag: "1"` and `Location: /api/v1/businesses/{id}`. Audit `business.created`.
- **Errors:** 409 `business_already_exists`; 422 `validation_failed`.
- **Concurrency:** two simultaneous creates: `businesses_one_per_org_uq` lets one succeed and the other gets 409.

### E-07 `GET /api/v1/businesses/{business_id}`

- **Purpose:** read the profile. **Response 200:** Business + ETag. **Errors:** 404.

### E-08 `PATCH /api/v1/businesses/{business_id}`

- **Purpose:** edit the profile.
- **Headers:** `If-Match`. **Request:** any subset of the E-06 fields; required fields cannot be `null` (`not_null`).
- **Response 200:** Business with the new ETag. Audit `business.updated` with the changed field names.
- **Errors:** 404, 412, 422, 428.
- **Effect on issued documents:** none (BR-11).

### E-09 `GET /api/v1/businesses/{business_id}/customers`

- **Purpose:** list and search customers.
- **Query:** `q` (optional, 1–100 characters; case-insensitive **prefix** of `display_name`), `limit`, `cursor`.
- **Response 200:** `{"items": [Customer summary], "next_cursor": null}`. **Errors:** 404, 422.

### E-10 `POST /api/v1/businesses/{business_id}/customers`

- **Purpose:** create a customer.
- **Request:** the Customer fields from §3.2 (only `display_name` is required).
- **Validation:** 09 §4. If both `gstin` and `state_code` are given, they must match (`state_mismatch`).
- **Response 201:** Customer + ETag + `Location`. Audit `customer.created`.
- **Errors:** 404 (business), 422.

### E-11 `GET /api/v1/businesses/{business_id}/customers/{customer_id}`

- **Response 200:** Customer + ETag. **Errors:** 404 (including a customer of another business or organization).

### E-12 `PATCH /api/v1/businesses/{business_id}/customers/{customer_id}`

- **Headers:** `If-Match`. **Request:** any subset of the Customer fields; `display_name` cannot be `null`.
- **Response 200:** Customer + new ETag. Audit `customer.updated`.
- **Errors:** 404, 412, 422, 428.
- **Effect on issued documents:** none; their buyer details come from the snapshot.

### E-13 `GET /api/v1/templates?doc_type=invoice`

- **Purpose:** the template catalogue for the selector and the Templates page. **Tenant scope:** global, read-only.
- **Query:** `doc_type` (optional, default `invoice`; any other value gives 422 `invalid_choice`).
- **Response 200:**

  ```json
  { "items": [ { "id": "classic@1", "code": "classic", "version": 1, "name": "Classic",
                 "description": "A clean, traditional A4 invoice layout.",
                 "tier": "free", "doc_type": "invoice" } ] }
  ```

  Only active templates are listed. With S-01, `minimal@1` is added.

### E-14 `POST /api/v1/businesses/{business_id}/calculate`

- **Purpose:** stateless server calculation for live totals in the editor (L-07).
- **Request:**

  ```json
  { "lines": [
      { "quantity": "2.5", "unit_price": "800", "discount_type": "percent", "discount_value": "10" },
      { "quantity": "3",   "unit_price": "333.33", "discount_type": "amount", "discount_value": "99.99" } ] }
  ```

  0–200 lines; the line fields and limits are in 09 §4. An empty list returns zero totals.
- **Response 200:**

  ```json
  { "calc_version": "calc-1.0.0",
    "lines": [ { "position": 1, "gross": "2000.00", "discount": "200.00", "line_total": "1800.00" },
               { "position": 2, "gross": "999.99",  "discount": "99.99",  "line_total": "900.00" } ],
    "totals": { "gross_total": "2999.99", "discount_total": "299.99", "grand_total": "2700.00" } }
  ```

- **Errors:** 404, 422 (pointers such as `/lines/0/quantity`), 429 (60 per minute).
- **Idempotency:** pure; nothing is stored.

### E-15 `POST /api/v1/businesses/{business_id}/documents`

- **Purpose:** create an invoice draft (L-06).
- **Request:**

  ```json
  { "doc_type": "invoice", "customer_id": "3d5f7b9c-1e2a-4b4d-8f6c-8e0a2c4e6f8b",
    "template_id": "classic@1", "reference": "PO-4471", "due_date": "2026-12-10",
    "notes": null, "terms": "Payment within 15 days of the invoice date.", "lines": [] }
  ```

  Only `customer_id` is required. `doc_type` defaults to `invoice`, `template_id` to `classic@1`, and `lines` to empty (0–200 lines).
- **Validation:**
  - `customer_id` must belong to this business, else 422 `not_found` at `/customer_id`;
  - `template_id` must be an active invoice template (`not_found` or `inactive`);
  - every line follows 09 §4.
- **Response 201:** Document (draft) + `ETag: "1"` + `Location: /api/v1/documents/{id}`.
- **Errors:** 404 (business), 422.

### E-16 `GET /api/v1/businesses/{business_id}/documents`

- **Purpose:** history list and dashboard recents (L-12, L-13).
- **Query:**
  - `status`: `draft` | `finalized` | omitted for all;
  - `q`: 1–50 characters. A case-insensitive prefix of the document number, or of the customer name shown (the snapshot buyer name for finalised documents, the current name for drafts);
  - `limit`, `cursor`.
- **Response 200:** `{"items": [Document list item], "next_cursor": "…"}`.
- **Errors:** 404, 422.
- **Note:** the `q` search runs without a dedicated index, which is adequate for P0-Lite volumes (thousands of documents).

### E-17 `GET /api/v1/documents/{document_id}`

- **Purpose:** open a draft in the editor, or show an issued invoice (L-12).
- **Response 200:** Document (§3.3) + ETag.
- **Errors:** 404.

### E-18 `PATCH /api/v1/documents/{document_id}`

- **Purpose:** save a draft.
- **Headers:** `If-Match`, CSRF.
- **Request:** any of `customer_id`, `template_id`, `reference`, `due_date`, `notes`, `terms`, `lines` (a full replacement of 0–200 lines).
- **Behaviour:** locks the document row (`FOR UPDATE`), checks the status and version, replaces the lines if given, and increments `version`, all in one transaction.
- **Response 200:** Document (draft, recomputed) + new ETag.
- **Errors:** 404, 409 `document_not_draft`, 412, 422, 428.

### E-19 `DELETE /api/v1/documents/{document_id}`

- **Purpose:** delete a draft. **Headers:** `If-Match`, CSRF.
- **Response 204.** The lines are removed by cascade.
- **Errors:** 404, 409 `document_not_draft`, 412, 428.

### E-20 `GET /api/v1/documents/{document_id}/preview.pdf`

- **Purpose:** watermarked draft preview (L-09).
- **Behaviour:** builds a preview payload from the current draft (same shape as the snapshot, `number` null, watermark on) and renders it in a worker. Nothing is stored and no audit event is written.
- **Response 200:** `Content-Type: application/pdf`, `Content-Disposition: inline; filename="draft-preview.pdf"`, `Cache-Control: no-store`.
- **Errors:**
  - 404;
  - 409 `document_not_draft`;
  - 422 `validation_failed` (`no_lines` when the draft has no lines);
  - 429 (20 per minute);
  - 503 `dependency_unavailable` (render timeout or no renderer available).

### E-21 `POST /api/v1/documents/{document_id}/finalize`

- **Purpose:** issue the invoice atomically (L-10).
- **Headers:** `Idempotency-Key`, `If-Match`, `X-CSRF-Token`. **Request:** no body.
- **Behaviour:** the transaction in 09 §8. After commit, the final PDF render is scheduled as a background task.
- **Response 200:** Document (finalised) with `pdf.status = "pending"` + new ETag. A replay returns the stored body with `Idempotent-Replayed: true`. The SPA then polls E-17 until `pdf.status` is `ready` or `failed`.
- **Errors:**
  - 400 `idempotency_key_missing` | `malformed_request`;
  - 404;
  - 409 `document_not_draft` | `idempotency_in_progress` | `number_series_exhausted`;
  - 412 `version_mismatch`;
  - 422 `finalization_blocked`, with `errors[]` codes from `no_lines`, `zero_total`, `total_too_large`, `due_date_before_issue_date`, `inactive` and any line validation code;
  - 422 `idempotency_key_mismatch`;
  - 428 `precondition_required`;
  - 503 `dependency_unavailable`.
- **Concurrency:** lock order idempotency record → document → number series. Concurrent finalisations of different drafts get consecutive, unique numbers. Two different keys for the same draft give one success and one 409 `document_not_draft`.

### E-22 `GET /api/v1/documents/{document_id}/pdf`

- **Purpose:** download the issued PDF (L-11, L-12).
- **Behaviour:**
  1. The document must be finalised and its artifact `ready`.
  2. Read the object and compute its SHA-256.
  3. It must equal `stored_files.sha256`, otherwise 500 `integrity_check_failed` (logged at ERROR; the file is not served).
  4. Audit `document.pdf_downloaded`.
- **Response 200:** the PDF bytes, with:
  - `Content-Type: application/pdf`;
  - `Content-Disposition: attachment; filename="INV-26-27-00001.pdf"` (`/` replaced by `-`);
  - `Content-Digest: sha-256=:<base64 of the digest>:` (RFC 9530);
  - `Cache-Control: no-store`.
- **Errors:** 404; 409 `document_not_finalized`; 409 `pdf_not_ready` (the body includes `"pdf_status": "pending" | "failed"`); 500 `integrity_check_failed`; 503 (storage unreachable).
- **Idempotency:** safe; every download returns the same bytes.

### E-23 `POST /api/v1/documents/{document_id}/pdf/render`

- **Purpose:** retry the final PDF without renumbering (L-11).
- **Headers:** CSRF. **Request:** no body.
- **Behaviour:** claims the artifact atomically:

  ```sql
  UPDATE document_artifacts SET status = 'pending', attempts = attempts + 1, updated_at = now()
  WHERE id = :artifact AND (status = 'failed'
     OR (status = 'pending' AND updated_at < now() - interval '120 seconds'))
  RETURNING …
  ```

  On a successful claim, the render is scheduled from the **same snapshot**.
- **Responses:**
  - 202 `{"pdf": {"status": "pending", "attempts": 2, …}}` (retry scheduled);
  - 200 `{"pdf": {"status": "ready", …}}` (already ready; nothing done).
- **Errors:** 404; 409 `document_not_finalized`; 409 `pdf_render_in_progress` (pending for less than 120 s); 429 (1 per 10 s per document).
- **Idempotency:** naturally idempotent through the claim condition; concurrent retries cannot both claim.
