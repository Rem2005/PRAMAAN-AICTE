# ADR-0001: Start with a Modular Monolith
- **Status:** Proposed
- **Date:** 2026-10-24

## Context
The prototype has distinct domains but limited time and needs a reliable end-to-end demo.

## Decision
Use a modular monolith with explicit domain boundaries and adapter interfaces. Add a background worker for long-running tasks. Split services only when evidence shows an operational need.

## Consequences
Simpler setup and testing; requires module discipline; independent scaling is limited until later.
