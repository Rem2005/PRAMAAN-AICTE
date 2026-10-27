# Implementation Roadmap
Work in order. Mark a task complete only after code, tests, and documentation exist.

## Completed milestones
- **Milestone 7.3 - Identity Review, Verification Requests and Administration workspaces:** the three screens previously rendered as internal documentation (a notice plus "already implemented"/"still missing" lists) and are now working-style screens. **No backend capability was added, because none exists:** there is no review API, candidate table, request API or adapter, so Identity Review and Verification Requests render their queue/table frames with the documented columns, disabled search and status filters with a stated reason, and an honest empty state — no case, candidate, score, request or decision is fabricated. Administration reads only real data: the session from `/auth/me`, plus the institution's active policy and approved intake snapshot from the existing `/reconciliation/policies` and `/reconciliation/snapshots` endpoints, with loading, permission-denied (403), error-with-retry and not-configured states. Account capabilities are labelled (CLI-only vs not available) instead of implying user management, and the provisioning command is copyable with no secret in it. Shared `StatusTag`, `EmptyState`, `MetaList` and `Dash` primitives were added to `components/ui.tsx`. `PrototypePages.tsx` was replaced by one file per screen. Verified by 14 new frontend tests, the full frontend suite, the production build, and the isolated-browser run at 1440px and 390px.
- **Milestone 7.2 - Sample roster files, intake copy and responsive fixes:** the roster contract now ships as two checked-in files, `docs/samples/sample-roster.csv` (10 valid synthetic rows) and `docs/samples/sample-roster-with-errors.csv` (the same 10 plus 3 deliberately broken rows), documented in `docs/samples/README.md`. `tests/test_intake.py` uploads both through the real create/validate/confirm endpoints, so the files cannot drift from the parser; `frontend/src/lib/sampleRoster.test.ts` asserts the CSV the intake screen downloads matches them row for row. The intake screen downloads the sample for the batch academic year it is about to validate. Pages were audited for long paragraphs and repeated helper text (header subtitles, session boxes, stat-card hints, footnotes) and trimmed to one line each, with the prototype/synthetic disclaimers and the review-only wording kept. Two real 390px overflows were found by the browser run and fixed: the page-header action area could not wrap, and the Administration grid track sized to its `<pre>` content. `frontend/scripts/verify-shell.cjs` had stale assertions (five nav areas were expected to be disabled) and now walks every screen at 1440px and 390px, checks for horizontal overflow and error alerts, and exercises the sample download.
- **Milestone 7 - Reconciliation workflow and screen:** `POST /batches/{id}/reconcile` runs the deterministic engine and persists a run with every row outcome and a SHA-256 digest; history and single-run reads are exposed at `/reconciliation/runs`. Snapshots and policies are listed for the session institution only. The engine previously could not run at all (undefined status constants, policy JSON never parsed, fixed `run_number`, no row outcomes), which is fixed. `python -m app.cli seed-demo` creates a synthetic approved snapshot and active policy idempotently. The Reconciliation screen offers real selectors, run summary, outcome table and history; Reports/Audit lists recorded runs and exports CSV. Identity Review, Verification Requests and Administration are honest screens with no simulated outcomes. Verified by backend tests, frontend tests, a live HTTP flow and an isolated browser run.
- **Milestone 7.1 - Dashboard load failure:** the dev server was loading a stale `vite.config.js` emitted next to `vite.config.ts` (Vite resolves `.js` first), which proxied `/api` to port 8000 while the backend ran on 8002. That surfaced as "Unable to load batches". The config now proxies to `127.0.0.1:8002` via `VITE_API_PROXY_TARGET`, and `tsc -b` no longer writes config output into the project root. Network failures now produce an actionable message instead of a bare fallback.
- **Milestone 6.1 - Dashboard screen:** `GET /api/v1/batches` lists the session institution's batches with counts derived from staged rows; batches record their uploaded file name (migration `0007`). The dashboard shows real totals, status filters, search and pagination with explicit loading/empty/error states, and every synthetic-data surface stays labelled. Verified by backend and frontend tests plus a live local run; Figma fidelity remains approximate because no full-resolution design export was available.
- **Milestone 5 � Roster intake:** batch state machine, CSV upload, row-level validation, preview, explicit confirmation. Backend: `python -m pytest -q`. Frontend: `npm run test`.
- **Milestone 5.1 � Intake integrity:** all-or-nothing submission policy fixed across backend, frontend, API responses and tests; `academic_year` now persisted; checksum always derived from the uploaded bytes; validation is a single transaction; re-validation replaces prior staged rows; unique indexes on staged rows; create/validate/confirm are idempotent on a client key.
- **Milestone 6 � Authentication and authorization:** local accounts (PBKDF2-HMAC-SHA256), server-side sessions in an HttpOnly cookie, role checks and institution scope enforced server-side on every batch endpoint. Verified by unit tests and a live HTTP run (401 unauthenticated, 403 wrong role / other institution, 404 cross-institution read).

