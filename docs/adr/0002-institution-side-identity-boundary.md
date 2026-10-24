# ADR-0002: Keep Plaintext Identity at the Institution Boundary
- **Status:** Proposed; security review required
- **Date:** 2026-10-24

## Context
A central plaintext identity store conflicts with claims that central matching is privacy-preserving.

## Decision
Keep plaintext identity attributes institution-side. The central matcher receives purpose-scoped tokens and/or a reviewed encoding only where required. Treat derived data as sensitive; do not claim anonymity or zero leakage.

## Follow-up
Document adversary model, key scope/rotation, query limits, encoding profile, retention, attack tests, and independent cryptographic/privacy review.
