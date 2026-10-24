# PRAMAAN–AICTE Project Audit

**Date:** 24 October 2026
**Status:** Audit complete. Implementation plan finalized and approved. No application code has been written.

## 1. Executive summary

PRAMAAN–AICTE is currently a documentation-blueprint project: the repository contains project documentation, research material, and plans, but **no application source code**.

The documentation set reviewed in this audit is unusually disciplined for a student project. It consistently separates:

- verified facts / authoritative sources,
- proposed design decisions,
- simulated behavior (`MOCK`/`DEMO`),
- prototype thresholds and targets,
- legal/regulatory claims pending external verification.

Core safety principles are well documented: candidate-not-verdict matching, institution-side plaintext identity boundary, versioned policies, deterministic reconciliation, purpose-limited verification, audit events.

**Key findings:**

1. The master Word report (`docs/PRAMAAN_AICTE_Complete_Master_Report_Final.docx`) is a three-part document (Research / Redesigned Architecture / Implementation Specification) prepared 24 October 2026, with an explicit change log correcting prior technical/factual positions.
2. Several documents are stale or internally inconsistent (CONTENTS.txt; API contracts; adapter states; thresholds; batch lifecycle; legal interpretation).
3. External verification gates V-01…V-12 remain open; no web research was performed during the initial inspection.
4. The repository cannot yet execute acceptance criteria because no source code exists.

The user-approved audit direction (2026-10-24) resolves the most consequential internal contradictions directionally and is recorded in §16.

## 2. Complete document inventory

| # | Document | Path | Purpose | Reviewed | Issues |
|---|---|---|---|---|---|
| 1 | README | `README.md` | Blueprint status, goals, tiers, docs index | Yes | Consistent with docs-only state |
| 2 | Agent instructions | `AGENTS.md` | Agent directives | Yes | None material |
| 3 | Contents | `CONTENTS.txt` | Inventory | Yes | **Stale line counts; missing frontend-design-system.md and Word report** |
| 4 | PRD | `docs/PRD.md` | Product requirements | Yes | None material |
| 5 | Architecture | `docs/architecture.md` | Components, boundaries, lifecycles | Yes | Threshold wording superseded by report correction |
| 6 | Data model | `docs/data-model.md` | Logical entities | Yes | Naming drift vs. report |
| 7 | API contracts | `docs/api-contracts.md` | Internal API examples | Yes | **Path/set drift vs. report Part III** |
| 8 | Security baseline | `docs/security-privacy.md` | Threats/controls | Yes | Release checklist unchecked |
| 9 | Testing | `docs/testing.md` | Tests/evaluation | Yes | **T vs. TS numbering drift; benchmark honesty** |
| 10 | Research register | `docs/research-and-verification.md` | V-01…V-12 | Yes | Current-status note |
| 11 | Frontend design system | `docs/frontend-design-system.md` | UI rules | Yes | **Missing from CONTENTS.txt** |
| 12 | Glossary | `docs/GLOSSARY.md` | Terminology | Yes | None material |
| 13 | TODO | `docs/TODO.md` | Roadmap | Yes | Phase/task alignment pending |
| 14 | ADRs | `docs/adr/0001`–`0004` | Architecture decisions | Yes | Statuses: Proposed / Accepted |
| 15 | Master report | `docs/PRAMAAN_AICTE_Complete_Master_Report_Final.docx` | Research + redesign + implementation spec | Yes (OOXML text extraction) | **Table-extraction limits; open `[VERIFY]` gates** |

## 3. Confirmed project requirements

From the reviewed documentation:

- **PRD:** FR-01…FR-16 (authorization, batch intake, validation, snapshots, reconciliation, linkage, adjudication, verification, audit, adapters, operations, reporting, public-sector UI, accessibility, honest states, density), non-functional requirements, frontend acceptance criteria, prototype success criteria.
- **Architecture:** modular monolith; components; trust boundaries; identity constraints; policy lifecycle; batch lifecycle; adapter states; constraints.
- **Data model:** logical entities and invariants.
- **Security:** assets, threats, required controls, PPRL-specific risks, legal-review boundary, release checklist.
- **Testing:** T-01…T-16; identity evaluation; metrics; benchmark record.
- **Research:** source hierarchy, V-01…V-12, claim discipline, research log template.
- **Frontend design system:** design objective, visual principles, branding, shell, page patterns, status language, interaction/accessibility requirements, data safety, component list, prohibited shortcuts, UI review checklist.

