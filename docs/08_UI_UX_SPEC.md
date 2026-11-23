# 08 — UI and UX Specification

| | |
| --- | --- |
| Document | Frontend experience · version 1.2 · 23 November 2026 |
| Scope | Every P0-Lite screen. Nothing outside 03 §2 may appear (03 §8) |
| Stack | React 18, React Router, TanStack Query, React Hook Form + Zod, Tailwind, Radix (04 §4) |

## 1. Design direction: "The Ledger Assembles"

The product should feel like a well-kept ledger: calm, precise and trustworthy. Paper and ink colours, generous white space, figures that line up, and motion used only to explain what just happened (a line was added, a total was calculated, a document was locked). There are no stock photos, no gradients and no decorative illustrations unrelated to documents.

Principles:

1. **Numbers first:** amounts are large, right-aligned and in tabular figures.
2. **State is always visible:** Draft, Finalised and PDF status are shown in words, not only in colour.
3. **Irreversible actions are explicit:** finalising and deleting always ask for confirmation, in plain language.
4. **Honest labels:** "Specimen" and "Demonstration build" are visible where documents appear.

## 2. Design system: components

Each component in `src/components/ui/` wraps a Radix primitive or semantic HTML and is styled with the tokens in §3–§5.

| Component | Base | Use |
| --- | --- | --- |
| Button (primary, secondary, ghost, danger; sizes md and lg; loading state) | `<button>` | All actions; at least 40 px tall |
| TextField, TextArea (with counter), FieldError, FormSection | `<input>`, `<textarea>` | Forms; labels always visible |
| MoneyInput, QuantityInput | `<input inputmode="decimal">` | Text-based decimal entry, never `type="number"` |
| DateInput | native `<input type="date">` | Due date |
| Select | Radix Select | State, discount type, template |
| CustomerPicker | Radix Popover + listbox driven by E-09 search | Choosing a customer in the editor |
| Dialog, AlertDialog | Radix Dialog, AlertDialog | Quick-create customer; preview; finalise and delete confirmations |
| Drawer | Radix Dialog (side sheet) | Mobile navigation |
| DropdownMenu | Radix DropdownMenu | User menu |
| Toast | Radix Toast | Success and error notices (4 s; errors stay until dismissed) |
| Tooltip | Radix Tooltip | Hash and help hints (never essential information) |
| Table / CardList | `<table>` / `<ul>` | Lists: a table at 768 px and above, cards below |
| StatusPill | `<span>` with text | Draft / Finalised; PDF Pending / Ready / Failed |
| MoneyText | `<span>` | Formatted ₹ amounts (09 §6), tabular figures |
| EmptyState, ErrorState, Skeleton, Spinner, Banner | — | Page states (§9) |
| PageHeader | — | Page title (`h1`) + primary action |

## 3. Typography

| Role | Family | Size / line height | Weight |
| --- | --- | --- | --- |
| Landing display | Source Serif 4 | 48/56 px (desktop), 34/40 px (mobile) | 600 |
| Page title (`h1`) | Source Serif 4 | 30/36 px (desktop), 24/30 px (mobile) | 600 |
| Section title (`h2`) | Inter | 20/28 px | 600 |
| Body | Inter | 16/24 px | 400 |
| Small, labels | Inter | 14/20 px | 500 |
| Caption | Inter | 12/16 px | 400 |
| Amounts | Inter, `font-variant-numeric: tabular-nums` | Inherits; grand totals 24–30 px | 600 |

- Fonts are self-hosted WOFF2 files with `font-display: swap`; there are no requests to font CDNs.
- Inputs use at least 16 px on mobile to avoid automatic zoom.
- PDFs use the bundled Noto fonts instead (§20).

## 4. Colour tokens

Defined as CSS variables and mapped into Tailwind. The contrast ratios below are approximate, computed while writing this document; verify them with a contrast checker in M7.

