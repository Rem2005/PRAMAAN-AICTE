# ADR-0003: Mock External Integrations Until Verified
- **Status:** Accepted for prototype
- **Date:** 2026-10-24

## Decision
Use typed adapter interfaces and mocks first. Mark every mock result `MOCK`/`DEMO`. Implement a live adapter only after official contract documentation, authorization, credentials, and contract tests exist.
