# System Architecture
**Status:** Proposed design, not an official AICTE specification.

## Decision
Begin with a modular monolith. Use clear domain boundaries and a background worker for long-running imports/reconciliation. Choose the concrete framework after inspecting the actual codebase; do not pretend a stack is already selected.

## Components
1. Institution Portal — uploads, reconciliation, cases, verification requests, reports.
2. Authentication/Authorization — session, role, institution scope, privileged actions.
3. Roster Import — checksum, schema mapping, row validation, state machine.
4. Approved-Intake Registry — versioned snapshots and provenance.
5. Reconciliation Engine — deterministic rules tied to a policy version.
6. Identity Linkage — exact scoped-token comparison and candidate-generation interface.
7. Case/Adjudication — human review, evidence references, correction history.
8. Policy Registry — draft/test/approve/publish lifecycle.
9. Verification Gateway — purpose/authority checks and minimum disclosure.
10. Audit/Reporting — redacted structured events and scoped exports.
11. Integration Adapters — typed wrappers, mocks by default.
12. Background Worker — idempotent jobs and bounded retries.

## Data flow
```text
Portal -> Auth/tenant authorization -> Roster staging -> Validation
     -> Versioned intake snapshot + policy package -> Reconciliation
     -> Candidate review (if needed) -> Human adjudication
     -> Purpose-limited verification -> Scoped report + audit events
```

## Trust boundaries
**Institution boundary:** plaintext identity attributes remain institution-side in the proposed design. Local components generate only the tokens/encodings required for an approved purpose.

**Central application:** stores batch metadata, snapshots, policy versions, reconciliation outputs, case metadata, pseudonymous linkage data, verification requests, and audit events. Tokens and encodings remain sensitive and may permit inference.

**External adapter:** all calls go through typed adapters with schema validation, timeout/retry policy, correlation IDs, and explicit status. Mocks are default until contracts and access are verified.

## Identity-matching constraints
- Use scoped keyed tokens; do not use plain hashes for low-entropy identifiers.
- Do not use only the last four phone digits as a strong identity key. Shared/recycled numbers remain a risk even with full-number HMAC.
- Jaro–Winkler is for strings, not Bloom-filter bit arrays.
- Any encoded similarity method must match the representation and be tested on labelled synthetic data.
- Values such as `0.78` or `0.92` are prototype parameters only, not official thresholds.
- A high score is a candidate for review, never proof of a violation.

## Policy lifecycle
`Draft -> Test -> Source review -> Approve -> Publish with effective dates -> Supersede with new version`.
Published policy packages are immutable; every result records its version.

## Batch lifecycle
Proposed states: `CREATED -> UPLOADED -> VALIDATING -> VALIDATION_FAILED | VALIDATED -> RECONCILING -> RECONCILED -> SUBMITTED_FOR_REVIEW -> APPROVED | RETURNED | REJECTED`. All transitions are validated and audited.

## Adapter states
- `MOCK`: simulated only.
- `CONFIGURED`: configuration exists but is not proven.
- `SANDBOX_TESTED`: tested against an authorized sandbox/contract.
- `PRODUCTION_VERIFIED`: authorized production access and contract tests passed.
- `DISABLED`: unavailable or turned off.

## Constraints
No API calls from UI directly; no sensitive values in ordinary logs; no unversioned policy; no automatic penalties from match scores; no live-integration claim without evidence; no PPRL zero-leakage claim without independent review.


## Presentation layer
The presentation layer is an administrative public-sector interface, not a marketing landing page. Use the shared UI system in `frontend-design-system.md`. It communicates with application services through the project's internal API/client layer; the browser must not call external government services directly. Keep status, mock/live integration state, data classification, and reviewer decisions explicit. Do not expose identity attributes in global search, analytics events, URLs, browser logs, or routine error messages.

### Page patterns
- **Institution dashboard:** compact summary of actionable batches, unresolved exceptions, and recent activity; all counts must be derived from data and demo-labelled when synthetic.
- **Roster intake:** upload, column mapping, validation summary, row-level errors, and downloadable error report.
- **Reconciliation:** selected snapshot and policy versions, discrepancy table, and explainable result categories.
- **Identity review:** least-privilege candidate queue, reason codes, evidence references, and explicit reviewer actions; score is not a verdict.
- **Verification requests:** purpose, requested claims, requester, expiry, and decision state.
- **Audit and administration:** searchable, paginated, scoped records with sensitive values redacted.
