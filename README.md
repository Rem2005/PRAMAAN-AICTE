# PRAMAAN–AICTE
### APAAR-ID-Based Student Data Management and Verification Platform for AICTE-Approved Institutions

PRAMAAN–AICTE is a proposed workflow and verification platform for institutional roster intake, approved-intake reconciliation, identity-linkage exception review, and purpose-limited verification.

> **Status:** Prototype design. Do not claim official AICTE, APAAR/ABC, UGC, DPDP, DigiLocker, API Setu, ONOD, or SIH verification unless confirmed from primary sources and tested.
> **SIH reference:** SIH26263 — [VERIFY identifier, title, and current statement on the official SIH portal].

## Goals
- Validate roster imports with row-level errors and traceable batch states.
- Reconcile enrolment against versioned approved-intake snapshots.
- Generate identity-linkage candidates for human review, not automated verdicts.
- Support purpose-limited verification and minimum-necessary disclosure.
- Preserve policy versions, evidence references, corrections, and audit events.

## Core principles
1. Separate verified facts, proposed design, demo behavior, and open assumptions.
2. Keep plaintext identity attributes at the institution-side boundary in the proposed design.
3. Treat tokens and PPRL encodings as sensitive; do not claim zero leakage.
4. A similarity score is not proof of identity, fraud, or a policy violation.
5. Version policies and approved-intake snapshots; make results reproducible.
6. Label every simulated integration `MOCK` or `DEMO`.
7. Enforce institution scope and least privilege server-side.

## Prototype scope
**Tier 1:** auth/roles, synthetic CSV import, row validation, approved-intake fixtures, deterministic reconciliation, audit trail.
**Tier 1.5:** institution-side identity-vault simulation, scoped-token matching, candidate review, correction flow, synthetic evaluation.
**Tier 2:** adapter contracts and authorized sandbox integrations only after official documentation and access are confirmed.

## Architecture
```text
Institution Portal -> Auth/Tenant Scope -> Modular Application
  -> Roster Import & Validation
  -> Approved-Intake Registry + Versioned Policy Engine
  -> Reconciliation / Identity Candidate Review / Adjudication
  -> Purpose-Limited Verification Gateway
  -> Audit & Reporting
External services are accessed only through adapters (MOCK by default).
```

## Documentation
- [`AGENTS.md`](AGENTS.md) — instructions for coding agents.
- [`docs/PRD.md`](docs/PRD.md) — product goals and acceptance criteria.
- [`docs/architecture.md`](docs/architecture.md) — components, trust boundaries, and constraints.
- [`docs/TODO.md`](docs/TODO.md) — phased implementation roadmap.
- [`docs/GLOSSARY.md`](docs/GLOSSARY.md) — mandatory terminology.
- [`docs/data-model.md`](docs/data-model.md) — logical entities and invariants.
- [`docs/api-contracts.md`](docs/api-contracts.md) — proposed internal API, not external government endpoints.
- [`docs/security-privacy.md`](docs/security-privacy.md) — threat model and security gates.
- [`docs/testing.md`](docs/testing.md) — test strategy and evaluation.
- [`docs/research-and-verification.md`](docs/research-and-verification.md) — primary-source verification register.
- [`docs/frontend-design-system.md`](docs/frontend-design-system.md) — mandatory public-sector visual and interaction requirements.
- [`docs/adr/`](docs/adr/) — architecture decision records.

## Frontend direction
The UI should feel like a credible Indian public-sector administrative service: restrained forest green and off-white (ADR-0009), limited saffron/green accents, compact navigation, readable forms, practical filters, accessible tables, and clear status language. Avoid generic AI-product styling. See [`docs/frontend-design-system.md`](docs/frontend-design-system.md) for mandatory rules and acceptance checks. Any screenshot/reference is guidance for tone and information density only; do not copy another portal or imply official endorsement.

## Development note
The repository is now a runnable modular-monolith prototype, not only a blueprint:

- `backend/` � FastAPI + SQLAlchemy + Alembic, SQLite for tests/dev (`DATABASE_URL`), PostgreSQL targeted but **not verified**.
- `frontend/` � React 18 + TypeScript + Vite + Tailwind CSS v4, with a same-origin dev proxy so the session cookie stays first-party.

Local sign-in, roles and institution-scoped authorization are implemented with locally provisioned accounts. Roster intake, deterministic reconciliation, reconciliation reporting and CSV export run against persisted synthetic data; identity linkage, verification requests and official integrations are **not** implemented, and the screens say so. No external identity provider or government integration is connected. See `backend/README.md` and `frontend/README.md` for setup, including the `seed-demo` command that creates the synthetic snapshot and policy reconciliation needs.

Use synthetic data in development, screenshots, tests, and public demos. Never commit real student data, government identifiers, API secrets, or private keys.
