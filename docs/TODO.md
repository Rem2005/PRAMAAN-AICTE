# Implementation Roadmap
Work in order. Mark a task complete only after code, tests, and documentation exist.

## Phase 0 — Foundations
- [ ] Inspect actual repository, framework, entry points, dependency manager.
- [x] Adopt canonical taxonomies and decision records from `docs/audit/PROJECT_AUDIT.md` and `docs/audit/IMPLEMENTATION_PLAN.md` (adapter states, API contract source, batch lifecycle, threshold policy).
- [ ] Configure formatting, lint, type checks, tests, CI, and runtime secrets.
- [ ] Create synthetic fixtures and repeatable demo reset.
- [ ] Define roles, tenant isolation tests, migrations, and initial ADRs.
- [ ] Implement shared UI tokens, typography, header/navigation, form controls, status labels, tables, and responsive shell from `frontend-design-system.md`.
- [ ] Create page-level UI states: loading, empty, error, success, and explicitly labelled demo data.
**Exit:** fresh setup works; CI passes; no real student data/secrets committed; core UI matches the public-sector design specification and passes an initial accessibility/responsive review.

## Phase 1 — Roster intake
- [ ] Batch metadata/state machine and checksum.
- [ ] CSV upload and explicit column mapping.
- [ ] Row-level validation and actionable error codes.
- [ ] Idempotent processing; malformed/empty/oversized file tests.
- [ ] UI for validation results and correction.
**Exit:** every row accounted for; no silent loss; retries safe.

## Phase 2 — Intake reconciliation
- [ ] Immutable approved-intake snapshots with provenance/effective dates.
- [ ] Versioned policy packages and approval lifecycle.
- [ ] Deterministic reconciliation and discrepancy report.
- [ ] Boundary/regression tests and output digest.
**Exit:** same inputs/versions yield the same output; unverified rules remain demo-only.

## Phase 3 — Identity linkage
- [ ] Institution-side identity boundary and synthetic vault.
- [ ] Exact scoped-token path and key-management abstraction.
- [ ] Decide encoded similarity only after documenting method/threat model.
- [ ] Keep similarity bands (<0.78, [0.78, 0.92), ≥0.92) as experimental prototype parameters; route [0.78, 0.92) to human review; no automatic verification/merge/penalty from score alone.
- [ ] Synthetic labelled positives/hard negatives; review queue and reason codes.
- [ ] Test common names, spelling variants, missing data, shared/recycled phones, cross-scope linkage.
**Exit:** no central plaintext identity fields or sensitive logs; claims qualified.

## Phase 4 — Adjudication/audit
- [ ] Case states, reviewer scope, evidence refs, reason codes.
- [ ] Decisions, corrections/review, immutable event history.
- [ ] Audit policy changes, sensitive reads, exports, and decisions.
**Exit:** reproducible decisions; no score-only adverse outcome.

## Phase 5 — Verification/adapters
- [ ] Purpose-limited request and minimum-claim schema.
- [ ] Use canonical adapter states (MOCK, CONFIGURED, SANDBOX_TESTED, PRODUCTION_VERIFIED, DISABLED); a configured adapter must not be represented as tested, and a mock must never be represented as live.
- [ ] Timeout, malformed response, credential failure, retry tests.
- [ ] Add live adapter only with official contract and authorized access.
**Exit:** simulated and live states cannot be confused.

## Phase 6 — Hardening/demo
- [ ] Scoped reports and audited exports.
- [ ] Job monitoring, safe errors, backup/restore, retention plan.
- [ ] Security, authorization, resilience, and performance tests.
- [ ] Synthetic end-to-end demo and actual setup instructions.
- [ ] Review every screen against `frontend-design-system.md`; remove generic AI/SaaS decoration and verify that all visible controls work or are explicitly disabled.
- [ ] Close or disclose verification-register items.
**Exit:** repeatable demo, evidence-backed claims, limitations disclosed.

## Blocked until verified
- [ ] Enable official quota/penalty rules.
- [ ] Claim legal compliance or production readiness.
- [ ] Claim official external integration.
- [ ] Claim PPRL zero leakage or measured accuracy without evidence.
