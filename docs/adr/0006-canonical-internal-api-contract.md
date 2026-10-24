# ADR-0006: Canonical Internal API Contract Source

- **Status:** Accepted
- **Date:** 2026-10-24

## Context
`docs/api-contracts.md` and the master Word report Part III proposed different API path sets/shapes; drift could drive divergent implementation.

## Decision
Use the Word report Part III API design as the leading proposal; reconcile endpoint-by-endpoint with `docs/api-contracts.md`; publish one canonical contract. Do not invent undocumented external API specifications.

## Consequences
Dependent documentation must be updated; external government endpoints remain unclaimed until verified.
