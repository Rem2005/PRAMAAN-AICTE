# Proposed Internal API Contracts
These are planning examples, **not** existing AICTE/APAAR/ABC/DigiLocker/API Setu/ONOD endpoints. Publish OpenAPI from the implementation.

## Conventions
- Prefix `/api/v1`; authenticate and enforce institution scope server-side.
- Use idempotency keys for retryable creates/processes.
- Return request/correlation IDs and safe error codes.
- Use UTC timestamps, pagination, input validation, and redaction.
- Never return full sensitive identifiers or raw PPRL encodings by default.

| Method/path | Purpose | Essential inputs | Output |
|---|---|---|---|
| `POST /batches` | Create batch | institution, academic period, checksum, schema version | batch ID/state |
| `POST /batches/{id}/validate` | Validate rows | mapping profile | valid/invalid counts, row errors |
| `GET /batches/{id}` | Read batch | ID | state, counts, safe errors |
| `POST /batches/{id}/reconcile` | Reconcile | snapshot ID, policy version | run ID, totals, discrepancies |
| `GET /reconciliation-runs/{id}` | Read result | run ID | versions, totals, exclusions, digest |
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

## Adapter contract
Each adapter records ID/version, state (`MOCK`, `CONFIGURED`, `SANDBOX_TESTED`, `PRODUCTION_VERIFIED`, `DISABLED`), schemas, auth method, timeout/retry policy, correlation IDs, safe errors, and contract-test evidence. Do not implement live adapters until official contract and access are confirmed.
