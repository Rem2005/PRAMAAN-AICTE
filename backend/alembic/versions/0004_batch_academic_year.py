"""Persist the batch academic period.

`POST /api/v1/batches` has always required `academic_year`, but
`SubmissionBatch` had no column for it, so the value supplied by the client was
accepted and then silently discarded. This migration adds the column so the
stored batch matches the documented contract.

The column carries a server default of '' so the migration stays safe on a
database that already contains batch rows (legacy rows read back as an empty
period rather than the migration failing); the application always supplies a
value, and the model declares the column as required.

Revision ID: 0004_batch_academic_year
Revises: 0003_intake_integrity
Create Date: 2026-10-25

"""
from alembic import op
import sqlalchemy as sa

revision = "0004_batch_academic_year"
down_revision = "0003_intake_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "submission_batches",
        sa.Column(
            "academic_year",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("''"),
        ),
    )


def downgrade() -> None:
    op.drop_column("submission_batches", "academic_year")