| Token | Hex | Use | Contrast (approx.) |
| --- | --- | --- | --- |
| `--ink` | `#1B2A41` | Primary text | 13.6:1 on `--paper` |
| `--ink-muted` | `#5B6472` | Secondary text, captions | 6.0:1 on `--surface` |
| `--paper` | `#FAF8F3` | App background | — |
| `--surface` | `#FFFFFF` | Cards, inputs, dialogs | — |
| `--line` | `#D9D4C7` | Decorative dividers only (never the only boundary of a control) | — |
| `--field-border` | `#8A8272` | Input and select borders | 3.8:1 on `--surface` (meets 3:1 for UI components) |
| `--accent` | `#1F7A5A` | Primary buttons, links, Finalised status | 5.3:1 with white text |
| `--accent-hover` | `#17614A` | Hover and pressed states | higher than `--accent` |
| `--danger` | `#B42318` | Errors, destructive actions, PDF Failed | 6.6:1 on white |
| `--warning` | `#8A5A00` | PDF Pending, notices | 5.9:1 on white |
| `--focus` | `#2563EB` | Focus ring (2 px, offset 2 px) | 5.2:1 on white |
| `--tint-accent` | `#E7F3EE` | Finalised pill background | `--accent` text at 4.6:1 |
| `--tint-danger` | `#FDECEA` | Failed pill background | `--danger` text at 5.8:1 |
| `--tint-warning` | `#FBF3E3` | Pending pill background | `--warning` text at 5.4:1 |
| `--tint-neutral` | `#EEF0F3` | Draft pill background | `--ink-muted` text at 5.3:1 |

There is no dark theme in P0-Lite.

## 5. Spacing and layout

- **Spacing scale (4 px base):** 4, 8, 12, 16, 24, 32, 48, 64.
- **Radius:** 6 px for controls, 10 px for cards and dialogs.
- **Elevation:** one soft shadow for dialogs and popovers; cards use a border, not a shadow.
- **Layout:** content width at most 1200 px. Page padding is 16 px below 768 px, 24 px from 768 px and 32 px from 1280 px. The top bar is 56 px tall.
- **Forms:** one column below 768 px; two columns for short fields (city, state, PIN code) from 768 px.

## 6. Responsive behaviour

| Breakpoint | Width | Behaviour |
| --- | --- | --- |
| Base | ≥ 360 px | Single column; navigation in a drawer; lists as cards; editor lines as stacked cards; sticky bottom bar with the grand total and the primary action |
| `md` | ≥ 768 px | Top navigation links; lists as tables; editor lines as table rows (description wraps) |
| `lg` | ≥ 1280 px | Editor in two columns (lines on the left, sticky summary on the right); the landing hero sits side by side with the animation |

Testing widths: 360, 768 and 1280 px (FE-04; R5 reduces this to 360 and 1280).

## 7. Motion principles

1. **Purposeful:** motion explains a change of state (an item added, a total updated, a document locked). It is never decorative looping.
2. **Fast:** interface transitions take 150–250 ms with an ease-out curve. The landing animation finishes in under 5 s and plays once.
3. **Stable:** no layout shift. Amounts update in place with a brief background highlight (600 ms fade); digits do not count up.
4. **Respectful:** under `prefers-reduced-motion: reduce`, every non-essential animation is disabled and the landing page shows its final frame.
5. **Lightweight:** CSS transitions and keyframes only; no animation libraries (05 §3).

## 8. Accessibility (target: WCAG 2.2 AA, not certified)

- **Structure:** semantic landmarks (`header`, `nav`, `main`), one `h1` per page, a "Skip to content" link, and `lang="en-IN"`.
- **Forms:**
  - every input has a visible `<label>`;
  - required fields say "(required)" in text;
  - errors are linked with `aria-describedby`;
  - after a failed submit, focus moves to the first invalid field and an error summary appears at the top.
- **Keyboard:** every action is reachable by keyboard. Focus is always visible (`--focus` ring). Dialogs trap and restore focus (Radix). On route change, focus moves to the page `h1`.
- **Announcements:** `aria-live="polite"` regions announce "Saved", "Totals updated", "PDF ready" and "PDF generation failed".
- **Colour:** status is never conveyed by colour alone; pills always contain text.
- **Targets:** at least 24 × 24 px (WCAG 2.2, 2.5.8); buttons are 40 px or taller.
- **Tables:** `<th scope>` headers; amounts right-aligned; mobile cards repeat the labels.
- **Landing animation:** wrapped in a `figure` with a text description (§10.2). It is not needed to understand the page.

## 9. Global interaction patterns

