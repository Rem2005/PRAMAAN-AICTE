"""Reconciliation: snapshot header/entries, policy packages, runs, results.

`approved_intake_snapshots` previously stored one capacity line per row, which
made "this snapshot is immutable once approved" impossible to express. It is
rebuilt as a header with explicit version/status/provenance and the counts move
to `approved_intake_entries`.

Any rows already present are carried across: one header (version 1) per
institution plus one entry per former row, so nothing is discarded.

Revision ID: 0006_reconciliation
Revises: 0005_auth_sessions
Create Date: 2026-10-25

"""
from alembic import op
import sqlalchemy as sa

revision = "0006_reconciliation"
down_revision = "0005_auth_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- Carry existing snapshot rows across before the rebuild ------------
    conn = op.get_bind()
    legacy = conn.execute(
        sa.text(
            "SELECT id, institution_id, course_code, academic_year, "
            "approved_count, source_ref, effective_from, effective_to "
            "FROM approved_intake_snapshots"
        )
    ).fetchall()

    op.drop_table("approved_intake_snapshots")
    op.create_table(
        "approved_intake_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=False),
        sa.Column("effective_from", sa.DateTime(), nullable=False),
        sa.Column("effective_to", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("superseded_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], name="fk_sais_institution"
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"],
            ["approved_intake_snapshots.id"],
            name="fk_sais_superseded_by",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "institution_id", "version", name="uq_snapshots_inst_version"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','APPROVED','SUPERSEDED')", name="ck_snapshots_status"
        ),
    )

    # ---- Entries -----------------------------------------------------------
    op.create_table(
        "approved_intake_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("course_code", sa.String(length=64), nullable=False),
        sa.Column("academic_year", sa.String(length=32), nullable=False),
        sa.Column("seat_category", sa.String(length=64), nullable=False),
        sa.Column("approved_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"], ["approved_intake_snapshots.id"], name="fk_entry_snapshot"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "course_code",
            "academic_year",
            "seat_category",
            name="uq_entries_scope",
        ),
        sa.CheckConstraint("approved_count >= 0", name="ck_entries_count_nonneg"),
    )

    if legacy:
        by_institution = {}
        for row in legacy:
            by_institution.setdefault(row[1], []).append(row)
        for institution_id, rows in by_institution.items():
            first = rows[0]
            conn.execute(
                sa.text(
                    "INSERT INTO approved_intake_snapshots "
                    "(institution_id, version, status, source_ref, effective_from, "
                    " effective_to, created_at, approved_at, approved_by) "
                    "VALUES (:inst, 1, 'APPROVED', :src, :eff_from, :eff_to, "
                    " :now, :now, 'migration-0006')"
                ),
                {
                    "inst": institution_id,
                    "src": first[5],
                    "eff_from": first[6],
                    "eff_to": first[7],
                    "now": first[6],
                },
            )
            snapshot_id = conn.execute(
                sa.text(
                    "SELECT id FROM approved_intake_snapshots "
                    "WHERE institution_id = :inst AND version = 1"
                ),
                {"inst": institution_id},
            ).scalar()
            for row in rows:
                conn.execute(
                    sa.text(
                        "INSERT INTO approved_intake_entries "
                        "(snapshot_id, course_code, academic_year, seat_category, "
                        " approved_count) "
                        "VALUES (:snap, :course, :year, 'CAP_GENERAL', :count)"
                    ),
                    {
                        "snap": snapshot_id,
                        "course": row[2],
                        "year": row[3],
                        "count": row[4],
                    },
                )

    # ---- Policy packages ---------------------------------------------------
    op.create_table(
        "reconciliation_policies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rules", sa.Text(), nullable=False),
        sa.Column("rules_checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("activated_by", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], name="fk_policy_institution"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "institution_id", "version", name="uq_policies_inst_version"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','ACTIVE')", name="ck_policies_status"
        ),
    )

    # ---- Runs --------------------------------------------------------------
    op.create_table(
        "reconciliation_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_version", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("triggered_by", sa.String(length=255), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("digest", sa.String(length=64), nullable=True),
        sa.Column("totals", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], name="fk_run_institution"
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"], ["submission_batches.id"], name="fk_run_batch"
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["approved_intake_snapshots.id"],
            name="fk_run_snapshot",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["reconciliation_policies.id"], name="fk_run_policy"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id", "run_number", name="uq_runs_batch_number"),
        sa.CheckConstraint(
            "status IN ('SUCCEEDED','FAILED')", name="ck_runs_status"
        ),
    )
    op.create_index(
        "ix_runs_institution_started",
        "reconciliation_runs",
        ["institution_id", "started_at"],
    )

    # ---- Row outcomes ------------------------------------------------------
    op.create_table(
        "reconciliation_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("local_ref", sa.String(length=255), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("reasons", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["reconciliation_runs.id"], name="fk_result_run"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "row_number", name="uq_results_run_row"),
    )
    op.create_index(
        "ix_results_run_outcome",
        "reconciliation_results",
        ["run_id", "outcome"],
    )


def downgrade() -> None:
    # Read entry data first: the collapse below needs it, and it must not be
    # queried after the table is dropped.
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT e.snapshot_id, s.institution_id, e.course_code, "
            "e.academic_year, e.approved_count, s.source_ref, "
            "s.effective_from, s.effective_to "
            "FROM approved_intake_entries e "
            "JOIN approved_intake_snapshots s ON s.id = e.snapshot_id"
        )
    ).fetchall()

    op.drop_index("ix_results_run_outcome", table_name="reconciliation_results")
    op.drop_table("reconciliation_results")
    op.drop_index("ix_runs_institution_started", table_name="reconciliation_runs")
    op.drop_table("reconciliation_runs")
    op.drop_table("reconciliation_policies")
    op.drop_table("approved_intake_entries")

    op.drop_table("approved_intake_snapshots")
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
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], name="fk_sais_institution"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for row in rows:
        conn.execute(
            sa.text(
                "INSERT INTO approved_intake_snapshots "
                "(institution_id, course_code, academic_year, approved_count, "
                " source_ref, effective_from, effective_to) "
                "VALUES (:inst, :course, :year, :count, :src, :eff_from, :eff_to)"
            ),
            {
                "inst": row[1],
                "course": row[2],
                "year": row[3],
                "count": row[4],
                "src": row[5],
                "eff_from": row[6],
                "eff_to": row[7],
            },
        )
