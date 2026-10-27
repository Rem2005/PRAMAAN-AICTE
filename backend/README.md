# PRAMAAN-AICTE Backend

FastAPI backend foundation for the PRAMAAN-AICTE prototype.

## Setup

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

## Database migrations

The schema uses Alembic versioned migrations (`alembic/versions/`).

```bash
# Apply migrations (versioned; target is PostgreSQL per docs/architecture.md)
python -m alembic upgrade head

# Roll back the latest migration
python -m alembic downgrade -1

# Reset to an empty schema and re-apply
python -m alembic downgrade base
python -m alembic upgrade head
```

Local test executions use a temporary SQLite database configured through `DATABASE_URL`, which Alembic reads as well.

**PostgreSQL is the documented target but has not been verified.** Every test and local run so far used SQLite.

## API

All endpoints are prefixed `/api/v1`.

All `/api/v1/batches*` endpoints require a session. `401` = not signed in,
`403` = wrong role, or a body naming another institution; `404` = the batch
belongs to another institution; `409` = idempotency-key conflict.

Authentication:

- `POST /api/v1/auth/login` - username and password; sets an `HttpOnly`, `SameSite=Lax` session cookie
- `POST /api/v1/auth/logout` - revokes the session server-side and clears the cookie
- `GET /api/v1/auth/me` - current identity, or `authenticated: false`

Roster intake:

- `GET /health` - service liveness check
- `POST /api/v1/batches` - create an intake batch (`CREATED`). Optional client
  `idempotency_key`; `checksum` is optional because the server derives it from
  the uploaded bytes
- `POST /api/v1/batches/{id}/validate` - upload and validate a roster CSV;
  stages **every** row, valid or invalid
- `POST /api/v1/batches/{id}/confirm` - confirm a validated batch. All or
  nothing: any invalid row blocks confirmation. Replaying the same key returns
  the original outcome
- `GET /api/v1/batches` - list the session institution's batches with totals
- `GET /api/v1/batches/{id}` - read batch status and summary (same institution
  only)

Reconciliation (synchronous, deterministic, no external calls):

- `GET /api/v1/reconciliation/snapshots` - approved intake snapshots for the
  session institution, with entry counts
- `GET /api/v1/reconciliation/policies` - policy packages with their stored rules
- `POST /api/v1/batches/{id}/reconcile` - run against an approved snapshot and
  an active policy (both default to the latest). Accepts `?snapshot_id=` and
  `?policy_id=`. Each call appends a new run (with row outcomes and a digest)
- `GET /api/v1/reconciliation/runs` - run history, optionally `?batch_id=`
- `GET /api/v1/reconciliation/runs/{id}` - one run with every row outcome

A batch must be `VALIDATED` or `SUBMITTED_FOR_REVIEW` to be reconciled. An
outcome is a comparison result for review; it is never a penalty, a fraud
finding, or a legal conclusion.

## Running the server

```bash
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

Port 8002 is what `frontend/.env.example` proxies to; change
`VITE_API_PROXY_TARGET` if you run the API elsewhere.

## Provisioning accounts

Accounts are local; no external identity provider is integrated. The password
is read from the environment and never passed on the command line:

```bash
python -m app.cli create-institution --code INST001 --name "Demo Institution"
NEW_USER_PASSWORD='...' python -m app.cli create-user \
  --username operator1 --institution 1 --role INSTITUTION_DATA_OPERATOR
```

Repeat `--role` for additional roles. Available roles:
`INSTITUTION_DATA_OPERATOR`, `NODAL_OFFICER`, `AUDITOR`, `PLATFORM_ADMIN`.

## Synthetic demo data

Reconciliation needs an approved snapshot and an active policy. For a demo,
seed both (plus the institution and demo accounts) with **synthetic** data:

```bash
DEMO_PASSWORD='...' python -m app.cli seed-demo \
  --code SYN-DEMO-001 --name "Synthetic Demo Institute"
# or, for an existing institution:
python -m app.cli seed-demo --institution 1
```

It creates `operator1`, `nodal1` and `auditor1` (only when `DEMO_PASSWORD` is
set), an approved snapshot v1 and an active policy v1, idempotently. The
figures are demonstration data and are labelled `SYNTHETIC` — they are not an
official intake record or an approved AICTE rule set.

## Tests

```bash
python -m pytest -v
```

Tests run against a temporary SQLite database. `tests/conftest.py` lowers the password work factor for speed, while `test_auth.py::test_password_hash_uses_configured_work_factor` exercises the shipped default.
