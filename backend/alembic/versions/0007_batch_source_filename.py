"""Record the uploaded roster filename on a submission batch.

The dashboard lists batches by file name, which until now was read, validated
and then discarded. The name is the operator-visible label of the file the
server actually parsed; it is not an identity attribute.

Revision ID: 0007_batch_source_filename
Revises: 0006_reconciliation
Create Date: 2026-10-26

"""
from alembic import op
import sqlalchemy as sa

revision = "0007_batch_source_filename"
down_revision = "0006_reconciliation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "submission_batches",
        sa.Column("source_filename", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("submission_batches", "source_filename")
