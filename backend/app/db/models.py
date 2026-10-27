from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)

from app.db.base import Base


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    official_code = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False)

    __table_args__ = (UniqueConstraint("official_code", name="uq_institutions_official_code"),)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(Integer, nullable=False)
    # Local login identifier. `subject` remains the stable account reference
    # (it mirrors `username` for locally-created accounts).
    username = Column(String(255), nullable=False)
    # PBKDF2-HMAC-SHA256 encoded as `pbkdf2_sha256$<iterations>$<salt>$<hash>`.
    # Never returned by any endpoint.
    password_hash = Column(String(512), nullable=False)
    subject = Column(String(255), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["institution_id"], ["institutions.id"], name="fk_users_institution"),
        Index("uq_users_username", "username", unique=True),
    )


class AuthSession(Base):
    """Server-side session. Only the SHA-256 of the cookie value is stored,
    so a database read alone cannot be replayed as a login."""

    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_hash = Column(String(128), nullable=False)
    user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_auth_session_user"),
        Index("uq_auth_sessions_token_hash", "token_hash", unique=True),
    )


class UserRoleAssignment(Base):
    __tablename__ = "user_role_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    institution_id = Column(Integer, nullable=False)
    role = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_ura_user"),
        ForeignKeyConstraint(["institution_id"], ["institutions.id"], name="fk_ura_institution"),
    )


class ApprovedIntakeSnapshot(Base):
    """An approved institutional intake snapshot for one institution.

    Header only: the counts live in :class:`ApprovedIntakeEntry` so the whole
    snapshot can be made immutable as one unit. `version` is stable and unique
    per institution; approving a new snapshot marks the overlapping approved
    predecessor `SUPERSEDED` and points `superseded_by_id` at the successor, so
    history is superseded rather than deleted.
    """

    __tablename__ = "approved_intake_snapshots"

    STATUS_DRAFT = "DRAFT"
    STATUS_APPROVED = "APPROVED"
    STATUS_SUPERSEDED = "SUPERSEDED"
    STATUSES = (STATUS_DRAFT, STATUS_APPROVED, STATUS_SUPERSEDED)

    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(Integer, nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False)
    source_ref = Column(String(255), nullable=False)
    effective_from = Column(DateTime, nullable=False)
    effective_to = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(255), nullable=True)
    superseded_by_id = Column(Integer, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["institution_id"], ["institutions.id"], name="fk_sais_institution"),
        ForeignKeyConstraint(
            ["superseded_by_id"],
            ["approved_intake_snapshots.id"],
            name="fk_sais_superseded_by",
        ),
        UniqueConstraint("institution_id", "version", name="uq_snapshots_inst_version"),
        CheckConstraint(
            "status IN ('DRAFT','APPROVED','SUPERSEDED')",
            name="ck_snapshots_status",
        ),
    )


class ApprovedIntakeEntry(Base):
    """One approved capacity line inside a snapshot.

    Immutable with its snapshot; there is no update path once approved.
    """

    __tablename__ = "approved_intake_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, nullable=False)
    course_code = Column(String(64), nullable=False)
    academic_year = Column(String(32), nullable=False)
    seat_category = Column(String(64), nullable=False)
    approved_count = Column(Integer, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["snapshot_id"],
            ["approved_intake_snapshots.id"],
            name="fk_entry_snapshot",
        ),
        UniqueConstraint(
            "snapshot_id",
            "course_code",
            "academic_year",
            "seat_category",
            name="uq_entries_scope",
        ),
        CheckConstraint("approved_count >= 0", name="ck_entries_count_nonneg"),
    )


class ReconciliationPolicy(Base):
    """A versioned, deterministic reconciliation policy package.

    `rules` holds canonical JSON validated by `PolicyRules`. Editing a DRAFT in
    place is allowed; `ACTIVE` policies are immutable, so changing rules always
    means creating a new version rather than silently rewriting history.
    """

    __tablename__ = "reconciliation_policies"

    STATUS_DRAFT = "DRAFT"
    STATUS_ACTIVE = "ACTIVE"
    STATUSES = (STATUS_DRAFT, STATUS_ACTIVE)

    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(Integer, nullable=False)
    version = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(1024), nullable=True)
    status = Column(String(32), nullable=False)
    rules = Column(Text, nullable=False)
    rules_checksum = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False)
    created_by = Column(String(255), nullable=False)
    activated_at = Column(DateTime, nullable=True)
    activated_by = Column(String(255), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["institution_id"], ["institutions.id"], name="fk_policy_institution"),
        UniqueConstraint("institution_id", "version", name="uq_policies_inst_version"),
        CheckConstraint("status IN ('DRAFT','ACTIVE')", name="ck_policies_status"),
    )


