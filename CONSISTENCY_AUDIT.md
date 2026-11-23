# Cross-Document Consistency Audit

**Package:** HIVE DOCS (PS5) documentation 1.1 · **Date:** 23 November 2026 · **Re-run** after the version 1.1 corrections
**Checked against:**

- the official PS5 requirements (as restated in the master documentation prompt);
- Revision 2 with the Revision 2.1 errata;
- the accepted recommendations of the independently reviewed Perplexity, Grok and Gemini research reports, as consolidated in those decisions;
- the constraints of the master documentation prompt.

## 1. Result

The package is internally consistent: **no contradiction remains between the 16 documents.**

| Upstream contradiction | Status |
| --- | --- |
| C-04, C-07, C-08, C-09 | **Open**; they need Heloavy's decision (§4) |
| C-01 (MinIO versus SeaweedFS) | **Resolved**: SeaweedFS retained, subject to the M0 verification gate |
| C-02 | **Withdrawn**: it rested on an incorrect provenance statement |

**Research provenance:** the Perplexity, Grok and Gemini research reports were independently reviewed, their relevant recommendations were audited, and the accepted decisions are consolidated in this package. The original full reports are not bundled in the ZIP. This audit therefore checks consistency against the accepted decisions, not against the original reports.

## 2. Automated checks (re-run on version 1.1; all passing)

| Check | Result |
| --- | --- |
| All 16 documents in `docs/`, plus README.md, CLAUDE.md, PROJECT_SUMMARY.md and this file | Present; no stray files |
| Cross-references of the form "NN §X.Y" between documents, and "§X" within one (including the new 05 §14.1 and 14 §7) | Every referenced section exists |
| API: 23 endpoints in the 07 index, each with a detail section; every `/api/v1/...` path cited matches the index | Pass |
| Schema: 15 tables; every index and constraint names columns defined for its table; composite foreign-key targets exist; 5 triggers, referenced consistently | Pass |
| Identifiers defined and referenced within range: L-01–16, S-01–05, P1-01–16, P2-01–07, FR-01–39, NFR-01–14, BR-01–18, US-01–12, Q-01–26 (25 defined; Q-24 withdrawn), A-01–20, C-01–12 (11 defined; C-02 withdrawn), DC-01–20, AT-01–15, V-01–19, RK-01–11 (RK-12 withdrawn), ADR-01–13, F-01–16, M0–M8, CP1–CP5, R1–R6 | Pass |
| Withdrawn identifiers Q-24, C-02 and RK-12 appear only in withdrawal notes (14 §1, 01, README version history, this file) | Pass |
| Every test ID cited in any document is defined in 11 | Pass |
| Error codes: every status and code pair cited is in the 07 catalogue (24 codes); every code has UI copy in 08 §21; field codes are listed in 07 §1.5 | Pass |
| Audit events (12 types) and environment variables (05 §9) used consistently | Pass |
| The SPECIMEN statement appears only in its exact form | Pass |
| **Retention wording:** no "kept permanently", "forever" (except the "do not say" example in 13), "any time later", "for good", "always retrievable" or "can never change". The immutability-while-retained statement is present in 01, 02, 09, 12, 13 and PROJECT_SUMMARY | Pass |
| **Schedule labelling:** the 16.5–22 h estimate is labelled "aggressive and conditional" in 00, 01, 02, 03, 10, 13, README and PROJECT_SUMMARY; 10 states explicitly that completion is not guaranteed; no wording promises completion within 19 h; milestone estimates still sum to 16.5–22 h | Pass |
| **Provenance:** README, PROJECT_SUMMARY, 01, 14 and this file state that Perplexity, Grok and Gemini were independently reviewed and that the original reports are not bundled; no "never provided" or "not used" wording remains | Pass |
| **SeaweedFS gate:** 01, 02, 04, 05, 10, 14 and 15 reference the M0 verification gate (05 §14.1); V-18 and V-19 are defined and cited in M0 | Pass |
| Restricted terms (MinIO, "Tax Invoice", `gst_demo`, `gst_approved`, `csrf_token_hash`) appear only in their proper contexts | Pass |
| Markdown tables have consistent column counts; code fences are balanced; Mermaid labels have balanced quotes and brackets | Pass |