| Situation | Behaviour |
| --- | --- |
| Loading | Skeletons appear after 200 ms (no flash for fast responses); buttons show a spinner and are disabled while submitting |
| Empty | EmptyState: an icon, one sentence explaining why it is empty, and the next action |
| Error | ErrorState: plain message (§21), request ID in small text, and a Retry button. Field errors appear inline |
| Success | Toast for 4 s: "Customer saved.", "Invoice INV/26-27/00001 finalised." |
| Double submit | Prevented: buttons are disabled while their request is in flight |
| Unsaved changes | A route blocker and `beforeunload` prompt when a form is dirty |
| 401 | Redirect to `/login?next=<current path>&reason=expired` |
| 412 `version_mismatch` | Dialog: "This was changed elsewhere. Reload to see the latest version." → Reload |
| 409 `document_not_draft` | Reload the document into its read-only details view, with a banner "This invoice has already been finalised." |
| Offline / network failure | Banner: "Can't reach HIVE DOCS. Check your connection or that the app is running." Retry buttons stay available |
| Money entry | Free text with decimal keyboard. Client-side Zod checks the 09 §4 patterns on blur; the server is authoritative |
| Updates | Pessimistic: the UI waits for the server before showing a change as saved. Calculations are never optimistic |

## 10. Landing page (`/`)

### 10.1 Layout and content

| Area | Content |
| --- | --- |
| Header | "HIVE DOCS" wordmark, a small "Demonstration build" badge, and an ENTER THE SYSTEM button on the right |
| Hero | Headline: "Correct invoices. Numbered once. Stored exactly as issued." Sub-headline: "Enter your business details once, add line items, and HIVE DOCS calculates every amount on the server, issues a unique invoice number and stores the exact PDF you sent." Primary button ENTER THE SYSTEM; secondary link "How it works" (scrolls to the workflow strip) |
| Animation panel | "The Ledger Assembles" (§10.2), beside the text from 1280 px, below it on smaller screens |
| Value points (3 cards) | **Totals you can trust:** calculated on the server with exact decimal arithmetic. **Numbered once, then locked:** each finalised invoice gets a unique number and can no longer be changed. **Retrievable as issued:** the issued PDF is stored privately, and every download is identical to the original |
| Workflow strip | Business → Customer → Invoice → Finalise → PDF → History (six labelled steps) |
| Footer | "Demonstration build · PDFs are specimens, not tax invoices · Built by Group 6 for HIVE Hub / Heloavy" |

Not allowed on the landing page: pricing, plans, testimonials, client logos, statistics, or any deferred feature (03 §8).

**Interactions:**

- ENTER THE SYSTEM navigates to `/app` when the cached session (`['me']`) is valid, otherwise to `/login`. `/login` itself redirects to `/app` when a session exists.
- **Loading:** none needed (static page). **Empty, error:** not applicable. If the optional session check fails, the button still goes to `/login`.

### 10.2 MUST animation (L-01): three beats, under 5 s, played once

| Time | Beat | Visual |
| --- | --- | --- |
| 0.0–0.6 s | Sheet | A white A4 card with faint ruled lines scales in from 98 % to 100 % and fades in. A small "SPECIMEN" tag sits in the corner throughout |
| 0.6–2.0 s | 1. Lines | Two rows slide in one after the other: "Brand identity consultation · 2.5 × ₹800.00 · −10% · ₹1,800.00" and "Website support hours · 3 × ₹333.33 · −₹99.99 · ₹900.00" |
| 2.0–3.0 s | 2. Totals | The totals block reveals "Subtotal ₹2,999.99 · Discount −₹299.99 · **Total ₹2,700.00**", with a highlight sweep under the total |
| 3.0–4.2 s | 3. Finalise | A stamp "FINALISED · INV/26-27/00001" presses onto the sheet (scale 1.15 → 1, opacity 0 → 1) with a lock icon; caption "Numbered once. Locked." |
| From 4.2 s | End frame | Static |

- **Implementation:** HTML and SVG with CSS keyframes. It starts when the panel enters the viewport and runs once.
- **Reduced motion:** the end frame is shown immediately.
- **Text alternative:** "An invoice is filled with two lines, the server calculates a total of ₹2,700.00, and it is finalised as INV/26-27/00001."

### 10.3 Full storyboard (S-04, stretch)

Adds three things to §10.2, still within 5 s in total:

1. Line text typing in.
2. A "Generating PDF…" indicator that turns into a PDF icon with "SHA-256 ✓".
3. The sheet sliding into a small "History" stack beside two earlier invoices.