**Not verified:** PostgreSQL. All test and local runs used SQLite; the PostgreSQL target in `docs/architecture.md` is unproven.

## Phase 0 — Foundations
- [x] Inspect actual repository, framework, entry points, dependency manager. (FastAPI + SQLAlchemy/Alembic backend; React 18 + TypeScript + Vite + Tailwind v4 frontend; pip and npm.)
- [x] Adopt canonical taxonomies and decision records from `docs/audit/PROJECT_AUDIT.md` and `docs/audit/IMPLEMENTATION_PLAN.md` (adapter states, API contract source, batch lifecycle, threshold policy).
- [ ] Configure formatting, lint, type checks, tests, CI, and runtime secrets.
- [ ] Create synthetic fixtures and repeatable demo reset.
- [x] Define roles, tenant isolation tests, migrations, and initial ADRs. (Roles live in `user_role_assignments`; `backend/tests/test_auth.py::test_cross_institution_access_is_denied` covers T-07; migrations `0001`-`0005` round-trip.)
- [x] Implement shared UI tokens, typography, header/navigation, form controls, status labels, tables, and responsive shell. (Tokens in `frontend/src/index.css`; persistent desktop sidebar plus disclosure navigation for narrow screens.) Note: the shell uses a forest-green primary accent on an off-white canvas per the current design direction, which differs from the navy primary named in `docs/frontend-design-system.md` section 2 � that document still needs reconciling.
- [x] Create page-level UI states: loading, empty, error, success, and explicitly labelled demo data. (Dashboard, roster intake, reconciliation and reports have all four; Identity Review and Verification Requests are explicit "not implemented" screens rather than empty screens with invented rows.)
**Exit:** fresh setup works; CI passes; no real student data/secrets committed; core UI matches the public-sector design specification and passes an initial accessibility/responsive review.

## Phase 1 — Roster intake
- [x] Batch metadata/state machine and checksum.
- [x] CSV upload against a documented fixed column contract. Free column mapping is **not** implemented: headers must already match `REQUIRED_COLUMNS`.
- [x] Row-level validation and actionable error codes.
- [x] Idempotent processing; malformed/empty/oversized/encoding/duplicate file tests. Create, validate and confirm all replay the original outcome for a reused key; conflicting reuse returns 409.
- [x] UI for validation results and correction.
**Exit:** every row accounted for; no silent loss; retries safe.

## Phase 2 — Intake reconciliation
- [x] Immutable snapshot storage with provenance/effective dates (migration `0006`). **Authoring/approval API is not built:** the only writer is the synthetic CLI seed.
- [ ] Versioned policy packages and approval lifecycle. Storage, checksum and ACTIVE-only use are implemented; drafting, activating and approving through the API are not.
- [x] Deterministic reconciliation and discrepancy report (`app/services/reconciliation.py`, `/reconciliation/*` endpoints, Reconciliation and Reports screens).
- [x] Boundary/regression tests and output digest (`tests/test_reconciliation.py`: reproducibility, scoping, refusal paths, duplicate rows, auditor read-only).
- [ ] `RECONCILING`/`RECONCILED` batch states from `docs/architecture.md`; a submitted batch is accepted for reconciliation instead.
**Exit:** same inputs/versions yield the same output; unverified rules remain demo-only. (Met for the implemented slice; the approval lifecycle is still open.)

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
