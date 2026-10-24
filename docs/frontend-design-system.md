# Frontend Design System — Public-Sector Administrative Portal

**Status:** Mandatory proposed design specification for the PRAMAAN–AICTE prototype. This is a visual/product requirement, not a claim of official Government of India or AICTE endorsement.

## 1. Design objective
Build a calm, credible, accessible administrative service for institution operators, nodal officers, reviewers, and auditors. The UI should communicate reliability through clarity, traceability, predictable interactions, and restrained visual design—not through decorative effects or unsupported claims. The supplied National Internship Portal screenshot is a reference for tone, practical information density, compact navigation, and filtering patterns only. Do not copy its exact layout, assets, wording, or branding.

## 2. Visual principles
- **Administrative, not promotional:** start authenticated users on a task-oriented dashboard. Avoid giant hero banners, sales copy, oversized metrics, and marketing CTAs.
- **Restrained palette:** use deep navy for primary navigation/actions, white and neutral grey for surfaces, and small saffron/green accents where they help identify context. Define design tokens centrally; do not scatter arbitrary hex values through components.
- **Typography:** use a highly legible system sans-serif stack, consistent type scale, clear hierarchy, comfortable line height, and strong table readability. Avoid oversized display fonts.
- **Shape and depth:** mostly square or modestly rounded controls, subtle separators, minimal shadows. No glassmorphism, neon glow, gradient borders, animated blobs, or decorative AI artwork.
- **Density:** fit useful operational context above the fold while preserving whitespace and readability. Prefer tables, filter bars, tabs, breadcrumbs, and compact summary strips to a grid of oversized cards.
- **Consistency:** shared spacing, typography, buttons, fields, badges, alerts, tables, pagination, modals, and empty/loading/error states.

## 3. Branding and trust
- Do not create or imitate the State Emblem of India, AICTE marks, ministry logos, official seals, or government certification badges. Use approved assets only where their use is authorised and appropriate.
- If authorised official assets are not available, use a text-only PRAMAAN–AICTE wordmark and a visible prototype disclosure such as **“Prototype demonstration — not an official government service.”**
- Never imply the prototype is hosted, approved, certified, or operated by AICTE or another government body unless this is verifiably true and authorised.
- Show `MOCK` / `DEMO` near simulated integrations and synthetic data. This label must persist in detail pages, exports, and status views—not only in a one-time toast.
- Avoid invented verified counts, fake testimonials, fabricated partner logos, and made-up service-level claims.

## 4. Application shell
- Compact top header with product identity, environment/prototype status, help/accessibility entry points, and signed-in role/institution context when available.
- Conventional primary navigation: Dashboard, Roster Intake, Reconciliation, Identity Review, Verification Requests, Reports/Audit, and Administration, filtered by permission. Do not show inaccessible modules as if available.
- Use breadcrumbs and descriptive page titles. Keep page actions close to the page title or relevant record.
- Navigation should be stable and predictable; avoid excessive floating buttons, decorative ticker strips, or carousel-like controls.
- Responsive navigation may collapse on narrow screens, but the active page and institution context must remain clear.

## 5. Page patterns
### Dashboard
Show actionable workload first: batches needing attention, unresolved reconciliation differences, identity cases awaiting review, and recent audit events. Every count must be computed from the current scoped dataset. For synthetic/demo fixtures, show a persistent demo label. Avoid decorative charts unless they answer a real operational question.

### Tables and lists
Use clear column headings, sensible column widths, row separators, sortable headers only when sorting works, search/filter controls that actually filter, pagination for long lists, and explicit no-results states. Keep row actions consistent. Do not truncate critical identity or status context without an accessible way to inspect it.

### Forms and imports
Use visible labels above fields, examples where formats are non-obvious, file constraints before upload, inline field errors, a summary of errors after submission, and confirmation before irreversible actions. Preserve row counts and make invalid rows inspectable; never imply failed rows were processed successfully.

### Identity review
Separate candidate signals from reviewer decisions. Display method/version, reason codes, relevant evidence references, and review state. Do not use “fraudster,” “duplicate confirmed,” or similarly conclusive labels based only on an algorithmic score. Require explicit human action and record rationale.

### Status language
Use plain language such as Draft, Queued, Processing, Completed, Needs attention, Pending review, Confirmed by reviewer, Rejected by reviewer, and Unable to determine. Use colour plus text (and, where useful, an icon); never use colour alone. “Verified” must identify what was verified and by which actual or mock source.

## 6. Interaction and accessibility requirements
- All interactive elements work, or are visibly disabled with a concise explanation. No decorative fake buttons.
- Keyboard navigation, logical focus order, visible focus indicators, semantic headings, proper labels, accessible names, and dialog focus management.
- Meet WCAG 2.2 AA contrast targets as a design goal; verify actual colour combinations rather than relying on intuition.
- Do not convey state by colour alone. Provide accessible error text and associate field errors with their fields.
- Respect reduced-motion preferences; motion should communicate state only and never be required to understand the workflow.
- Layouts must remain usable at 320 CSS pixels wide and at common desktop widths. Tables may use a contained horizontal scroll where necessary, without breaking the entire page.
- Use localised date/time/number formatting consistently, and make timezone assumptions explicit when they matter.

## 7. Data safety in the UI
- Enforce tenant and role permissions on the server; hiding a button is not authorization.
- Do not put sensitive student attributes in URLs, client analytics, console logs, toast messages, or unredacted error reports.
- Mask sensitive values by default where full display is not necessary; gate reveal/export actions by permission and audit them.
- Confirm high-impact actions and explain their consequences. Provide safe empty/error states without leaking cross-tenant record existence.
- Demo records and mock integration responses must be clearly marked. Never mix synthetic and live records without explicit provenance labels.

## 8. Components to implement consistently
Design tokens; app header; primary navigation; breadcrumbs; page heading/action bar; buttons (primary, secondary, danger); text/select/date/file fields; inline validation; alerts; status badges; filter bar; data table; pagination; empty/loading/error states; confirmation dialog; audit event row; demo/mock indicator. Prefer the existing framework's accessible primitives over custom interaction code.

## 9. Prohibited visual shortcuts
- Generic AI landing page with oversized slogan and gradient hero.
- Glass panels, neon outlines, glowing shadows, animated blobs, excessive gradient fills, or unnecessary motion.
- A large grid of rounded cards when a table or structured list is more useful.
- Emoji as the primary icon system, random icon styles, or inconsistent corner radii.
- Fake real-time data, random counters, fake verification seals, placeholder links that appear live, and buttons that do nothing.
- Copying another government portal pixel-for-pixel or using assets without permission.

## 10. UI review checklist
Before calling a screen done, verify:
- [ ] It follows the shared tokens and component patterns.
- [ ] It looks like a serious administrative service, not a generic AI/SaaS template.
- [ ] No unapproved official logo/seal or misleading endorsement is present.
- [ ] Synthetic data and mock integrations are visibly and persistently labelled.
- [ ] All shown controls work, or are disabled with an explanation.
- [ ] Search, filters, sorting, and pagination work as represented.
- [ ] Loading, empty, error, success, and permission-denied states are covered.
- [ ] Keyboard focus, labels, contrast, status text, and narrow-screen layout are checked.
- [ ] No sensitive identity data leaks through URLs, logs, errors, or client events.
- [ ] Screenshot review has been completed for dashboard, roster intake, reconciliation, identity review, and audit/report screens.