## 11. Authentication screen (`/login`)

| Aspect | Specification |
| --- | --- |
| Layout | A centred card on `--paper` with the wordmark, `h1` "Sign in", Email, Password (with a show/hide toggle) and a "Sign in" button. Note: "This is a demonstration workspace. Accounts are created by the administrator." There is no sign-up link and no "forgot password" link (P1-01) |
| Components | TextField (`autocomplete="username"`), TextField (`type="password"`, `autocomplete="current-password"`), Button, Banner |
| Interactions | Enter submits. On success, go to `next` (only same-origin `/app…` paths are allowed), otherwise to `/app` |
| Loading | The button shows a spinner; the fields are disabled |
| Empty | Not applicable |
| Errors | `invalid_credentials` → "Email or password is incorrect." `rate_limited` → "Too many attempts. Try again in N minutes." (from `Retry-After`). Network → offline message. `reason=expired` → an information banner "Your session ended. Please sign in again." |
| Success | Redirect; no toast |

## 12. Application shell, routes and dashboard

### 12.1 Routes

| Route | Page | Access |
| --- | --- | --- |
| `/` | Landing | Public |
| `/login` | Sign in | Public; redirects to `/app` when signed in |
| `/app` | Dashboard | Signed in |
| `/app/business` | Business profile (create or edit) | Signed in |
| `/app/customers` | Customer list | Signed in; business required |
| `/app/customers/new` | New customer | Signed in; business required |
| `/app/customers/:customerId` | Edit customer | Signed in; business required |
| `/app/invoices` | Document history | Signed in; business required |
| `/app/invoices/new` | Choose a customer, then create a draft | Signed in; business required |
| `/app/invoices/:documentId` | Editor (draft) or details (finalised) | Signed in; business required |
| `/app/templates` | Template selection | Signed in |
| `*` | Not found (§22) | Public |

"Business required": without a business, these routes redirect to `/app/business` with the banner "Set up your business first."

### 12.2 Shell

- **Top bar:** wordmark (links to `/app`); navigation (Dashboard, Invoices, Customers, Templates, Business) with the current page highlighted (`aria-current="page"`); a user menu (display name, organization name, Sign out).
- **Below 768 px:** a menu button opens the Drawer with the same items.
- **Footer:** "Demonstration build — PDFs are specimens, not tax invoices."
- **Sign out:** calls E-04, clears the query cache and goes to `/login`.

### 12.3 Dashboard (`/app`)

| Aspect | Specification |
| --- | --- |
| Layout | PageHeader "Dashboard"; quick-action buttons; a "Recent invoices" panel |
| Components | Button, Table/CardList, StatusPill, MoneyText, EmptyState |
| Behaviour | No business → only a setup card: "Set up your business — your details appear on every invoice." with a "Set up business" button. With a business → New invoice, New customer, and the five most recent invoices (E-16 `limit=5`: number or "Draft", customer, issue date, total, status) with a "View all invoices" link. Rows open the document |
| Loading | Skeleton rows |
| Empty | "No invoices yet. Create your first invoice." with a New invoice button |
| Errors | ErrorState with Retry |
| Success | Not applicable |
| Never shown | Charts, revenue figures, analytics |

## 13. Business profile (`/app/business`)

| Aspect | Specification |
| --- | --- |
| Layout | PageHeader "Business profile". Sections: **Business details** (legal name (required), trade name); **Address** (line 1 (required), line 2, city (required), state (required, a select showing names from 09 §4.4), PIN code (required)); **Contact** (phone, email); **Tax identifier (optional)** (GSTIN, help text: "Optional. Printed on your documents if provided. This demonstration does not calculate GST.") |
| Banner (edit mode) | "Issued invoices keep the details they were issued with." |
| Interactions | Create mode (no business) → POST E-06. Edit mode → PATCH E-08 with `If-Match`. Save is disabled until the form changes |
| Loading | Form skeleton; Save spinner |
| Empty | Create mode is the empty state, with the intro "Your business details appear on every invoice." |
| Errors | Inline field errors (PIN code, state, GSTIN pattern, `state_mismatch`); 412 conflict dialog; 409 `business_already_exists` → reload in edit mode |
| Success | Toast "Business profile saved." In create mode, go on to the dashboard |

## 14. Customers

### 14.1 Customer list (`/app/customers`)