class ReconciliationRun(Base):
    """One immutable reconciliation attempt over a batch.

    Runs are append-only: a new attempt gets a new row, so finished history is
    never overwritten. `digest` is null when the run failed.
    """

    __tablename__ = "reconciliation_runs"

    STATUS_SUCCEEDED = "SUCCEEDED"
    STATUS_FAILED = "FAILED"
    STATUSES = (STATUS_SUCCEEDED, STATUS_FAILED)

    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(Integer, nullable=False)
    batch_id = Column(Integer, nullable=False)
    run_number = Column(Integer, nullable=False)
    snapshot_id = Column(Integer, nullable=False)
    # Denormalised so a run stays explainable after its inputs are superseded.
    snapshot_version = Column(Integer, nullable=False)
    policy_id = Column(Integer, nullable=False)
    policy_version = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    triggered_by = Column(String(255), nullable=False)
    row_count = Column(Integer, nullable=False)
    digest = Column(String(64), nullable=True)
    totals = Column(Text, nullable=True)
    error_code = Column(String(64), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["institution_id"], ["institutions.id"], name="fk_run_institution"),
        ForeignKeyConstraint(["batch_id"], ["submission_batches.id"], name="fk_run_batch"),
        ForeignKeyConstraint(["snapshot_id"], ["approved_intake_snapshots.id"], name="fk_run_snapshot"),
        ForeignKeyConstraint(["policy_id"], ["reconciliation_policies.id"], name="fk_run_policy"),
        UniqueConstraint("batch_id", "run_number", name="uq_runs_batch_number"),
        CheckConstraint("status IN ('SUCCEEDED','FAILED')", name="ck_runs_status"),
        Index("ix_runs_institution_started", "institution_id", "started_at"),
    )


class ReconciliationResult(Base):
    """Row-level outcome for one staged row in one run.

    Carries only a non-sensitive reference and field-level reasons; it never
    stores identity attributes.
    """

    __tablename__ = "reconciliation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, nullable=False)
    row_number = Column(Integer, nullable=False)
    local_ref = Column(String(255), nullable=True)
    outcome = Column(String(32), nullable=False)
    reasons = Column(Text, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["run_id"], ["reconciliation_runs.id"], name="fk_result_run"),
        UniqueConstraint("run_id", "row_number", name="uq_results_run_row"),
        Index("ix_results_run_outcome", "run_id", "outcome"),
    )


class SubmissionBatch(Base):
    __tablename__ = "submission_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(Integer, nullable=False)
    uploader_ref = Column(String(255), nullable=False)
    academic_year = Column(String(32), nullable=False)
    # Name of the uploaded roster file, recorded once validation accepts it.
    # NULL for batches that have not been uploaded yet (or pre-0007 rows).
    source_filename = Column(String(255), nullable=True)
    checksum = Column(String(128), nullable=False)
    schema_version = Column(String(64), nullable=False)
    state = Column(String(32), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    created_at = Column(DateTime, nullable=False)
    submitted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["institution_id"], ["institutions.id"], name="fk_sb_institution"),
        UniqueConstraint("idempotency_key", name="uq_submission_batches_idempotency_key"),
    )


class StagedEnrolment(Base):
    __tablename__ = "staged_enrolments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(Integer, nullable=False)
    row_number = Column(Integer, nullable=False)
    # NULL when the row fails before a local_ref can be read. NULLs are distinct
    # in a unique index on both SQLite and PostgreSQL, so rows without a
    # reference never collide with each other.
    local_ref = Column(String(255), nullable=True)
    course_code = Column(String(64), nullable=False)
    academic_year = Column(String(32), nullable=False)
    seat_category = Column(String(64), nullable=False)
    entry_level = Column(String(64), nullable=False)
    identity_status = Column(String(64), nullable=False)
    validation_state = Column(String(64), nullable=False)
    errors = Column(String(1024), nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(["batch_id"], ["submission_batches.id"], name="fk_se_batch"),
        Index("uq_staged_enrolments_batch_row", "batch_id", "row_number", unique=True),
        # Only VALID rows participate: invalid rows (missing/duplicate
        # references) must still be staged so they stay inspectable, and every
        # valid row must carry its own reference.
        Index(
            "uq_staged_enrolments_batch_valid_local_ref",
            "batch_id",
            "local_ref",
            unique=True,
            sqlite_where=text("validation_state = 'VALID'"),
            postgresql_where=text("validation_state = 'VALID'"),
        ),
    )