## 4. Word report summary and relationship to existing documentation

The Word report is `docs/PRAMAAN_AICTE_Complete_Master_Report_Final.docx` (approx. 141 KB). It contains:

- **Part I — Corrected source research:** executive summary, official problem statement, ecosystem analysis, gap analysis, innovation candidates, scoring, architecture, database/API contracts, validation rules, security/privacy assessment, prototype plan, synthetic data, demo plan, risks, verification decisions, ERD.
- **Part II — Redesigned architecture & ERP summary:** executive decision, goals/non-goals, logical architecture, data flow, PPRL redesign, domain model, intake compiler, adjudication, DPDP, security/audit, API design, implementation backlog, sprint order, UI/screen inventory, governance/retention, demo plan, ADR register, verification register, final assessment.
- **Part III — Implementation-ready technical specification:** requirements traceability, workflows/sequences, logical API contracts, data dictionary, threat model, security design rules, deployment, performance, backlog, sprint order, UI inventory, governance, demo plan, ADR register, consolidated `[VERIFY]` register, release gates, final assessment.

**Change-log corrections** (authoritative within the report): A1–A7, B1–B6, C1–C5, D1–D2, E1–E6 — including corrections to demo-script arithmetic, API response totals, DPDP notification date, DigiLocker sample URI, SIH statement range, similarity thresholds, legal-notice handling, PPRL data-flow contradiction, mobile HMAC approach, implementation-plan scope, benchmark claims, SIH provenance, and bibliography quality.

The report is treated as an important research input and proposal source, **not** unquestionable authority; corrections are leading proposals pending reconciliation with the Markdown documentation.

## 5. Conflicts, contradictions, omissions, and ambiguities

| # | Conflict | Affected files | Severity | Practical impact | Resolution proposal | Approval / verification need |
|---|---|---|---|---|---|---|
| 1 | API contract drift | `docs/api-contracts.md` vs. report Part III / §20 | High | Two different endpoint shapes/sets could drive divergent implementation | Adopt report Part III as leading proposal; reconcile endpoint-by-endpoint; publish one canonical contract | User decision 3 approved |
| 2 | Adapter state vocabulary | `docs/PRD.md`, `docs/architecture.md`, report §10.1/§29 vs. report §14 | High | `MOCK`/`SANDBOX_TESTED` vs. `MOCKED`/`TESTED` confusion risks mislabelling | Standardize on `MOCK`, `CONFIGURED`, `SANDBOX_TESTED`, `PRODUCTION_VERIFIED`, `DISABLED` | User decision 2 approved |
| 3 | Similarity bands | report change-log A7 / §4.3 vs. `docs/architecture.md` | High | Threshold semantics unclear; risk of mis-band classification | Keep `<0.78`, `[0.78, 0.92)`, `≥0.92` as experimental; human review; no automatic consequence | User decision 1 approved |
| 4 | Tier taxonomy | `README.md`, `docs/PRD.md`, `docs/TODO.md` vs. report §14 tiers | Medium | Confusing scope boundaries | Keep Tier 1 / 1.5 / 2 canonical; crosswalk report Core/Extended/Future | User decision 6 approved |
| 5 | Batch lifecycle | `docs/architecture.md` vs. report workflow steps | Medium | State naming/granularity drift | One canonical state machine; workflow steps separate | User decision 7 approved |
| 6 | Legal/privacy interpretation | report change-log B1–B6 vs. markdown | High | Consent/notice/legal-basis interpretation risk | Provisional design guidance; keep `[VERIFY]` | User decision 4 approved |
| 7 | Benchmark labels | report change-log C5 vs. `docs/testing.md` | Medium | Measured vs. target claims | Keep precision/FAR/latency as synthetic-data targets | Medium |
| 8 | Inventory staleness | `CONTENTS.txt` | Low | Wrong/missing entries | Correct inventory | Low |
| 9 | DPDP notification date | report change-log A3 vs. research register | Medium | Date accuracy | Treat as `[VERIFY]` pending primary source | Medium |

## 6. Technical feasibility assessment

