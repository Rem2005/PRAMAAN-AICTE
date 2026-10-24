# Product Requirements Document
**Status:** Proposed specification; external rules remain subject to primary-source verification.

## Product summary
PRAMAAN–AICTE proposes controlled workflows for roster intake, approved-intake reconciliation, identity-linkage exception review, and authorized verification. It is a workflow layer, not a replacement for national education repositories or a campus ERP.

## Goals
- Import roster data with row-level validation and traceable batch states.
- Compare validated enrolment with an immutable, versioned approved-intake snapshot.
- Produce deterministic and explainable reconciliation results.
- Route possible identity matches to authorized human review.
- Support purpose-limited verification and minimum-necessary disclosure.
- Preserve policy versions, source references, corrections, and audit events.

## Non-goals
- Issuing or changing official identifiers.
- Automatically determining fraud or imposing penalties.
- Claiming production-ready PPRL before independent review.
- Claiming legal compliance merely because selected controls exist.
- Connecting to government systems without official contracts and authorized credentials.

## Roles
| Role | Responsibility | Limit |
|---|---|---|
| Institution Data Operator | Upload and correct roster | Own institution only |
| Nodal Officer | Review batch/reconciliation | Cannot bypass audit history |
| Identity Review Officer | Review candidates | Sensitive access limited and audited |
| Policy Author | Draft/test rules | Cannot self-approve production policy |
| Policy Approver | Approve/publish versions | Must cite verified sources |
| Verification Requester | Request specific claims | No unrestricted roster browsing |
| Auditor | Inspect audit events | Audit access is also logged |
| Platform Admin | Manage roles/configuration | Admin does not imply identity-data access |

## Functional requirements
- **FR-01 Authorization:** every request checks role and institution scope. Acceptance: cross-tenant access tests are denied.
- **FR-02 Batch intake:** record uploader, checksum, schema version, timestamps, and state. Acceptance: retries are idempotent.
- **FR-03 Validation:** report row-level errors and counts; never silently drop rows.
- **FR-04 Intake snapshots:** published snapshots are immutable and include provenance/effective dates.
- **FR-05 Reconciliation:** record input snapshot and policy version; same inputs yield same output.
- **FR-06 Linkage:** record method/version/reasons; a match score cannot trigger an adverse outcome.
- **FR-07 Adjudication:** decisions, evidence refs, corrections, and transitions are audited.
- **FR-08 Verification:** record requester, purpose, requested claims, authority/consent state where applicable, expiry, and decision.
- **FR-09 Audit:** log sensitive reads, exports, policy changes, and decisions without exposing sensitive values.
- **FR-10 Adapters:** use explicit states `MOCK`, `CONFIGURED`, `SANDBOX_TESTED`, `PRODUCTION_VERIFIED`, `DISABLED`.
- **FR-11 Operations:** show job state, retry count, safe error codes, and adapter health.
- **FR-12 Reporting:** reports include generation time, versions, and data classification; exports are audited.
- **FR-13 Public-sector UI:** use the required visual and interaction rules in `frontend-design-system.md`; no generic AI/SaaS aesthetic or unverified official branding.
- **FR-14 Accessible workflows:** every form control has a visible label, errors are actionable and associated with fields, keyboard focus is visible, status is not conveyed by colour alone, and layouts remain usable on narrow screens.
- **FR-15 Honest state presentation:** demo data, mock integrations, empty states, loading states, errors, and disabled actions are explicitly labelled; no fabricated counts or success states.
- **FR-16 Operational density:** administrative pages prioritize search, filters, tables, batch states, review queues, and audit context over marketing copy and oversized hero sections.

## Non-functional requirements
Security, tenant isolation, privacy/data minimization, reproducibility, accessible validation, bounded retries, redacted logs, maintainability, and measurable—not invented—performance targets.

## Frontend acceptance criteria
- The interface follows `frontend-design-system.md` and has no gratuitous gradients, glass effects, glowing borders, or decorative AI motifs.
- The primary workflow can be understood without onboarding animation or marketing-style copy.
- Tables and filters support real search/sort/pagination where shown; controls without implemented behavior are disabled and explained.
- Branding is accurate and authorised; otherwise the UI uses a plain product wordmark and prototype disclosure.
- Review states distinguish pending, candidate match, confirmed by reviewer, rejected, and unable to determine; colour is supplemented by text/icons.
- Key pages pass keyboard-only navigation, visible-focus, labelled-control, contrast, and responsive-width checks.

## Success criteria for prototype
All rows accounted for; deterministic reconciliation; no cross-tenant access in tests; no plaintext identity fields in central matcher tables; no score-only adverse decision; mock/live states distinguishable; benchmarks reproducible.

## Dependencies to verify
Official SIH statement; applicable AICTE intake rules; UGC policy; DPDP Act/Rules applicability; APAAR/ABC and DigiLocker/API Setu contracts; institutional ERP schemas; controller/processor roles; PPRL threat model. See `research-and-verification.md`.
