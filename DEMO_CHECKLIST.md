# Demonstration checklist — HIVE DOCS P0-Lite

Demonstration: **Wednesday 25 November 2026, 1:00 PM IST.** This checklist puts `docs/11_QA_AND_ACCEPTANCE.md` §3, §5 and §7 and `docs/10_IMPLEMENTATION_PLAN.md` §7 into one presenter sheet. Setup commands are in [`README.md`](README.md#setting-up-and-running). Evidence and open questions are in [`PROGRESS.md`](PROGRESS.md).

## 1. Blocking decision: the presenter machine

The documented runtime is the Docker stack on the presenter laptop (D-1). On 24 Nov:

- the developer's Windows laptop cannot run Docker (hardware virtualization disabled; no further BIOS attempt);
- the committed Dockerfile has not been built anywhere, so way B in the README is unverified;
- everything below was rehearsed only in the cloud development container (way A, Linux).

Decide by Tuesday evening, and record the choice in `PROGRESS.md`:

| Option | What it needs | Risk |
| --- | --- | --- |
| A Docker-capable laptop (preferred) | Normal internet access to build the image once; then way B | Lowest: the documented path; DC-01 and DC-17 can pass fully |
| The Windows laptop, native (way C) | PostgreSQL 16 and SeaweedFS running natively (both reported installed on 23 Nov), WeasyPrint's native libraries | Untested end to end by Claude Code. Run `uv run pytest` and every DC check on it before relying on it |

Never use mock screens, hard-coded data or a different storage provider to work around this (10 §7 rule 6).

## 2. Tuesday: prepare the machine

- [ ] Check out branch `claude/busy-bell-14l7rh` at the commit recorded in `PROGRESS.md`. `git status` must be clean; `.env`, `.env.test` and `deploy/seaweedfs/s3.json` exist and are not tracked.
- [ ] Start the services and the application (README way B, or A or C). `curl http://localhost:8000/readyz` reports `database`, `storage` and `templates` as `ok`.
- [ ] `cd backend && uv run alembic current` prints `0004_issuance (head)`.
- [ ] Run the automated checks on this machine: `uv run pytest`, then FE-01 to FE-03 (README "Tests"). Expect 534 passing tests.
- [ ] Create the accounts with the CLI, at the hidden prompt: `owner@demo.invalid` ("Demo Owner", "Demo Studio") and `auditor@demo.invalid` ("Isolation Auditor", "Isolation Check Org"). Passwords: at least 12 characters, shared only with the presenter through a private channel, **never written in any file, slide or chat** (12 §2.1).
- [ ] Enter the prepared data (§4): `uv run python scripts/enter_demo_data.py --base-url http://localhost:8000`, or type it in the browser.
- [ ] Sign in as the auditor once and enter a business for "Isolation Check Org" (for example "Isolation Check Studio (Demo)", Mysuru, Karnataka, PIN 570001). Without a business, step 16 shows the business set-up page instead of the not-found message.
- [ ] **Recommended (working assumption, not in the docs):** run DC-01 to DC-20 in a **separate rehearsal account**, so that the prepared data stays exactly as in 11 §5. The DC checks create "Harbour Line Logistics (Demo)" and finalise several invoices; on the demonstration account, step 5 would then create a second Harbour Line customer. To do this, create `rehearsal@demo.invalid` ("Rehearsal Owner", "Rehearsal Studio") and fill it with `scripts/enter_demo_data.py --email rehearsal@demo.invalid`. Run DC-19 with the auditor against a rehearsal invoice URL.
- [ ] Record each DC result (Pass, Fail or Deferred) in `PROGRESS.md` under "Demonstration checks", labelled with this machine's name. Run **DC-03 only once**: 5 failed sign-ins throttle the account and the IP for 15 minutes.
- [ ] Freeze (10 M8.4), only after the DC run passes: tag `v0.1.0-demo`; `docker save` the image (way B); `pg_dump` of `ps5` plus a copy of the SeaweedFS data; export one preview PDF and one final PDF with its SHA-256; record a screen capture of the full script, labelled "Recorded on … from the frozen build".
- [ ] Backup machine (10 §7): the same image or checkout, the restored dump and storage copy, the same `.env`. Test it on Wednesday between 11:00 and 11:45.

## 3. Wednesday: one hour before

- [ ] Laptop on mains power; sleep, screen saver and notifications off.
- [ ] Chrome at 100 % zoom; one normal window and one private window ready (step 16).
- [ ] Stack started; DC-01 run (`/healthz` 200; `/readyz` 200, all `ok`).
- [ ] Signed out. The prepared data is present: the dashboard lists `INV/26-27/00001`, and its details page shows "PDF ready".
- [ ] A terminal ready for step 13: `sha256sum <file>` (Linux, macOS), `Get-FileHash <file> -Algorithm SHA256` (PowerShell) or `certutil -hashfile <file> SHA256` (Windows).
- [ ] Type the password carefully. **Never run `docker compose down -v`** (it deletes every invoice and PDF).

## 4. Prepared data (11 §5)

| Item | Value |
| --- | --- |
| Demonstration account | `owner@demo.invalid`, "Demo Owner", organization "Demo Studio" |
| Isolation account | `auditor@demo.invalid`, "Isolation Auditor", organization "Isolation Check Org", with its own business |
| Business | "Lotus Lane Design Studio (Demo)", 12 Example Road, Indiranagar, Bengaluru, Karnataka (29), PIN 560038, phone +91 80 0000 0000, `accounts@demo.invalid`, **GSTIN empty** |
| Customers | "Riverstone Consulting (Demo)", Pune, Maharashtra (27), 411001 · "Saffron Leaf Foods (Demo)", Chennai, Tamil Nadu (33), 600001 |
| Finalised invoice | `INV/26-27/00001` for Riverstone: F-01 "Brand identity consultation" 2.5 hrs × ₹800.00, 10 % discount = ₹1,800.00; F-02 "Website support hours" 3 hrs × ₹333.33, ₹99.99 discount = ₹900.00; **total ₹2,700.00**; PDF ready |
| Draft | Saffron Leaf: "Menu card design", 1 job × ₹4,500.00 (the line is a working assumption; 11 §5 does not fix it) |
| Created live | "Harbour Line Logistics (Demo)" (step 5) |

Every name carries "(Demo)", every email uses `.invalid`, and phone numbers are placeholders. No real people, companies or GSTINs.

## 5. The five-minute script (E2E-01, 11 §7)

What the screen should show comes from the cloud-container rehearsal of 24 Nov.

| Step | Action | Expected on screen | Say |
| --- | --- | --- | --- |
| 1 | Open `http://localhost:8000/` and let the animation play | Two lines → totals ₹2,700.00 → stamp "FINALISED · INV/26-27/00001", in about 3–4 s | "The server calculates, numbers once and stores the exact PDF it issued." |
| 2 | ENTER THE SYSTEM → sign in | Dashboard | Real Argon2id password check and a server session |
| 3 | Dashboard | "Recent invoices" lists INV/26-27/00001, Riverstone, ₹2,700.00 | The prepared invoice |
| 4 | Business | The profile form; "Issued invoices keep the details they were issued with." | Entered once; issued invoices keep their original details |
| 5 | Customers → New customer: "Harbour Line Logistics (Demo)" (for example Kochi, Kerala) → Save customer | Back in the list; toast "Customer saved." | Saved to PostgreSQL |
| 6 | Invoices → New invoice → choose Harbour Line | The editor opens; "Add your first line item." | A draft is created |
| 7 | Add line: "Brand identity consultation", 2.5, hrs, 800, discount % 10 | Line amount ₹1,800.00 | Calculated by the server |
| 8 | Add line: "Website support hours", 3, hrs, 333.33, discount ₹ 99.99 | ₹900.00; Subtotal ₹2,999.99, Discount −₹299.99, **Total ₹2,700.00** | Decimal arithmetic, half-up per line |
| 9 | Save draft → reload the page | "All changes saved"; the same lines and totals after reload | The draft persists |
| 10 | Preview PDF | The classic layout with a diagonal "DRAFT — NOT ISSUED", "Not yet issued", and the footer "SPECIMEN — demonstration document, not a tax invoice." | Watermark and the SPECIMEN statement |
| 11 | Finalise → Finalise invoice | Heading `INV/26-27/00002` (or the next free number), today's date, status Finalised, read-only details | Next number and today's date, in one transaction |
| 12 | Wait for "PDF ready" → Download PDF → open it | The stored PDF: no watermark, title "Invoice", SPECIMEN footer | The real stored PDF |
| 13 | Open "Integrity"; optionally hash the file | The SHA-256 on the page equals the file's hash | The fingerprint matches |
| 14 | Invoices → Finalised → search "Harb" → open → Download PDF | The same file, byte for byte | Byte-identical file |
| 15 (optional) | Show that there is nothing to edit | Read-only details; no Save draft | Finalised invoices are immutable |
| 16 (optional) | Private window, sign in as `auditor@demo.invalid`, paste the invoice URL | "This invoice doesn't exist or you don't have access." | Tenant isolation |
| 17 | Close | — | Deferred: receipts, payment requests, salary slips, plans, GST after CA approval; next steps (docs/14) |

Step 16 shows the invoice page's own copy (08 §15.4). DC-19's generic wording, "This item doesn't exist or you don't have access to it.", is the 08 §21 fallback; the meaning is the same.

## 6. If a step fails (10 §7)

1. Stay honest: say what failed. Never improvise a workaround that hides it.
2. Fall back to the prepared invoice `INV/26-27/00001`: open it, download it, show its integrity section.
3. If a PDF shows "PDF generation failed", press **Retry PDF**. Retrying is a real feature (DC-18), and the invoice keeps its number.
4. If sign-in is throttled after mistakes, wait 15 minutes or switch to the backup machine. Never reset the database during the demonstration.
5. Backup machine, then the labelled screen recording, then the exported PDFs, in that order.

## 7. After the evaluation (12 §2.1, §16)

- Deactivate the demonstration accounts (`users.is_active = false`) or delete the demonstration data by removing the volumes. Keep the tagged image and the documentation.
- Do not reuse the demonstration passwords anywhere.