- Recommended prototype stack (from report and ADR-0001): modular monolith; FastAPI / Pydantic v2; PostgreSQL 16; React 18 + TypeScript + Vite + Tailwind; TanStack virtualized tables; Web Worker CSV parsing; RapidFuzz; scikit-learn; jwcrypto Ed25519; W3C SD-JWT (later).
- Feasible for a student team to demonstrate Tier 1 end-to-end on synthetic data; PPRL + SD-JWT scope is ambitious but bounded.
- 36-hour sprint figure is a stretch target, not a commitment (report change-log C4).

## 7. Security and privacy risks

- Documentation-level findings reviewed against security-review expectations.
- Required controls documented; release checklist currently unchecked.
- Not a security audit or legal compliance certification.

## 8. Algorithmic and research concerns

- Two-stage matching design; composite Bloom filter; secondary split encoding; Jaro–Winkler on blocked candidate pairs; similarity bands.
- Thresholds experimental; no automatic verify/merge/consequence from score.

## 9. Unverified external claims and required evidence

- V-01…V-12 open; `[VERIFY]` items; no web research performed in initial inspection.

## 10. Frontend and accessibility findings

- Design system mandatory and detailed; no code yet; UI review checklist defined.

## 11. Prioritized recommendations

- Critical: SIH verification gate; privacy-design contradiction corrected in report must be codified; doc contradictions before implementation.
- High: thresholds; adapter taxonomy; API canonicalization; legal interpretation; security release checklist.
- Medium: benchmark honesty; tier/lifecycle unification; CONTENTS freshness.
- Low: polish.

## 12. Proposed final source of truth for requirements and architecture

- Word report Part II (redesigned architecture) as engineering proposal source for prototype; Markdown docs as living project docs; PRD as product requirements; ADRs as decisions; research register as verification tracker.

## 13. Decisions requiring team approval

- Legal/regulatory posture; live integration; credential issuance; PPRL production; retention/deletion; penalties/enforcement automation.

## 14. Issues that must be resolved before implementation

- Internal contradictions; verification gates; security release checklist; legal interpretation.

## 15. Issues that can safely be deferred

- Live adapters; SD-JWT issuance; Isolation Forest; advanced PPRL hardening; scale/performance hardening.

## 16. Decisions recorded from the approved audit direction (2026-10-24)

1. Similarity thresholds `<0.78`, `[0.78, 0.92)`, `≥0.92` kept as experimental prototype parameters; no automatic identity verification/merge/consequential decision from score alone; future auto-matching requires separate validation/approval.
2. Adapter states standardized on `MOCK`, `CONFIGURED`, `SANDBOX_TESTED`, `PRODUCTION_VERIFIED`, `DISABLED`; configured ≠ tested; mock ≠ live.
3. API contracts: report Part III leading proposal; reconcile with `docs/api-contracts.md`; one canonical contract; no invented external specs.
4. Legal/privacy: report corrections provisional design guidance, not legal certification; keep `[VERIFY]`.
5. MVP scope: demonstrable MVP with synthetic data + labelled mocks; defer Isolation Forest, production integrations, SD-JWT issuance unless essential; modular for later addition.
6. Tier taxonomy: Tier 1 / 1.5 / 2 canonical; map report Core/Extended/Future via crosswalk; flag ambiguity.
7. Batch lifecycle: one canonical state machine; report 11 workflow steps separate from persistent states.
8. Verification: maintain V-01…V-12; distinguish confirmed/proposed/assumptions/unresolved; source + access date; identify DOCX tables needing visual check.
9. Deliverables: create `docs/audit/PROJECT_AUDIT.md`, `docs/audit/IMPLEMENTATION_PLAN.md`, update `docs/TODO.md`, correct `CONTENTS.txt`; preserve useful docs/ADRs.

---

Now IMPLEMENTATION_PLAN.md.

# PRAMAAN–AICTE Implementation Plan

**Date:** 24 October 2026
**Status:** Finalized per approved decisions; pending verification gates.

## 1. Agreed MVP scope
...

## 2. Main user roles and workflows
...

## 3. Proposed technology stack
...

## 4. Component/module boundaries
...

## 5. Core data entities and relationships
...

## 6. API implementation sequence
...

## 7. Frontend implementation sequence
...

