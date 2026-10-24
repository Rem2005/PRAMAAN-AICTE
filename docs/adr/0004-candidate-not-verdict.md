# ADR-0004: Matching Produces Candidates, Not Verdicts
- **Status:** Accepted
- **Date:** 2026-10-24

## Context
Identity matching can produce false positives/negatives due to common names, missing data, shared phones, and source inconsistencies.

## Decision
Matching creates a candidate with method/version and reason metadata. It cannot automatically declare fraud, violation, or penalty. Consequential outcomes require applicable verified policy, context, evidence, authorized human review, and an auditable decision.
