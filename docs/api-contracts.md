# Proposed Internal API Contracts
These are planning examples, **not** existing AICTE/APAAR/ABC/DigiLocker/API Setu/ONOD endpoints. Publish OpenAPI from the implementation.

## Conventions
- Prefix `/api/v1`; authenticate and enforce institution scope server-side.
- **Authentication (implemented):** `POST /api/v1/auth/login` returns an `HttpOnly`, `SameSite=Lax` session cookie. Every `/api/v1/batches*` endpoint requires it. The user, institution and roles are read from the session, never from the request body; a body-supplied `institution_id` may only ever *match* the session scope.
- **Status codes:** `401` no valid session; `403` authenticated but wrong role or wrong institution in the body; `404` batch outside your institution (existence is not confirmed); `409` idempotency-key conflict.
- **Idempotency (implemented):** `POST /batches` accepts an optional client `idempotency_key`; reusing it with an equivalent request returns the original batch, and with a different request returns `409`. `POST /batches/{id}/confirm` is keyed by the batch's own `idempotency_key`: a retry returns the original outcome unchanged.
- Use idempotency keys for retryable creates/processes.
- Return request/correlation IDs and safe error codes.
- Use UTC timestamps, pagination, input validation, and redaction.
- Never return full sensitive identifiers or raw PPRL encodings by default.

| Method/path | Purpose | Essential inputs | Output |
|---|---|---|---|
| `POST /batches` | Create batch | institution, academic period, checksum, schema version | batch ID/state |
| `POST /batches/{id}/validate` | Validate rows | uploaded CSV file | valid/invalid/duplicate counts, row errors |
| `POST /batches/{id}/confirm` | Confirm a validated batch (all-or-nothing) | batch idempotency key | state, persisted row count |
| `POST /auth/login` | Start a session | username, password | session identity + roles (sets cookie) |
| `POST /auth/logout` | End a session | session cookie | `signed_out` |
| `GET /auth/me` | Current session, or `authenticated: false` | session cookie | identity, institution, roles |
| `GET /batches` | List the session institution's batches (implemented) | session cookie | newest-first batches with state, academic year, source filename, uploader, created time and staged-row counts, plus totals |
| `GET /batches/{id}` | Read batch | ID | state, counts, safe errors |
| `GET /reconciliation/snapshots` | List approved snapshots (implemented) | session cookie | version, status, source ref, entry count |
| `GET /reconciliation/policies` | List policy packages (implemented) | session cookie | version, status, stored rules, checksum |
| `POST /batches/{id}/reconcile` | Reconcile (implemented) | `?snapshot_id=`, `?policy_id=` (both optional; latest approved/active by default) | run ID, versions, outcome counts, totals, digest, per-row outcomes |
| `GET /reconciliation/runs` | List runs (implemented) | optional `?batch_id=`, `?limit=` | newest-first runs with versions and counts |
| `GET /reconciliation/runs/{id}` | Read result (implemented) | run ID | versions, totals, exclusions, digest, per-row outcomes |
| `GET /cases` | List cases | filters, pagination | scoped summaries |
| `POST /cases/{id}/decision` | Record decision | outcome, reason, evidence refs | decision ID, state, policy version |
| `POST /verification-requests` | Request verification | subject ref, purpose, claims, authority context | request ID, state, permitted claims |
| `GET /jobs/{id}` | Job status | job ID | state, attempts, safe error |
| `GET /audit-events` | Audit search | time, actor, type, scoped object | paginated metadata |

## Example response envelope
```json
{"request_id":"example-id","status":"accepted","data":{},"errors":[],"policy_version":"demo-policy-v1","correlation_id":"example-correlation-id"}
```

## Error taxonomy
`VALIDATION_*` input invalid; `AUTHN_*` authentication issue; `AUTHZ_*` not permitted; `POLICY_*` missing/ambiguous version; `INTEGRATION_UNAVAILABLE` bounded retry may be safe; `INTEGRATION_CONTRACT_MISMATCH` quarantine and investigate; `MATCH_REVIEW_REQUIRED` route to human review; `CONFLICT_VERSION` reload and explicitly select version.

## Implemented vs proposed
Rows marked **implemented** exist in `backend/app/api/`. `GET /batches` is the dashboard data source: scope comes from the session, counts are derived from staged rows, and a batch outside the caller's institution is never in the result set. There is no institution parameter to widen.

Reconciliation is implemented as deterministic, synchronous work over persisted rows: `POST /batches/{id}/reconcile` accepts `VALIDATED` or `SUBMITTED_FOR_REVIEW` batches, appends a run (new `run_number`), and returns the run with every row outcome. It makes no external call. Snapshot and policy packages can currently only be created by `python -m app.cli seed-demo` (synthetic); there is no API for authoring, approving or activating them, so no approval lifecycle is claimed.

`docs/architecture.md` routes `SUBMITTED_FOR_REVIEW` after `RECONCILED`. The prototype accepts a submitted batch for reconciliation instead of adding `RECONCILING`/`RECONCILED` states, so the documented lifecycle is not yet implemented as written. Re-validation adds the edge `VALIDATION_FAILED -> UPLOADED`, which the architecture document does not enumerate.

The remaining rows (`/cases`, `/verification-requests`, `/jobs`, `/audit-events`) are planning examples and have no implementation.

## Adapter contract
Each adapter records ID/version, state (`MOCK`, `CONFIGURED`, `SANDBOX_TESTED`, `PRODUCTION_VERIFIED`, `DISABLED`), schemas, auth method, timeout/retry policy, correlation IDs, safe errors, and contract-test evidence. Do not implement live adapters until official contract and access are confirmed.