## 8. Security and privacy controls
...

## 9. Testing and acceptance criteria
...

## 10. External integration dependencies
...

## 11. Demo data and mock integration boundaries
...

## 12. Milestones with concrete completion criteria
...

## 13. Recorded decisions and their implementation impact
...

Let me write both files now, in parallel.</think>Plan mode is over, so I can now write the finalized deliverables. Writing the two audit documents:<tool_call>write<arg_key>content</arg_key><arg_value># PRAMAAN–AICTE Project Audit

**Date:** 24 October 2026
**Status:** Audit complete. Implementation plan finalized and approved. No application code has been written.

## 1. Executive summary

PRAMAAN–AICTE is currently a documentation-blueprint project: the repository contains project documentation, research material, and plans, but **no application source code**.

The documentation set reviewed in this audit is unusually disciplined for a student project. It consistently separates verified facts / authoritative sources, proposed design decisions, simulated behavior (`MOCK`/`DEMO`), prototype thresholds and targets, and legal/regulatory claims pending external verification.

Core safety principles are well documented: candidate-not-verdict matching, institution-side plaintext identity boundary, versioned policies, deterministic reconciliation, purpose-limited verification, audit events.

**Key findings:**

1. The master Word report (`docs/PRAMAAN_AICTE_Complete_Master_Report_Final.docx`) is a three-part document (Research / Redesigned Architecture / Implementation Specification) prepared 24 October 2026, with an explicit change log correcting prior technical/factual positions.
2. Several documents are stale or internally inconsistent (CONTENTS.txt; API contracts; adapter states; thresholds; batch lifecycle; legal interpretation).
3. External verification gates V-01…V-12 remain open; no web research was performed during the initial inspection.
4. The repository cannot yet execute acceptance criteria because no source code exists.

The user-approved audit direction (2026-10-24) resolves the most consequential internal contradictions directionally and is recorded in §16.

## 2. Complete document inventory

| # | Document | Path | Purpose | Reviewed | Issues |
|---|---|---|---|---|---|
| 1 | README | `README.md` | Blueprint status, goals, tiers, docs index | Yes | Consistent with docs-only state |
| 2 | Agent instructions | `AGENTS.md` | Agent directives | Yes | None material |
| 3 | Contents | `CONTENTS.txt` | Inventory | Yes | Stale line counts; missing frontend design system and Word report |
| 4 | PRD | `docs/PRD.md` | Product requirements | Yes | None material |
| 5 | Architecture | `docs/architecture.md` | Components, boundaries, lifecycles | Yes | Threshold wording superseded by report correction |
| 6 | Data model | `docs/data-model.md` | Logical entities | Yes | Naming drift vs. report |
| 7 | API contracts | `docs/api-contracts.md` | Internal API examples | Yes | Path/set drift vs. report Part III |
| 8 | Security baseline | `docs/security-privacy.md` | Threats/controls | Yes | Release checklist unchecked |
| 9 | Testing | `docs/testing.md` | Tests/evaluation | Yes | Test ID numbering drift; benchmark honesty |
| 10 | Research register | `docs/research-and-verification.md` | V-01…V-12 | Yes | Current-status note |
| 11 | Frontend design system | `docs/frontend-design-system.md` | UI rules | Yes | Missing from CONTENTS |
| 12 | Glossary | `docs/GLOSSARY.md` | Terminology | Yes | None material |
| 13 | TODO | `docs/TODO.md` | Roadmap | Yes | Phase/task alignment pending |
| 14 | ADRs | `docs/adr/0001`–`0004` | Architecture decisions | Yes | Statuses: Proposed / Accepted |
| 15 | Master report | `docs/PRAMAAN_AICTE_Complete_Master_Report_Final.docx` | Research + redesign + implementation spec | Yes (OOXML text extraction) | Table-extraction limits; open `[VERIFY]` gates |

## 3. Confirmed project requirements

