# ADR-0009: Visual Direction - Forest Green Primary on Off-White

- **Status:** Accepted
- **Date:** 2026-10-25

## Context

Two documents gave contradictory palette guidance:

- `docs/frontend-design-system.md` section 2 and `AGENTS.md` directive 18
  specified a **deep navy** primary on white with limited Indian tricolour
  accents.
- The Milestone 5/7 brief specified **off-white surfaces with a forest-green
  primary accent**, a persistent desktop sidebar, thin borders and restrained
  neutral surfaces.

Milestone 5 implemented navy. Milestone 6's restyle moved to forest green while
the specification still said navy, leaving contradictory guidance on record -
which the Milestone 7 brief explicitly asks to resolve.

## Decision

**Forest green (`--color-forest-700`, #1b5e3a) is the single primary accent,
on an off-white canvas (`--color-canvas`, #f6f5f1) with white surfaces and thin
neutral borders.** Navy is retired as the primary; no component may reference
`--color-navy-*`, and those tokens no longer exist.

Everything else in `docs/frontend-design-system.md` is unchanged and still
binding: restrained and administrative rather than promotional, compact
navigation, dense scannable tables, status conveyed by colour *plus* text,
persistent `MOCK`/`DEMO` labelling, WCAG 2.2 AA contrast as the target, usable
at 320 CSS pixels, and no gradients, glassmorphism, glowing borders, decorative
AI imagery or oversized hero sections. The saffron/green tricolour accents stay
small and contextual; they are never the primary action colour.

`AGENTS.md` directive 18 and `docs/frontend-design-system.md` section 2 are
amended so the repository states one direction rather than two.

## Consequences

- `frontend/src/index.css` is the only place palette values are declared;
  components reference tokens, not raw hex.
- Headings use neutral ink (`--color-ink`), not the accent, so green reads as an
  action colour rather than decoration.
- A future palette change is a token edit plus this ADR's successor - not a
  sweep of component files.
