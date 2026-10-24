# PRAMAAN-AICTE Backend

FastAPI backend foundation for the PRAMAAN-AICTE prototype.

## Setup

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

## Database migrations

The schema baseline uses Alembic versioned migrations (`alembic/versions/0001_initial_schema.py`).

```bash
# Apply migrations (versioned; target is PostgreSQL per docs/architecture.md)
python -m alembic upgrade head

# Roll back the latest migration
python -m alembic downgrade -1

# Reset to an empty schema and re-apply
python -m alembic downgrade base
python -m alembic upgrade head
```

Local test executions use a temporary SQLite database configured through `DATABASE_URL`.

## Tests

```bash
python -m pytest -v
```