- **PRD:** FR-01…FR-16 (authorization, batch intake, validation, snapshots, reconciliation, linkage, adjudication, verification, audit, adapters, operations, reporting, public-sector UI, accessibility, honest states, density), non-functional requirements, frontend acceptance criteria, prototype success criteria.
- **Architecture:** modular monolith; components; trust boundaries; identity constraints; policy lifecycle; batch lifecycle; adapter states; constraints.
- **Data model:** logical entities and invariants.
- **Security:** assets, threats, required controls, PPRL-specific risks, legal-review boundary, release checklist.
- **Testing:** T-01…T-16; identity evaluation; metrics; benchmark record.
- **Research:** source hierarchy, V-01…V-12, claim discipline, research log template.
- **Frontend design system:** design objective, visual principles, branding, shell, page patterns, status language, interaction/accessibility requirements, data safety, components, prohibited shortcuts, UI review checklist.

## 4. Word report summary and relationship to existing documentation

The Word report is `docs/PRAMAAN_AICTE_Complete_Master_Report_Final.docx` (approx. 141 KB). It contains three parts:

- **Part I — Corrected source research:** executive summary, official problem statement, ecosystem analysis, gap analysis, innovation candidates, scoring, architecture, database/API contracts, validation rules, security/privacy assessment, prototype plan, synthetic data, demo plan, risks, verification decisions, ERD.
- **Part II — Redesigned architecture & ERP summary:** executive decision, goals/non-goals, logical architecture, data flow, PPRL redesign, domain model, intake compiler, adjudication, DPDP, security/audit, API design, implementation backlog, sprint order, UI/screen inventory, governance/retention, demo plan, ADR register, verification register, final assessment.
- **Part III — Implementation-ready technical specification:** requirements traceability, workflows/sequences, logical API contracts, data dictionary, threat model, security design rules, deployment, performance, backlog, sprint order, UI inventory, governance, demo plan, ADR register, consolidated `[VERIFY]` register, release gates, final assessment.

**Change-log corrections** (authoritative within the report): A1–A7, B1–B6, C1–C5, D1–D2, E1–E6 — covering demo-script arithmetic, API response totals, DPDP notification date, DigiLocker sample URI, SIH statement range, similarity thresholds, legal-notice handling, PPRL data-flow contradiction, mobile HMAC approach, implementation-plan scope, benchmark claims, SIH provenance, and bibliography quality.

The report is treated as an important research input and proposal source, **not** unquestionable authority; its corrections are leading proposals pending reconciliation with the Markdown documentation.

## 5. Conflicts, contradictions, omissions, and ambiguities

| # | Conflict | Affected files | Severity | Practical impact | Resolution proposal | Approval / verification need |
|---|---|---|---|---|---|---|
| 1 | API contract drift | `docs/api-contracts.md` vs. report Part III / §20 | High | Two endpoint shapes/sets could drive divergent implementation | Adopt report Part III as leading proposal; reconcile endpoint-by-endpoint; publish one canonical contract | User decision 3 approved |
| 2 | Adapter state vocabulary | `docs/PRD.md`, `docs/architecture.md`, report §10.1/§29 vs. report §14 | High | `MOCK`/`SANDBOX_TESTED` vs. `MOCKED`/`TESTED` confusion risks mislabelling | Standardize on `MOCK`, `CONFIGURED`, `SANDBOX_TESTED`, `PRODUCTION_VERIFIED`, `DISABLED` | User decision 2 approved |
| 3 | Similarity bands | report change-log A7 / §4.3 vs. `docs/architecture.md` | High | Threshold semantics unclear; risk of mis-band classification | Keep `<0.78`, `[0.78, 0.92)`, `≥0.92` as experimental; human review; no automatic consequence | User decision 1 approved |
| 4 | Tier taxonomy | `README.md`, `docs/PRD.md`, `docs/TODO.md` vs. report §14 tiers | Medium | Confusing scope boundaries | Keep Tier 1 / 1.5 / 2 canonical; crosswalk report Core/Extended/Future | User decision 6 approved |
| 5 | Batch lifecycle | `docs/architecture.md` vs. report workflow steps | Medium | State naming/granularity drift | One canonical state machine; workflow steps separate | User decision 7 approved |
| 6 | Legal/privacy interpretation | report change-log B1–B6 vs. markdown | High | Consent/notice/legal-basis interpretation risk | Provisional design guidance; keep `[VERIFY]` | User decision 4 approved |
| 7 | Benchmark labels | report change-log C5 vs. `docs/testing.md` | Medium | Measured vs. target claims | Keep precision/FAR/latency as synthetic-data targets | Medium |
| 8 | Inventory staleness | `CONTENTS.txt` | Low | Wrong/missing entries | Correct inventory | Low |
| 9 | DPDP notification date | report change-log A3 vs. research register | Medium | Date accuracy | Treat as `[VERIFY]` pending primary source | Medium |

