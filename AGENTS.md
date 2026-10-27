# Agent Instructions — PRAMAAN–AICTE

## Read first
Read `docs/PRD.md`, `docs/architecture.md`, `docs/TODO.md`, `docs/GLOSSARY.md`, `docs/security-privacy.md`, `docs/research-and-verification.md`, and `docs/frontend-design-system.md` before changing behavior or UI. Review relevant ADRs. If source code and docs conflict, report the conflict; do not silently guess.

## Strict directives
1. Do not invent regulatory rules, SIH facts, official endpoints, schemas, deadlines, credentials, or API capabilities.
2. Mark every simulated integration `MOCK`/`DEMO` in code, UI, logs, and reports.
3. Matching creates a candidate for review; never trigger a penalty or declare fraud from a score alone.
4. Under the proposed design, plaintext identity attributes remain at the institution-side boundary; do not add them to central matcher tables or routine logs.
5. Treat HMAC tokens, PPRL encodings, and scores as sensitive and potentially linkable—not anonymous by default.
6. Enforce institution scope and role authorization server-side on every resource request.
7. Version policy packages, approved-intake snapshots, matching methods, and reconciliation runs.
8. Never silently drop invalid rows; preserve counts and row-level errors.
9. Do not claim legal compliance, production security, accuracy, FAR, latency, or official integration without evidence.
10. Use synthetic data by default. Never commit real student records, credentials, tokens, private keys, or unredacted logs.
11. Do not invent custom cryptography or claim zero leakage; require a threat model and specialist review for production PPRL.
12. Jaro–Winkler works on strings, not Bloom-filter bit arrays. Any encoded similarity method must be compatible, documented, and tested.
13. Do not implement guessed external endpoints. Build typed adapter interfaces and mocks until official contracts and access are verified.
14. Keep changes small; add tests and update docs/ADRs when behavior or architecture changes.
15. Follow `docs/frontend-design-system.md` as a required UI specification, not optional inspiration.
16. The interface must resemble a restrained, credible Indian public-sector administrative portal—not a generic AI/SaaS dashboard.
17. Never fabricate official emblems, government seals, verification badges, agency endorsements, or integration status. Use approved assets only when usage is authorised; otherwise use a text wordmark and clearly identify the prototype.
18. Prefer compact headers, conventional navigation, readable forms, dense but scannable tables, clear status labels, and restrained forest-green/off-white surfaces with limited Indian tricolour accents (see ADR-0009).
19. Avoid gratuitous gradients, glassmorphism, glowing borders, oversized hero sections, excessive rounded cards, decorative AI imagery, emoji-heavy UI, and animations without functional purpose.
20. Every visible control must work or be explicitly disabled with an explanation. Never present placeholder metrics or mock records as real institutional data; persistently label demo data and mock integrations.
21. Meet keyboard, focus, contrast, semantic-label, validation, and responsive-layout requirements. Test important screens at desktop and mobile widths.
22. Do not copy another portal pixel-for-pixel. Use the National Internship Portal screenshot only as a high-level reference for official tone, information density, filters, and navigation.

## Required workflow
Inspect existing code; state assumptions; implement the smallest roadmap slice; add tests; run available checks; update docs; report changed files, test results, untested paths, and residual risks.

## Definition of done
Acceptance criteria met; relevant tests pass or failures are reported; tenant and privacy implications reviewed; docs updated; mock/live status explicit; no unsupported claims introduced.

## Browser testing policy
- Use Playwright only when browser testing materially helps verify the feature: interactive UI, responsive layouts, keyboard navigation, accessibility behavior, or end-to-end workflows.
- Do not launch a browser for backend-only work, documentation changes, or ordinary unit tests. Prefer unit tests, component tests, static checks, and production builds when those adequately verify the change.
- Never terminate, restart, or interfere with the user's existing Brave or Chrome application or browser session.
- Never use a broad process-kill command (e.g. `taskkill //IM brave.exe`, `pkill chrome`) to clean up browser processes.
- Never call `browser.close()` on a browser connected to the user's existing browser through CDP.
- Close only the test page or browser instance created exclusively for the test, and only when it is safe to do so.
- Browser tests must launch their own isolated browser instance with a temporary user-data directory, separate from the user's normal profile. Never attach to or reuse the user's normal browser profile.
- Track only the process and temporary profile created by the test. Clean up only resources owned by the test, using a bounded and safe cleanup strategy.
- If safe isolated browser startup is unavailable, report browser verification as skipped with a clear explanation. Do not silently fall back to controlling the user's active browser.
