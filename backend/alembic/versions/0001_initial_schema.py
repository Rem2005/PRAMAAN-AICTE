"""Initial schema baseline for PRAMAAN-AICTE.

Creates the minimal baseline schema consistent with docs/data-model.md for the
next planned milestones (intake, reconciliation, linkage, adjudication).

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-24

"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "institutions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("official_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("official_code", name="uq_institutions_official_code"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], name="fk_users_institution"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_role_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_ura_user"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], name="fk_ura_institution"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "approved_intake_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("course_code", sa.String(length=64), nullable=False),
        sa.Column("academic_year", sa.String(length=32), nullable=False),
        sa.Column("approved_count", sa.Integer(), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=False),
        sa.Column("effective_from", sa.DateTime(), nullable=False),
        sa.Column("effective_to", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], name="fk_sais_institution"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "submission_batches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("uploader_ref", sa.String(length=255), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], name="fk_sb_institution"),
        sa.UniqueConstraint("idempotency_key", name="uq_submission_batches_idempotency_key"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "staged_enrolments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("local_ref", sa.String(length=255), nullable=False),
        sa.Column("course_code", sa.String(length=64), nullable=False),
        sa.Column("academic_year", sa.String(length=32), nullable=False),
        sa.Column("seat_category", sa.String(length=64), nullable=False),
        sa.Column("entry_level", sa.String(length=64), nullable=False),
        sa.Column("identity_status", sa.String(length=64), nullable=False),
        sa.Column("validation_state", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["submission_batches.id"], name="fk_se_batch"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("staged_enrolments")
    op.drop_table("submission_batches")
    op.drop_table("approved_intake_snapshots")
    op.drop_table("user_role_assignments")
    op.drop_table("users")
    op.drop_table("institutions")