## 6. Technical feasibility assessment

The recommended prototype stack (report; ADR-0001) — FastAPI / Pydantic v2; PostgreSQL 16; React 18 + TypeScript + Vite + Tailwind; TanStack virtualized tables; Web Worker CSV parsing; RapidFuzz; scikit-learn; jwcrypto Ed25519; W3C SD-JWT (later) — is assessed as feasible for a student team to demonstrate Tier 1 end-to-end on synthetic data; the PPRL + SD-JWT scope is ambitious but bounded.

The 36-hour sprint figure is a stretch target, not a commitment.

## 7. Security and privacy risks

Documentation-level findings reviewed. Required controls are documented; the release checklist is currently unchecked; the document is explicitly not a security audit or legal compliance certification.

## 8. Algorithmic and research concerns

Two-stage matching design (exact scoped APAAR HMAC → composite Bloom filter + secondary split encoding → similarity on blocked candidate pairs / Jaro–Winkler in trusted boundary → adjudication). Bands `<0.78`, `[0.78, 0.92)`, `≥0.92` treated as experimental; human review; no automatic consequence from score.

## 9. Unverified external claims and required evidence

V-01…V-12 open; `[VERIFY]` items; no web research performed during initial inspection.

## 10. Frontend and accessibility findings

Design system is mandatory and detailed; no code yet; UI review checklist defined.

## 11. Prioritized recommendations

- **Critical:** SIH verification gate; privacy-design contradiction corrected in report must be codified; documentation contradictions before implementation.
- **High:** thresholds; adapter taxonomy; API canonicalization; legal interpretation; security release checklist.
- **Medium:** benchmark honesty; tier/lifecycle unification; CONTENTS freshness.
- **Low:** documentation polish.

## 12. Proposed final source of truth for requirements and architecture

Proposed canonical sources: Word report Part II (redesigned architecture) as engineering proposal source for prototype; Markdown docs as living project docs; PRD as product requirements; ADRs as decisions; research register as verification tracker.

## 13. Decisions requiring team approval

Legal/regulatory posture; live integration; credential issuance; PPRL production; retention/deletion; enforcement automation.

## 14. Issues that must be resolved before implementation

Internal contradictions; verification gates; security release checklist; legal interpretation.

## 15. Issues that can safely be deferred

Live adapters; SD-JWT issuance; Isolation Forest; advanced PPRL hardening; scale/performance hardening.

## 16. Decisions recorded from the approved audit direction (2026-10-24)

1. Similarity thresholds `<0.78`, `[0.78, 0.92)`, `≥0.92` kept as experimental prototype parameters; no automatic identity verification/merge/consequential decision from score alone; future auto-matching requires separate validation/approval.
2. Adapter states standardized on `MOCK`, `CONFIGURED`, `SANDBOX_TESTED`, `PRODUCTION_VERIFIED`, `DISABLED`; configured ≠ tested; mock ≠ live.
3. API contracts: report Part III leading proposal; reconcile with `docs/api-contracts.md`; one canonical contract; no invented external specifications.
4. Legal/privacy: report corrections provisional design guidance, not legal certification; keep `[VERIFY]`.
5. MVP scope: demonstrable MVP with synthetic data + labelled mocks; defer Isolation Forest, production integrations, SD-JWT issuance unless essential; modular for later addition.
6. Tier taxonomy: Tier 1 / 1.5 / 2 canonical; map report Core/Extended/Future via crosswalk; flag ambiguous mappings.
7. Batch lifecycle: one canonical state machine; report 11 workflow steps separate from persistent states.
8. Verification: maintain V-01…V-12; distinguish confirmed/proposed/assumptions/unresolved; source + access date; identify DOCX tables needing visual check.
9. Deliverables: create `docs/audit/PROJECT_AUDIT.md`, `docs/audit/IMPLEMENTATION_PLAN.md`, update `docs/TODO.md`, correct `CONTENTS.txt`; preserve useful docs/ADRs.
