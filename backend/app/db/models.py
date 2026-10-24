from sqlalchemy import Column, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint

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
    subject = Column(String(255), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["institution_id"], ["institutions.id"], name="fk_users_institution"),
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
    __tablename__ = "approved_intake_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(Integer, nullable=False)
    course_code = Column(String(64), nullable=False)
    academic_year = Column(String(32), nullable=False)
    approved_count = Column(Integer, nullable=False)
    source_ref = Column(String(255), nullable=False)
    effective_from = Column(DateTime, nullable=False)
    effective_to = Column(DateTime, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["institution_id"], ["institutions.id"], name="fk_sais_institution"),
    )


class SubmissionBatch(Base):
    __tablename__ = "submission_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(Integer, nullable=False)
    uploader_ref = Column(String(255), nullable=False)
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
    local_ref = Column(String(255), nullable=False)
    course_code = Column(String(64), nullable=False)
    academic_year = Column(String(32), nullable=False)
    seat_category = Column(String(64), nullable=False)
    entry_level = Column(String(64), nullable=False)
    identity_status = Column(String(64), nullable=False)
    validation_state = Column(String(64), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["batch_id"], ["submission_batches.id"], name="fk_se_batch"),
    )