class MatchCandidate(Base):
    """A synthetic match candidate flagged during reconciliation or linkage.

    A score is recorded but never used as the sole basis for an adverse outcome.
    The state machine tracks whether the candidate has been reviewed, assigned,
    or decided. Institution-scoped: a candidate can only belong to its home institution.
    """
    __tablename__ = "match_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(Integer, nullable=False)
    record_ref = Column(String(255), nullable=False)
    method = Column(String(64), nullable=False)
    version = Column(String(32), nullable=False)
    score = Column(Float, nullable=True)
    reasons = Column(Text, nullable=True)
    state = Column(String(32), nullable=False, default="PENDING_REVIEW")
    created_at = Column(DateTime, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, nullable=True)
    assigned_reviewer_id = Column(Integer, nullable=True)
    assigned_at = Column(DateTime, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["institution_id"], ["institutions.id"], name="fk_mc_institution"),
        Index("ix_mc_institution_state", "institution_id", "state"),
        Index("ix_mc_record_ref", "record_ref"),
    )


class ReviewerAssignment(Base):
    """An assignment of a reviewer to a match candidate.

    One reviewer may be assigned to many candidates, but a candidate is
    assigned at most one primary reviewer at a time. The assignment carries
    the assignment timestamp and the reviewer's institutional scope.
    """
    __tablename__ = "reviewer_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, nullable=False)
    reviewer_id = Column(Integer, nullable=False)
    assigned_at = Column(DateTime, nullable=False)
    status = Column(String(32), nullable=False, default="ACTIVE")
    reviewer_institution_id = Column(Integer, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["candidate_id"], ["match_candidates.id"], name="fk_ra_candidate"),
        ForeignKeyConstraint(["reviewer_id"], ["users.id"], name="fk_ra_reviewer"),
        ForeignKeyConstraint(["reviewer_institution_id"], ["institutions.id"], name="fk_ra_institution"),
        UniqueConstraint("candidate_id", name="uq_ra_candidate_one_reviewer"),
        Index("ix_ra_reviewer_load", "reviewer_institution_id", "status"),
    )


class AdjudicationCase(Base):
    """A case created when a reviewer assigns a candidate for adjudication.

    Carries the reviewer's rationale, the policy version in effect, and the
    timestamp trail. Corrections preserve prior history — the case row itself
    is never overwritten; a new revision is appended instead.
    """
    __tablename__ = "adjudication_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, nullable=False)
    reviewer_id = Column(Integer, nullable=False)
    policy_version = Column(Integer, nullable=False)
    outcome = Column(String(32), nullable=True)
    decision_reason_code = Column(String(64), nullable=True)
    decision_reason_text = Column(Text, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    confirmed_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    state = Column(String(32), nullable=False, default="PENDING_REVIEW")

    __table_args__ = (
        ForeignKeyConstraint(["candidate_id"], ["match_candidates.id"], name="fk_ac_candidate"),
        ForeignKeyConstraint(["reviewer_id"], ["users.id"], name="fk_ac_reviewer"),
        Index("ix_ac_candidate_state", "candidate_id", "state"),
        Index("ix_ac_reviewer_load", "reviewer_id", "state"),
    )


class DecisionHistory(Base):
    """Append-only audit trail for every decision made on a case.

    Every edit or state transition creates a new row, so the full decision
    history is never overwritten. The `parent_id` chain traces the evolution.
    """
    __tablename__ = "decision_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, nullable=False)
    outcome = Column(String(32), nullable=True)
    decision_reason_code = Column(String(64), nullable=True)
    decision_reason_text = Column(Text, nullable=True)
    changed_by = Column(Integer, nullable=False)
    changed_at = Column(DateTime, nullable=False)
    parent_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["case_id"], ["adjudication_cases.id"], name="fh_case"),
        Index("ix_dh_case_ts", "case_id", "changed_at"),
        Index("ix_dh_parent", "parent_id"),
    )
