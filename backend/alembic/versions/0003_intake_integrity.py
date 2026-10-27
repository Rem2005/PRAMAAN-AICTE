"""Intake integrity: unique indexes on staged rows and nullable local_ref.

`local_ref` becomes nullable so rows that fail before the reference can be read
are stored as NULL instead of a shared sentinel value. NULLs are distinct in a
unique index on both SQLite and PostgreSQL, so multiple unparseable rows in one
batch do not collide.

Constraints are created as unique indexes rather than table constraints because
SQLite cannot `ALTER TABLE ... ADD CONSTRAINT` at all, and Alembic's SQLite
batch mode could not add the composite constraints reliably.

Revision ID: 0003_intake_integrity
Revises: 0002_roster_intake_errors
Create Date: 2026-10-25

"""
from alembic import op
import sqlalchemy as sa

revision = "0003_intake_integrity"
down_revision = "0002_roster_intake_errors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("staged_enrolments") as batch_op:
        batch_op.alter_column(
            "local_ref",
            existing_type=sa.String(length=255),
            nullable=True,
        )

    op.create_index(
        "uq_staged_enrolments_batch_row",
        "staged_enrolments",
        ["batch_id", "row_number"],
        unique=True,
    )
    # Partial index: only VALID rows must have distinct references within a
    # batch. Invalid rows (missing or duplicate references) are staged on
    # purpose so the operator can inspect them, so a full unique index would
    # reject the very rows intake is required to keep.
    op.create_index(
        "uq_staged_enrolments_batch_valid_local_ref",
        "staged_enrolments",
        ["batch_id", "local_ref"],
        unique=True,
        sqlite_where=sa.text("validation_state = 'VALID'"),
        postgresql_where=sa.text("validation_state = 'VALID'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_staged_enrolments_batch_valid_local_ref", table_name="staged_enrolments"
    )
    op.drop_index("uq_staged_enrolments_batch_row", table_name="staged_enrolments")

    with op.batch_alter_table("staged_enrolments") as batch_op:
        batch_op.alter_column(
            "local_ref",
            existing_type=sa.String(length=255),
            nullable=False,
        )
