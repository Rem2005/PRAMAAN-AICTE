"""Add database models for identity review workflow.

Revision ID: 0008_identity_review_models
Revises: 0007_batch_source_filename
Create Date: 2026-10-27

"""

from alembic import op
import sqlalchemy as sa


revision = "0008_identity_review_models"
down_revision = "0007_batch_source_filename"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "match_candidates",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("record_ref", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("reasons", sa.Text(), nullable=True),
        sa.Column(
            "state", sa.String(length=32), nullable=False, server_default="PENDING_REVIEW"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("assigned_reviewer_id", sa.Integer(), nullable=True),
        sa.Column(
            "assigned_at", sa.DateTime(), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], name="fk_mc_institution"
        ),
        sa.Index("ix_mc_institution_state", "institution_id", "state"),
        sa.Index("ix_mc_record_ref", "record_ref"),
    )
    op.create_table(
        "reviewer_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reviewer_institution_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["match_candidates.id"], name="fk_ra_candidate"
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"], ["users.id"], name="fk_ra_reviewer"
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_institution_id"], ["institutions.id"],
            name="fk_ra_institution"
        ),
        sa.UniqueConstraint("candidate_id", name="uq_ra_candidate_one_reviewer"),
        sa.Index("ix_ra_reviewer_load", "reviewer_institution_id", "status"),
    )
    op.create_table(
        "adjudication_cases",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("decision_reason_code", sa.String(length=64), nullable=True),
        sa.Column("decision_reason_text", sa.Text(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["match_candidates.id"], name="fk_ac_candidate"
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"], ["users.id"], name="fk_ac_reviewer"
        ),
        sa.Index("ix_ac_candidate_state", "candidate_id", "state"),
        sa.Index("ix_ac_reviewer_load", "reviewer_id", "state"),
    )
    op.create_table(
        "decision_history",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("decision_reason_code", sa.String(length=64), nullable=True),
        sa.Column("decision_reason_text", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["case_id"], ["adjudication_cases.id"], name="fh_case"
        ),
        sa.Index("ix_dh_case_ts", "case_id", "changed_at"),
        sa.Index("ix_dh_parent", "parent_id"),
    )


def downgrade() -> None:
    op.drop_table("decision_history")
    op.drop_table("adjudication_cases")
    op.drop_table("reviewer_assignments")
    op.drop_table("match_candidates")