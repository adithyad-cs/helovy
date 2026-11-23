# CLAUDE.md — HIVE DOCS (PS5)

This repository builds HIVE DOCS, the PS5 business document and billing platform for HIVE Hub / Heloavy.

## Before any task

1. Read `docs/15_CLAUDE_CODE_INSTRUCTIONS.md`. Its rules are binding.
2. Read `docs/00_START_HERE.md`, then every other file in `docs/`, before writing code in a new session.
3. Read `PROGRESS.md` (once it exists) to see which milestone is current.

## Non-negotiables (full list in docs/15)

- Build only the P0-Lite scope in `docs/03_SCOPE_AND_FEATURES.md`, one milestone at a time from `docs/10_IMPLEMENTATION_PLAN.md`.
- Keep the approved stack and the modular monolith. No new dependency, service or architectural change without asking.
- The server recalculates every amount with `Decimal`; money travels as decimal strings; floats are never authoritative.
- Organization identity comes from the session, never from the request body. Cross-tenant access returns 404.
- Finalised documents, snapshots, ready PDFs and audit events are immutable.
- Every PDF carries "SPECIMEN — demonstration document, not a tax invoice." No GST calculation and no compliance claims.
- Never present unfinished or mocked functionality as complete.
- If two documents disagree, or a needed decision is not documented, stop and ask the developer. Never choose silently.
- Workflow: Inspect → Plan → Implement → Test → Review → Report → next milestone.
