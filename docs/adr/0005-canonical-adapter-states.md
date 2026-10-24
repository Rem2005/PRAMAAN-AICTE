# ADR-0005: Canonical Adapter State Taxonomy

- **Status:** Accepted
- **Date:** 2026-10-24

## Context
Documentation used inconsistent adapter state vocabulary (`MOCK`/`SANDBOX_TESTED` in some docs; `MOCKED`/`TESTED` in others), risking mock/live mislabelling.

## Decision
Use the explicit adapter states: `MOCK`, `CONFIGURED`, `SANDBOX_TESTED`, `PRODUCTION_VERIFIED`, and `DISABLED`.

## Consequences
A configured adapter must not be represented as tested; a mock must never be represented as a live integration.
