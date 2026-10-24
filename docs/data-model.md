# Logical Data Model
Proposed logical entities; final SQL types, indexes, encryption, and retention require implementation review.

| Entity | Key fields | Invariants |
|---|---|---|
| Institution | internal ID, official code, name, status | Code unique within authoritative namespace; changes audited. |
| User/RoleAssignment | user, institution, role, status | Role is institution-scoped; deactivation revokes access. |
| ApprovedIntakeSnapshot | institution/course/year/category counts, source, effective dates, version | Published versions immutable; updates create a new version. |
| SubmissionBatch | institution, uploader, checksum, schema, state, idempotency key | Retries do not duplicate processing; transitions audited. |
| StagedEnrolment | batch, row number, local ref, programme/category, validation state | No silent row loss; minimize central identity fields. |
| InstitutionIdentityVault | local ref, encrypted identity attributes, key version, retention | Institution-side boundary; strict access/audit. |
| LinkageToken | local ref, token type, scoped token, key version, purpose, expiry | Scope and key version explicit; avoid cross-purpose reuse. |
| PPRLEncoding | local ref, profile/version, encoded value, expiry | Sensitive pseudonymous data; restricted access/retention. |
| MatchCandidate | record refs, method/version, score, reasons, state | Score is not a legal conclusion. |
| PolicyPackage | version, domain, source clauses, effective dates, approval state, checksum | Published versions immutable. |
| ReconciliationRun | batch, snapshot, policy version, input/output digest, totals | Reproducible for same input and versions. |
| AdjudicationCase | candidate, reviewer, outcome, policy version, timestamps | Corrections preserve prior history. |
| VerificationRequest | requester, purpose, claims, authority/consent ref, expiry, decision | Least-privilege claims; disclosure audited. |
| AuditEvent | actor, scope, action, object, time, result, correlation ID | No secrets or full sensitive values. |
| IntegrationJob | adapter, operation, state, attempts, safe error, correlation ID | Idempotent; secrets excluded from logs. |

## Relationship sketch
```text
Institution -> Users, IntakeSnapshots, SubmissionBatches
SubmissionBatch -> StagedEnrolments -> local references -> IdentityVault
IdentityVault -> LinkageTokens / PPRLEncodings -> MatchCandidates -> AdjudicationCases
Batch + IntakeSnapshot + PolicyPackage -> ReconciliationRun
VerificationRequest -> DisclosureReceipt
Sensitive actions -> AuditEvent
Adapter -> IntegrationJob
```
