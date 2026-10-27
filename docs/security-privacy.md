# Security and Privacy Baseline
**Not a security audit or legal compliance certification.**

## Assets
Student roster data; institution-side plaintext identity attributes; linkage tokens/PPRL encodings; match candidates and decisions; verification requests/disclosures; credentials and keys; policy packages; audit events and exports.

## Threats
Cross-tenant access; malicious insider exports; database frequency/inference attacks; key compromise; incorrect policy publication; forged/malformed adapter responses; log/backup leakage; repeated-query inference; false match causing harm.

## Authentication and authorization as implemented (Milestone 6)
- **Mechanism:** local username/password accounts with **server-side sessions**. An opaque random token is stored only as a SHA-256 hash; the browser holds it in an `HttpOnly`, `SameSite=Lax` cookie, so it is not reachable from JavaScript, URLs, or client logs. Logout revokes the row server-side, so replaying a stolen cookie fails.
- **Passwords:** PBKDF2-HMAC-SHA256 via `hashlib.pbkdf2_hmac`, per-user random salt, work factor from `PASSWORD_HASH_ITERATIONS` (600,000 by default). Verification fails closed on malformed or empty input. The work factor is an engineering parameter, not a compliance claim.
- **Authorization:** deny-by-default dependencies. Unauthenticated requests get `401`; a missing role gets `403`; a body naming another institution gets `403`; a batch belonging to another institution returns `404` so its existence is not confirmed. The client-supplied `institution_id` is never used to grant access.
- **Provisioning:** `python -m app.cli create-user` reads `NEW_USER_PASSWORD` from the environment and refuses to run without it. No credentials are committed; `backend/.env.example` documents the variables with no values.
- **Deliberately not implemented:** MFA, password reset, account lockout, session listing UI, audited role changes, and any external identity provider. These remain open items, not silent gaps.
- **Still unproven:** PostgreSQL behaviour. Every run so far used SQLite.

## Required controls
- Deny-by-default and server-side role + institution authorization on every resource.
- MFA for privileged roles where available; session revocation and audited role changes.
- Minimize collected fields; keep plaintext identity at institution-side boundary in the proposed design.
- Redact identifiers, tokens, raw encodings, secrets, and access tokens from logs.
- Use keyed scoped tokens, not plain hashes for low-entropy identifiers; separate keys and plan rotation.
- Encrypt network traffic and sensitive stored fields; keep secrets out of source control.
- Validate file size/type/schema; bound retries, uploads, and queries.
- Audit sensitive reads, exports, policy publication, and adjudication.
- Treat encoded data as potentially linkable; document adversary model, query controls, retention, key scope, and attack tests.
- Provide correction/review paths; a score is never a verdict.

## PPRL-specific risks
Frequency attacks, low-entropy fields, cross-scope linkage, shared/recycled phone numbers, source-data errors, and automation bias. Before production, require an explicit threat model, method/profile documentation, labelled evaluation, attack testing, and independent privacy/cryptographic review.

## Legal/privacy verification
The accountable institution and qualified reviewers must verify applicable laws, notice/consent, minors, exemptions, third-party sharing, retention/deletion, rights, incident duties, and controller/processor roles. Do not hard-code legal conclusions from secondary sources.

## Release checklist
- [ ] No high-severity tenant-isolation failure.
- [ ] No secrets or real student data committed.
- [ ] Sensitive values redacted from logs.
- [ ] Upload, authorization, migration, and resilience tests pass.
- [ ] Decisions and policy changes are audited.
- [ ] PPRL claims are qualified and reviewed.
- [ ] Retention and deletion have an accountable owner and authoritative basis.
- [ ] Integration state is accurately represented.