The script that ran these checks is a review tool. It is not part of the package, which contains no source code.

## 3. Version 1.1 changes (exact list)

All 16 documents moved from version 1.0 to 1.1 in their headers. In addition:

| File | Changes |
| --- | --- |
| README.md | Status: version 1.1 is the approved working baseline. Demonstration heading now reads "planned to cover". The P0-Lite estimate is labelled aggressive and conditional with no completion guarantee, and a new bullet says the quality floor is never weakened. Source-of-truth item 3 now records the independent review of the Perplexity, Grok and Gemini reports and that the originals are not bundled (the Q-24 reference is removed). A "Version history" section was added |
| PROJECT_SUMMARY.md | "Kept permanently" replaced: the issued PDF stays unchanged while retained, and retention follows Heloavy's policy and the law. Status rows: research reviews (Perplexity, Grok, Gemini; not bundled); version 1.1; capacity labelled aggressive and conditional. Demonstration section now "aims to show", and only stages that pass their checks are shown. New limit: the retention period is undefined. Storage row: SeaweedFS retained behind M0 verification. Guarantee 3 is limited to the retention period. "When behind" lists the explicit checkpoint reductions and the quality floor. The Grok and Gemini deviation bullet is removed and the MinIO bullet updated. New "Research provenance" section |
| docs/00_START_HERE.md | §1: the PDF is stored unchanged while retained. §4: P0-Lite is a target (aggressive, conditional; 10 §1) with no completion guarantee. §5: only stages that pass their checks are shown live. §11: version 1.1 approved |
| docs/01_PROJECT_CHARTER.md | §2: new research provenance paragraph. §4: the vision says "unchanged for as long as it is retained"; a new paragraph separates immutability from retention; the "Issued means frozen" principle is limited to the retention period. §10: the estimate is aggressive and conditional with no completion guarantee; the quality floor is reworded. RK-01 is reworded. RK-03 mitigation is now the SeaweedFS M0 gate. **RK-12 removed** (withdrawal note) |
| docs/02_PRD.md | BR-10: immutable while retained; retention and deletion per policy and law. §9: P0-Lite is an aggressive, conditional target, and the never-cut reference is corrected from 11 §2 to 11 §1 (a version 1.0 reference error). §10: the storage dependency is now the M0 gate (V-07, V-08, V-18, V-19) |
| docs/03_SCOPE_AND_FEATURES.md | Header rule: an aggressive, conditional target. §1: MUST COMPLETE is not a completion guarantee. L-11: purpose and benefit wording limited to the retention period |
| docs/04_ARCHITECTURE.md | §13: the Local row requires the M0 gate; new Retention row. ADR-13: retained by team decision, subject to the M0 gate |
| docs/05_TECH_STACK_AND_SETUP.md | §1 and §7.2 storage rows reference the gate. §8: `init-dev-storage` is safe to re-run (V-18). §14: V-07 and V-08 reworded as gate items; **new V-18** (bucket initialization) and **V-19** (authenticated PUT/GET); **new §14.1** "SeaweedFS verification gate (M0 exit criterion)" with stop-and-ask on failure |
| docs/06_DATABASE_SCHEMA.md | §10: finalised records are immutable while retained; retention-based deletion is not part of P0-Lite |
| docs/07_API_SPEC.md | Version only |
| docs/08_UI_UX_SPEC.md | §10.1 landing copy: "Stored exactly as issued"; value points "Numbered once, then locked" and "Retrievable as issued" |
| docs/09_FINANCIAL_AND_DOCUMENT_RULES.md | §9: new "Retention and deletion" row |
| docs/10_IMPLEMENTATION_PLAN.md | §1: "the target is P0-Lite"; a new bullet says the estimate is aggressive and conditional and that completion is not guaranteed; the quality floor names calculation correctness, tenant isolation, finalisation integrity and data and PDF persistence. §2: estimate labelled; completion is a target, not a commitment. §3: statuses are targets; M0.4 spike B is the SeaweedFS gate; the M0 exit requires the gate, with stop-and-ask on failure. §5: the meaning of MUST COMPLETE. §6: new "How checkpoint decisions work" (five rules); "Never cut" is renamed "Never weakened" |
| docs/11_QA_AND_ACCEPTANCE.md | §7 step 1: the presenter line now says "stores the exact PDF it issued" |
| docs/12_SECURITY_AND_PRIVACY.md | §16: a new opening paragraph separates immutability from retention; retention-based deletion is deferred to an audited administrative process |
| docs/13_TEAM_HANDOFF.md | §3: "locks it forever" and "any time later" replaced. §4: a planned-demonstration note. §7: "cannot be changed while retained". §11: the estimate is aggressive and conditional, and the quality floor is never weakened. §12: a new "Say / Do not say" row and a new FAQ on retention |
| docs/14_OPEN_QUESTIONS_AND_ASSUMPTIONS.md | §1: withdrawal note. **Q-24 removed.** Q-25 marked answered (SeaweedFS retained, M0 gate). A-16 updated. C-01 resolved. **C-02 removed.** §5: C-01 dropped from the deviations needing acceptance. §6: decision #2 accepted; new decisions #5–#8. **New §7** "Research provenance and source packaging" |
| docs/15_CLAUDE_CODE_INSTRUCTIONS.md | §6: the M0 row requires the SeaweedFS verification gate |
| CLAUDE.md | Unchanged |
| CONSISTENCY_AUDIT.md | Rewritten for version 1.1 |

