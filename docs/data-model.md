# Logical Data Model
Proposed logical entities; final SQL types, indexes, encryption, and retention require implementation review.

| Entity | Key fields | Invariants |
|---|---|---|
| Institution | internal ID, official code, name, status | Code unique within authoritative namespace; changes audited. |
| User/RoleAssignment | user, username, password hash, institution, role, status | Username unique. Password stored as PBKDF2-HMAC-SHA256 and never returned by any endpoint. Role is institution-scoped; deactivation revokes access. |
| AuthSession | token hash, user, created, expires, revoked | Only the SHA-256 of the cookie value is stored; a database read alone cannot be replayed as a login. Revocation and expiry are checked on every request. |
| ApprovedIntakeSnapshot | institution/course/year/category counts, source, effective dates, version | Published versions immutable; updates create a new version. |
| SubmissionBatch | institution, uploader, academic year, source filename, checksum, schema, state, idempotency key | Academic year is stored (it was previously accepted and dropped). The uploaded file name is recorded (basename only) so batch lists can identify the file without exposing a path; it is NULL until an upload is validated. Checksum is recomputed from the uploaded bytes. Transitions go through one transition table. |
| StagedEnrolment | batch, row number, local ref (nullable), programme/category, validation state, errors | No silent row loss: invalid rows are staged too. `local_ref` is NULL when unreadable, so rows without a reference never collide. Unique indexes: `(batch_id, row_number)` always, `(batch_id, local_ref)` for VALID rows only. |
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