| Aspect | Specification |
| --- | --- |
| Layout | PageHeader "Customers" + "New customer"; a search field ("Search by name", prefix match, debounced 300 ms); a table (Name, Contact, Email, City, Added) at 768 px and above, cards below; a "Load more" button for the next page |
| Interactions | A row opens the edit page; the search updates the URL (`?q=`) |
| Loading | Skeleton rows; "Load more" shows a spinner |
| Empty | "No customers yet. Add your first customer to start invoicing." + New customer. Empty search: "No customers start with “{q}”." + Clear search |
| Errors | ErrorState with Retry |
| Success | Not applicable |

### 14.2 Create and edit customer (`/app/customers/new`, `/app/customers/:customerId`)

| Aspect | Specification |
| --- | --- |
| Layout | Display name (required), contact name, email, phone; address (line 1, line 2, city, state, PIN code); GSTIN (optional; must match the state when both are given) |
| Banner (edit) | "Changes apply to drafts and new invoices. Issued invoices keep the details they were issued with." |
| Interactions | Save → E-10 or E-12 (`If-Match`); Cancel → back to the list (with the unsaved-changes guard) |
| Quick create | From the invoice editor, a Dialog with display name (required), email and city → E-10 → the new customer is selected in the draft |
| Loading | Skeleton (edit); Save spinner |
| Empty | Not applicable |
| Errors | Inline field errors; 404 → "This customer doesn't exist or you don't have access."; 412 conflict dialog |
| Success | Toast "Customer saved." → back to the list, or to the editor for quick create |

## 15. Invoice editor (draft) — `/app/invoices/new`, `/app/invoices/:documentId`

### 15.1 New invoice

`/app/invoices/new` shows "Choose a customer": a CustomerPicker plus a "New customer" quick create. Selecting a customer calls E-15 (`customer_id`, default template) and replaces the route with `/app/invoices/:id`. Empty customers → "Add a customer first" with the quick create.

### 15.2 Editor layout

| Region | Content |
| --- | --- |
| Header | Breadcrumb "Invoices / Draft"; StatusPill "Draft"; save indicator ("All changes saved", "Unsaved changes", "Saving…") |
| Details | Customer (CustomerPicker; can be changed in a draft), Reference, Due date, Template (Select; in P0-Lite the only option is "Classic · Free", with the helper "Classic is the template available in this build.") |
| Lines | Columns: # · Description · Qty · Unit · Unit price (₹) · Discount (Select None / % / ₹ + value) · Amount (from the server) · remove. "Add line" button (disabled at 200 lines with the note "Maximum 200 lines") |
| Notes and terms | TextAreas with counters (2,000 characters) |
| Summary card (sticky from 1280 px; at the end on smaller screens, plus a sticky bottom bar with Total and Finalise) | Subtotal, Discount (−), **Total**; buttons **Save draft** · **Preview PDF** · **Finalise** · Delete draft (danger ghost) |

### 15.3 Interactions

- **Live totals:** any change to quantity, price or discount posts the current lines to E-14, debounced 400 ms. While waiting, "Calculating…" appears in the summary and amounts are dimmed. A 422 shows the field messages and "—" in the affected Amount cells and totals.
- **Save draft:** PATCH E-18 with the full lines and `If-Match`. It is disabled when nothing has changed.
- **Preview PDF:** saves first if there are unsaved changes, then opens the preview (§17). It is disabled when there are no lines.
- **Finalise:** enabled when the draft is saved, has at least one line and a total above ₹0.00. It opens an AlertDialog:
  - Title: "Finalise invoice?"
  - Body: "This assigns the next invoice number and today's date (India time). After finalising, the invoice can't be edited or deleted. The PDF is marked SPECIMEN — not a tax invoice."
  - It shows the customer and the total. Buttons: Cancel / **Finalise invoice**.
- **On confirm:**
  1. Generate one idempotency key for this attempt and call E-21.
  2. 422 `finalization_blocked` → list the reasons inside the dialog.
  3. 409 `idempotency_in_progress` or a network failure → retry automatically with **the same key**, after 2 s, up to 3 times. Show "Confirming…".
  4. 412 → conflict dialog.
  5. Success → the route re-renders as the details view (§19), with the toast "Invoice INV/26-27/00001 finalised."