No architecture, technology, schema, API, endpoint or feature was added or changed.

## 4. Unresolved upstream contradictions (need a decision)

| ID | Contradiction | Current handling | Decision needed from |
| --- | --- | --- | --- |
| C-04 | Subscriptions, usage limits and premium templates (official requirements) are not in the demonstration | Deferred to P1-04, not removed; stated openly | Heloavy (Q-08, Q-12) |
| C-07 | Cloud deployment moved from the demonstration path (Revision 2.1) to stretch (S-02) | The local Docker runtime is the guaranteed path | Heloavy (Q-14) |
| C-08 | Salary slips (an official requirement) are scheduled for P2 | Kept in the specification with privacy controls | Heloavy (Q-06, Q-22) |
| C-09 | The title says "Point of Sale", but the scope excludes retail checkout | Billing documents first; P1-16 only with written confirmation | Heloavy (Q-01) |

**Resolved:** C-01, by team decision on 23 November 2026: SeaweedFS retained, subject to the M0 verification gate.

**Resolved but deliberately flagged:**

- C-03: Revision 2 P0 versus P0-Lite;
- C-05: Revision 2.1's reserved columns removed;
- C-06: managed PostgreSQL versus the local demonstration database;
- C-10: development tooling;
- C-11: extra environment variables;
- C-12: where the template hash lives.

**Withdrawn:** C-02. See `docs/14` §1, §4 and §7.

## 5. Not verifiable in this environment

- **Mermaid diagrams** were checked for syntax hazards only; they were not rendered, because no renderer was available offline.
- **Versions and commands** marked "(verify)" in 05 are unverified by design (V-01 to V-19). SeaweedFS must pass the M0 gate (05 §14.1) before M0 exits.
- **Regulatory statements** (GST rules, the e-invoicing threshold, retention periods, DPDP dates) are marked for CA or legal verification. None is implemented in P0-Lite.
- **Colour contrast ratios** in 08 §4 were computed by hand and must be confirmed with a contrast checker in M7.
