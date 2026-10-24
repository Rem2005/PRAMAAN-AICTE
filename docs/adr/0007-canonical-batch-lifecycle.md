# ADR-0007: Canonical Batch State Machine and Workflow Separation

- **Status:** Accepted
- **Date:** 2026-10-24

## Context
Batch lifecycle wording differed between `docs/architecture.md` and the master report workflow steps.

## Decision
Define one canonical batch state machine; keep report workflow steps separate from persistent batch states.

## Consequences
Implementation must map workflow steps onto the canonical state machine explicitly.
