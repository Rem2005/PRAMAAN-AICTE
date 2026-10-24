# Glossary

| Term | Required meaning/usage |
|---|---|
| APAAR/ABC identifier | Identifier in the relevant official education ecosystem; follow current official documentation. |
| Institution scope | Boundary defining which institution's data a user/service may access. |
| Approved-intake snapshot | Immutable approved-intake version with provenance and effective period. |
| Roster batch | Tracked submission with checksum, schema version, uploader, and state. |
| Reconciliation | Deterministic comparison under a specific input snapshot and policy version. |
| Policy package | Versioned, tested, approved rules with source references and effective dates. |
| Candidate match | Possible linkage requiring review; not proof of identity, fraud, or violation. |
| Scoped token | Keyed token limited to a defined purpose/scope; not a universal identifier. |
| PPRL | Privacy-preserving record linkage; does not guarantee anonymity or zero leakage. |
| PPRL encoding | Encoded linkage representation; treat as sensitive. |
| Identity vault | Institution-side controlled storage of plaintext identity attributes. |
| Match score | Output of a particular algorithm/features/version, interpreted with evaluation evidence. |
| Review band | Configured score interval for human review; prototype values until validated. |
| Adjudication | Human review using evidence and a versioned applicable policy. |
| Minimum-necessary disclosure | Return only claims authorized for the stated purpose. |
| MOCK/DEMO | Simulated behavior, not official external verification. |
| Sandbox-tested | Tested against an authorized sandbox and recorded contract version. |
| Production-verified | Authorized production access and contract tests passed; not a legal-compliance certification. |
| Source provenance | Origin, version/date, clause/page, and authority for a rule/data value. |

Avoid unsupported claims such as “fraud detected,” “100% accurate,” “zero PII leakage,” “anonymous,” “fully compliant,” “officially verified,” or “production-ready.” Prefer “candidate match,” “verification pending,” “prototype target,” and “mock response” where accurate.