- **Delete draft:** AlertDialog "Delete this draft? This can't be undone." → E-19 → back to the history, with the toast "Draft deleted."

### 15.4 States

| State | Behaviour |
| --- | --- |
| Loading | Skeleton of the form |
| Empty (new draft with no lines) | The lines area says "Add your first line item." with Add line; totals show ₹0.00 |
| Errors | Save failure → a banner with the request ID; 404 → "This invoice doesn't exist or you don't have access."; 409 `document_not_draft` → details view with a banner |
| Success | Save indicator plus the polite announcement "Saved" |

## 16. Template selection (`/app/templates` and the editor's Template field)

| Aspect | Specification |
| --- | --- |
| Layout | PageHeader "Templates". A card per active template from E-13: a CSS-drawn miniature of the layout (header block, table rows, totals; not an image), the name "Classic", a "Free" badge, and the description |
| Behaviour | Informational in P0-Lite: Classic is the default for new drafts. In the editor, the Template select lists the same templates. With S-01, a second card and option appear, and choosing one in the editor saves `template_id` through E-18 |
| Loading | Skeleton cards |
| Empty | Treated as an error: "No templates are available." with the request ID |
| Errors | ErrorState with Retry |
| Success | Not applicable |
| Never shown | Premium, locked or "coming soon" templates |

## 17. PDF preview

| Aspect | Specification |
| --- | --- |
| Trigger | "Preview PDF" in the editor |
| Behaviour | The SPA fetches E-20 as a blob. That keeps errors inside the app and avoids popup blockers. From 768 px it shows a large Dialog with an `<iframe title="Draft preview PDF">` of the blob URL and a "Download preview" button. Below 768 px it offers "Open preview" (download or open with the device viewer). The blob URL is revoked when the dialog closes |
| Content | The Classic layout with a diagonal "DRAFT — NOT ISSUED" watermark, "Not yet issued" in place of the number, "Assigned when finalised" for the date, and the SPECIMEN footer (09 §13) |
| Loading | The button shows a spinner ("Generating preview…") |
| Errors | `no_lines` → "Add at least one line to preview."; 429 → "Please wait a moment before previewing again."; 503 → "The PDF service is busy. Try again." |
| Success | The dialog opens |

## 18. Document history (`/app/invoices`)

| Aspect | Specification |
| --- | --- |
| Layout | PageHeader "Invoices" + "New invoice". A segmented filter All / Drafts / Finalised (`status`) and a search field ("Search by number or customer", prefix). Table columns: Number (or "Draft"), Customer, Issue date, Total (finalised only; "—" for drafts), Status, PDF (Ready / Pending / Failed / —). Cards below 768 px. "Load more" for pagination |
| Interactions | Row → `/app/invoices/:id`. Filter and search update the URL (`?status=&q=`) |
| Loading | Skeleton rows |
| Empty | "No invoices yet." + New invoice. With filters: "No invoices match these filters." + Clear filters |
| Errors | ErrorState with Retry |
| Success | Not applicable |

## 19. Document details (finalised) — `/app/invoices/:documentId`

| Aspect | Specification |
| --- | --- |
| Header | The number in display type, the "Finalised" pill, a lock icon with "Finalised invoices can't be edited.", issue date, due date, customer (as issued), reference |
| Actions | **Download PDF** (primary; enabled when the PDF is ready). **Retry PDF** (shown when `pdf.retry_available`). Back to invoices |
| PDF status panel | Pending → "Generating PDF…" with a spinner; polls E-17 every 1.5 s for up to 60 s. Ready → "PDF ready", with the size and the shortened SHA-256 (a copy button copies the full hash). Failed → "PDF generation failed" plus a reason (`storage_error` → "storage unavailable"; `render_timeout` → "took too long"; `render_error` or `snapshot_integrity` → "internal error") and Retry. Pending for more than 120 s → "This is taking longer than expected." and Retry |
| Body | Read-only seller and buyer blocks and the lines table, all from the snapshot; totals; notes; terms |
| Integrity section (collapsible) | Snapshot SHA-256 and PDF SHA-256, with: "These fingerprints show that the invoice and its PDF have not changed since they were issued." |
| Banner | "Specimen — demonstration document, not a tax invoice." |
| Download | Fetch E-22 as a blob, then save it with an anchor `download="INV-26-27-00001.pdf"`. Errors stay in the app |
| Loading | Skeleton |
| Errors | `pdf_not_ready` → refresh the status; `integrity_check_failed` → "This PDF failed its integrity check and was not downloaded. Reference: {request_id}"; 404 → not-found state |
| Success | Toast "PDF downloaded."; polite announcement "PDF ready" when the status changes |

