# ADR-0008: Reconciliation Sits Between VALIDATED and SUBMITTED_FOR_REVIEW

- **Status:** Accepted
- **Date:** 2026-10-25

## Context

ADR-0007 declared the batch state machine in `docs/architecture.md` canonical:

```
CREATED -> UPLOADED -> VALIDATING -> VALIDATION_FAILED | VALIDATED
       -> RECONCILING -> RECONCILED -> SUBMITTED_FOR_REVIEW
       -> APPROVED | RETURNED | REJECTED
```

Milestone 5 shipped before Phase 2 existed and therefore wired `confirm` as
`VALIDATED -> SUBMITTED_FOR_REVIEW`, skipping `RECONCILING` and `RECONCILED`
entirely. That made the canonical machine unimplementable in practice: a batch
could reach review without ever being reconciled, and the two reconciliation
states were unreachable.

## Decision

Keep the canonical machine and make `confirm` follow it rather than the other
way round.

| Operation | From | To |
|---|---|---|
| `POST /batches/{id}/reconcile` starts a run | `VALIDATED` | `RECONCILING` |
| Re-run with a different snapshot or policy before submitting | `RECONCILED` | `RECONCILING` |
| Run completes successfully | `RECONCILING` | `RECONCILED` |
| `POST /batches/{id}/confirm` (operator submits for review) | `RECONCILED` | `SUBMITTED_FOR_REVIEW` |
| Operator re-uploads a corrected CSV (Milestone 5.1 edge) | `VALIDATION_FAILED` | `UPLOADED` |

**A failed run is a rollback, not a transition.** The batch's prior state is
captured before the run and restored if the run raises, while the attempt is
still recorded as a `FAILED` reconciliation run. No new persistent state is
invented for failure, because the canonical machine defines none.

### Separation of concerns

The four concerns are now distinct stages with distinct artifacts:

1. **Submission** - the operator uploads and validates a roster; artifact is the
   staged row set and batch state.
2. **Reconciliation** - a deterministic comparison against one approved snapshot
   under one policy version; artifact is an immutable run with row outcomes and
   a digest. It reads roster rows and snapshot entries and **writes to neither**.
3. **Review** - a human decides `APPROVED | RETURNED | REJECTED`. Not built yet.
4. **Identity verification** - out of scope. Reconciling successfully says
   nothing about who a student is; no identity-verified flag exists and none may
   be inferred from a reconciliation outcome (ADR-0004, ADR-0002).

## Consequences

- `confirm` now rejects a `VALIDATED` batch. Existing Milestone 5 tests gained an
  explicit reconciliation step; their assertions about the final state are
  unchanged. This is the one deliberate change to prior behavior.
- The Roster Intake page can no longer submit directly after validating: it
  routes the operator to Reconciliation and enables submission only once the
  batch is `RECONCILED`.
- Re-running against a new policy or snapshot is permitted before submission and
  appends a new run; finished runs are never rewritten, so history stays
  reproducible.
- `docs/api-contracts.md`, `docs/data-model.md`, the model, the API, the
  frontend and the tests are updated together to match.
