"""Add errors column to staged_enrolments for row-level validation errors.

Revision ID: 0002_roster_intake_errors
Revises: 0001_initial_schema
Create Date: 2026-10-25

"""
from alembic import op
import sqlalchemy as sa

revision = "0002_roster_intake_errors"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "staged_enrolments",
        sa.Column("errors", sa.String(length=1024), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("staged_enrolments", "errors")
