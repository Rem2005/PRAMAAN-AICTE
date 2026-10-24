# Testing and Evaluation Plan

## Test layers
Unit; database/job integration; role/resource authorization; API/adapter contract; policy regression; end-to-end workflow; security/privacy; performance.

## Minimum test cases
| ID | Scenario | Expected result |
|---|---|---|
| T-01 | Valid synthetic roster | Expected row count accepted |
| T-02 | Missing required column | Actionable schema error |
| T-03 | Mixed valid/invalid rows | All rows accounted for; invalid rows explained |
| T-04 | Same idempotency key retried | No duplicate side effect |
| T-05 | Same reconciliation inputs repeated | Same output digest |
| T-06 | Intake snapshot superseded | Old result remains reproducible |
| T-07 | Cross-tenant access attempt | Denied and appropriately audited |
| T-08 | High match score | Candidate/review only, no automatic violation |
| T-09 | Shared/recycled phone fixture | Potential false linkage documented |
| T-10 | Mock adapter success | UI/report still says `MOCK` |
| T-11 | Malformed adapter response | Safe failure/quarantine; no blind retry |
| T-12 | Over-broad verification request | Denied or narrowed |
| T-13 | Unauthorized export | Denied |
| T-14 | Unknown policy version | Safe explicit failure |
| T-15 | Secret-like value in logs | Redaction/scanner catches it |
| T-16 | Correction after decision | New event; previous history preserved |

## Identity evaluation
Use synthetic labelled positives and hard negatives including common names, spelling/transliteration variants, missing fields, changed guardian names, shared/recycled phones, and cross-scope records. Record generation method, seed, labels, and limitations.

## Metrics
Report only measured precision/recall, false candidate/negative rates, confidence intervals, throughput, p50/p95/p99, resource use, deterministic mismatch count, authorization coverage, and recovery behavior. Define each metric. Targets like `precision >= 0.97`, `FAR = 0.0%`, or `<20 ms` are hypotheses until supported by reproducible test evidence.

## Benchmark record
Commit/build; environment/hardware; dependency/database versions; dataset size/generation seed; concurrency; warm-up; run count; metrics and definitions; raw results; confidence intervals; limitations.