## 20. PDF template "Classic" (`classic@1`)

| Element | Specification |
| --- | --- |
| Page | A4 portrait; margins 18 mm top, 16 mm left and right, 22 mm bottom |
| Fonts | Noto Sans (Regular and Bold) for the body at 9.5 pt; Noto Sans Devanagari as fallback in the font stack; `font-feature-settings: "tnum"` for amounts; only the bundled `@font-face` files are loaded through the restricted fetcher |
| Header, left | Seller legal name (13 pt bold), trade name, address lines, phone, email, "GSTIN: …" only if provided |
| Header, right | Title "Invoice" (18 pt bold); a meta table: Invoice no., Invoice date, Due date, Reference (rows omitted when empty) |
| Accent | A 1.5 pt rule in `#1F7A5A` under the header |
| Bill to | Buyer display name (bold), contact name, address, email, phone, "GSTIN: …" if provided |
| Lines table | # · Description · Qty · Unit · Unit price · Discount · Amount. The header repeats on each page (`thead` as a table-header-group); rows do not break across pages; numbers are right-aligned; borders in `#D9D4C7` |
| Totals | Right-aligned: Subtotal, Discount, **Total** (11 pt bold). Amount in words below only with S-05 |
| Notes and terms | Headed sections, shown only when present |
| Running footer (every page) | Left: the exact SPECIMEN text (8 pt, `#5B6472`). Right: "Page X of Y" (`counter(page)` / `counter(pages)`) |
| Preview only | Diagonal "DRAFT — NOT ISSUED" (64 pt, `#E0DCD2`, rotated −35°, a fixed-position element repeated on every page behind the content); number "Not yet issued"; date "Assigned when finalised" |
| Never | Images, logos (P1-03), external URLs, scripts, user-supplied HTML or CSS, the words in 09 §13's forbidden list |

## 21. Error copy catalogue

| `code` | Message shown |
| --- | --- |
| `invalid_credentials` | Email or password is incorrect. |
| `rate_limited` | Too many attempts. Try again in {minutes} minute(s). (Calculations, previews: "Please wait a moment and try again.") |
| `unauthenticated` | Your session ended. Please sign in again. |
| `csrf_failed` | Your session needs refreshing. Please try again. |
| `not_found` | This item doesn't exist or you don't have access to it. |
| `business_already_exists` | Your business is already set up. Opening your profile. |
| `version_mismatch` | This was changed elsewhere. Reload to see the latest version. |
| `document_not_draft` | This invoice has already been finalised and can't be changed. |
| `document_not_finalized` | Finalise this invoice before downloading its PDF. |
| `pdf_not_ready` | The PDF isn't ready yet. |
| `pdf_render_in_progress` | The PDF is still being generated. |
| `number_series_exhausted` | No more invoice numbers are available for this financial year. Contact support. |
| `idempotency_in_progress` | Still confirming your previous request… |
| `finalization_blocked` | This invoice can't be finalised yet: {reasons}. Reasons: `no_lines` → "add at least one line"; `zero_total` → "the total must be more than ₹0.00"; `total_too_large` → "the total is above the allowed maximum"; `due_date_before_issue_date` → "the due date is before today"; `inactive` → "the selected template is no longer available" |
| `validation_failed` | Please correct the highlighted fields. |
| `payload_too_large` | This request is too large. Remove some lines or text. |
| `integrity_check_failed` | This PDF failed its integrity check and was not downloaded. Reference: {request_id}. |
| `dependency_unavailable` | The service is temporarily unavailable. Try again shortly. |
| `internal_error`, `malformed_request`, `method_not_allowed`, `idempotency_key_missing`, `idempotency_key_mismatch`, `precondition_required`, `forbidden_role` | Something went wrong. Reference: {request_id}. |

## 22. Not-found page and session expiry

- **404 page:** `h1` "Page not found"; "The page you're looking for doesn't exist." Links: Dashboard (when signed in) or Home.
- **Session expiry:** any 401 clears the cached session and redirects to `/login?next=…&reason=expired`. After sign-in, the user returns to `next`.
