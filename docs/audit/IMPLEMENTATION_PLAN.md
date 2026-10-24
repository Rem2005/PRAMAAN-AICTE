# PRAMAAN–AICTE Implementation Plan

**Date:** 24 October 2026
**Status:** Finalized per approved decisions; verification gates open; no application code written.

## 1. Agreed MVP scope

Approved demonstrable MVP (Tier 1 + Tier 1.5 canonical scope, synthetic data, labelled mocks):

- Auth/roles, institution scope.
- Synthetic CSV intake; row validation; checksum; batch state machine.
- Approved-intake fixtures; deterministic reconciliation; batch lock/versioning; audit trail.
- Institution-local identity vault simulation; exact scoped-token path; PPRL interface and threat model; candidate generation on synthetic data; review band UI; correction flow; synthetic evaluation.

Explicitly deferred: Isolation Forest; production integrations; SD-JWT issuance; live adapters.

## 2. Main user roles and workflows

From PRD: Institution Data Operator; Nodal Officer; Identity Review Officer; Policy Author/Approver; Verification Requester; Auditor; Platform Admin — each with institution scope and limit constraints.

## 3. Proposed technology stack

Based on existing decisions (ADR-0001, report): FastAPI / Pydantic v2; PostgreSQL 16; React 18 + TypeScript + Vite + Tailwind; TanStack virtualized tables; Web Worker CSV parsing; RapidFuzz; Celery + Redis (later); jwcrypto Ed25519; W3C SD-JWT (later).

## 4. Component/module boundaries

Intake, reconciliation, matching, adjudication, verification, audit, adapters, policy — with adapter interfaces and mocks.

## 5. Core data entities and relationships

Institutions; users/role assignments; approved intake snapshots; submission batches; staged enrolments; institution identity vault; linkage tokens; PPRL encodings; match candidates; policy packages; reconciliation runs; adjudication cases; verification requests; audit events; integration jobs.

## 6. API implementation sequence

Canonical sequence (report Part III leading proposal; decision 3 approved):

1. `POST /api/v1/batches`
2. `POST /api/v1/batches/{id}/validate`
3. `POST /api/v1/batches/{id}/reconcile`
4. `GET /api/v1/cases`
5. `POST /api/v1/cases/{id}/decision`
6. `POST /api/v1/verification-requests`
7. `GET /api/v1/jobs/{id}`
8. `GET /api/v1/audit-events`

Plus intake-compiler, identity-linkage, policy endpoints as required. Reconcile with `docs/api-contracts.md` endpoint-by-endpoint.

## 7. Frontend implementation sequence

Design tokens/shell → dashboard → roster intake → reconciliation → identity review → verification → audit.

## 8. Security and privacy controls

Deny-by-default server-side authorization; institution scope; redaction; MFA for privileged roles; audit; DPDP design guards; mock/live labels; encryption/TLS; secrets management.

## 9. Testing and acceptance criteria

T-01…T-16 / TS-01…TS-16; acceptance criteria from PRD; release gates; reproducibility; authorization coverage.

## 10. External integration dependencies

Mock adapters first; live adapters gated on V-07/V-08 and official contracts/access; adapter states `MOCK`, `CONFIGURED`, `SANDBOX_TESTED`, `PRODUCTION_VERIFIED`, `DISABLED`.

## 11. Demo data and mock integration boundaries

Synthetic data; synthetic APAAR prefix (`999…`) with Verhoeff-valid sandbox identifiers; labelled mock integrations; `MOCK`/`DEMO` persistent labels.

## 12. Milestones with concrete completion criteria

M1 schema/fixtures; M2 intake; M3 dedup; M4 W3C/SD-JWT; M5 integration — mapped to approved MVP deferrals.

## 13. Recorded decisions and implementation impact

Decisions 1–9 from the approved audit direction and their implementation impact.
