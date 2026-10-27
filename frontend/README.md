# PRAMAAN-AICTE Frontend

React 18 + TypeScript + Vite + Tailwind CSS v4 frontend for the PRAMAAN-AICTE prototype.

## Setup

```bash
npm install
cp .env.example .env   # sets VITE_API_PROXY_TARGET
```

## Development

```bash
npm run dev
```

Serves the app at http://localhost:5173.

## Production build

```bash
npm run build
npm run preview
```

## Tests

```bash
npm run test
```

## Backend integration

In development the Vite dev server proxies `/api` and `/health` to the backend, so the browser sees one origin and the session cookie stays first-party (`SameSite=Lax`). The proxy target defaults to `http://127.0.0.1:8002` and is set with `VITE_API_PROXY_TARGET` in `.env` (see `.env.example`). Start the backend on the same port:

```bash
# in backend/
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

Set `VITE_API_BASE_URL` only if the API is not reachable through the proxy; cross-origin cookie auth then also requires that origin in the backend's `CORS_ORIGINS`.

If the API cannot be reached, the screens show the failure with a retry control; they never fall back to sample numbers. A `401` returns the user to sign-in, `403` means the role lacks the action, and `404` on a batch means it belongs to another institution.

Authentication uses an `HttpOnly` cookie, so every request is sent with `credentials: "include"`; the cookie is never readable from JavaScript.

Requests used by the screens:

- `GET /api/v1/batches` — dashboard counts and the reconciliation batch selector
- `POST /api/v1/batches` — create batch
- `POST /api/v1/batches/{id}/validate` — upload & validate roster CSV (also re-validates a corrected file against the same batch)
- `POST /api/v1/batches/{id}/confirm` — confirm submission
- `GET /api/v1/reconciliation/snapshots` — approved snapshots for the selector
- `GET /api/v1/reconciliation/policies` — policy packages for the selector
- `POST /api/v1/batches/{id}/reconcile` — run reconciliation, returns the run and every row outcome
- `GET /api/v1/reconciliation/runs` — run history (optionally `?batch_id=`)
- `GET /api/v1/reconciliation/runs/{id}` — one run with row outcomes

Server-side authorization is the security boundary. Hiding navigation from a role is convenience only.

## Pages

- Sign in — local username and password; no external identity provider
- Dashboard — batch counts, status filters, search and pagination from `GET /batches`
- Roster Intake — sample CSV download, upload, row-level validation, correction and explicit confirmation
- Reconciliation — batch/snapshot/policy selectors, run, outcome table and run history
- Reports / Audit — recorded reconciliation runs and CSV exports of row outcomes
- Identity Review — a review-queue workspace with the case columns, search and status filters, and an empty state. No review API or matching service exists, so the queue is empty, the filters are disabled with a stated reason, and nothing is queued, scored or decided
- Verification Requests — a request workspace with the request columns, status filters and an empty state. No request API or adapter exists, so no request can be raised and the screen offers no create action; the proposed request lifecycle is shown as a labelled preview
- Administration — the signed-in account from the session, this institution's versioned configuration read from the real `/reconciliation/policies` and `/reconciliation/snapshots` endpoints (with loading, permission-denied, error and not-configured states), account capability labels, and a copyable CLI provisioning command

## Design notes

Off-white canvas, forest-green primary accent, white surfaces with thin
borders, a persistent desktop sidebar and disclosure navigation on narrow
screens. Only real API data or an explicit empty/error state is shown, and the
prototype disclaimers stay visible.
