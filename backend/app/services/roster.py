"""Roster intake service: CSV parsing, validation, and batch management.

Submission policy (Milestone 5.1)
---------------------------------
Intake is all-or-nothing *per batch*: a batch can only be submitted when every
row validates. Invalid rows are never dropped or silently skipped - they are
staged with their errors, reported in the validation response, and stay
inspectable. The operator corrects the CSV and uploads it again (either to the
same batch, which re-validates and replaces the previous staged rows, or as a
new batch). No partial submission path exists: `confirm_batch` refuses a batch
that has any invalid row.
"""

import csv
import hashlib
import io
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Institution, StagedEnrolment, SubmissionBatch

# Canonical batch states (ADR-0007 / docs/architecture.md).
STATE_CREATED = "CREATED"
STATE_UPLOADED = "UPLOADED"
STATE_VALIDATING = "VALIDATING"
STATE_VALIDATED = "VALIDATED"
STATE_VALIDATION_FAILED = "VALIDATION_FAILED"
STATE_SUBMITTED_FOR_REVIEW = "SUBMITTED_FOR_REVIEW"

# The single authoritative transition table. Every state change in this module
# goes through `_transition`, so an illegal move fails loudly instead of being
# written to the database.
#
# `VALIDATION_FAILED -> UPLOADED` is the re-validation edge: the operator
# corrects the CSV and re-uploads it to the same batch. docs/architecture.md
# does not enumerate a re-validation edge, so this one is documented here and
# in docs/api-contracts.md.
VALID_TRANSITIONS: Dict[str, List[str]] = {
    STATE_CREATED: [STATE_UPLOADED],
    STATE_UPLOADED: [STATE_VALIDATING],
    STATE_VALIDATING: [STATE_VALIDATED, STATE_VALIDATION_FAILED],
    STATE_VALIDATED: [STATE_SUBMITTED_FOR_REVIEW],
    STATE_VALIDATION_FAILED: [STATE_UPLOADED],
    STATE_SUBMITTED_FOR_REVIEW: [],
}

# Required CSV columns for the roster intake contract.
REQUIRED_COLUMNS = [
    "local_ref",
    "course_code",
    "academic_year",
    "seat_category",
    "entry_level",
    "identity_status",
]

# Allowed optional columns. `apaar_id` is parsed so duplicates can be detected,
# but it is deliberately never persisted or returned: plaintext identity stays
# at the institution-side boundary (ADR-0002).
OPTIONAL_COLUMNS = ["apaar_id"]

VALID_ENTRY_LEVELS = {"FIRST_YEAR", "SECOND_YEAR", "THIRD_YEAR", "FOURTH_YEAR"}
VALID_SEAT_CATEGORIES = {"CAP_GENERAL", "CAP_OBC", "CAP_SC", "CAP_ST", "CAP_EWS"}
VALID_IDENTITY_STATUSES = {"DOMESTIC_APAAR", "INTERNATIONAL", "NRI"}


class RosterError(Exception):
    """Raised for roster intake validation or processing errors."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        super().__init__(message)
        self.code = code
        self.message = message


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _checksum_for(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _safe_filename(filename: str) -> str:
    """Store only the printable base name of the uploaded file.

    The name is shown back to the operator in the dashboard, so any directory
    component and control characters are dropped rather than echoed.
    """
    base = os.path.basename(filename.replace("\\", "/")).strip()
    base = "".join(ch for ch in base if ch.isprintable())
    return base[:255] or "upload.csv"


def _transition(batch: SubmissionBatch, to_state: str) -> None:
    """Move `batch` to `to_state`, or raise if the edge is not allowed."""
    allowed = VALID_TRANSITIONS.get(batch.state, [])
    if to_state not in allowed:
        raise RosterError(
            f"Batch {batch.id} cannot move from '{batch.state}' to '{to_state}'.",
            code="INVALID_STATE",
        )
    batch.state = to_state


def _validate_file(filename: str, content: bytes, max_size_mb: int) -> None:
    """Validate file extension, size, and encoding."""
    _, ext = os.path.splitext(filename)
    allowed = [e.strip() for e in settings.allowed_upload_extensions.split(",") if e.strip()]
    if ext.lower() not in [e.lower() for e in allowed]:
        raise RosterError(
            f"Unsupported file extension '{ext}'. Allowed: {', '.join(allowed)}",
            code="INVALID_FILE_TYPE",
        )

    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise RosterError(
            f"File too large: {len(content)} bytes. Maximum: {max_size_mb} MB.",
            code="FILE_TOO_LARGE",
        )

    if len(content) == 0:
        raise RosterError("File is empty.", code="EMPTY_FILE")

    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        raise RosterError(
            "File is not valid UTF-8 encoded text.", code="INVALID_ENCODING"
        )


def _parse_csv(content: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """Parse CSV content into headers and rows.

    Returns (headers, rows) where rows are dicts keyed by header name.
    Malformed rows (wrong column count) are captured as rows with an
    "__error__" key so they are still counted and reported.
    """
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    if not rows:
        raise RosterError("CSV file contains no data.", code="EMPTY_CSV")

    headers = [h.strip() for h in rows[0]]
    if not headers or all(h == "" for h in headers):
        raise RosterError("CSV file has no header row.", code="MISSING_HEADER")

    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise RosterError(
            f"Missing required columns: {', '.join(missing)}",
            code="MISSING_COLUMNS",
        )

    if len(headers) != len(set(headers)):
        dupes = [h for h in set(headers) if headers.count(h) > 1]
        raise RosterError(
            f"Duplicate column headers: {', '.join(dupes)}",
            code="DUPLICATE_COLUMNS",
        )

    data_rows: List[Dict[str, str]] = []
    for idx, row in enumerate(rows[1:], start=2):  # header is row 1
        if not row or all(cell.strip() == "" for cell in row):
            continue  # blank rows carry no data and are not counted
        if len(row) != len(headers):
            data_rows.append(
                {
                    "__row_number__": idx,
                    "__error__": f"Row has {len(row)} columns, expected {len(headers)}.",
                }
            )
            continue
        row_dict = {headers[i]: row[i].strip() for i in range(len(headers))}
        row_dict["__row_number__"] = idx
        data_rows.append(row_dict)

    return headers, data_rows


def _validate_row(
    row: Dict[str, str],
    seen_refs: set,
    seen_line_refs: set,
    batch_academic_year: str,
) -> List[str]:
    """Validate a single parsed row. Returns a list of error messages.

    Duplicate detection is scoped to the file being validated. It is not
    compared against rows staged in other batches: Phase 1 has no authoritative
    final-record store, and treating overlap with an *unreviewed* batch as an
    error would make a corrected replacement roster impossible to submit.
    """
    errors: List[str] = []
    row_number = row.get("__row_number__", 0)

    local_ref = row.get("local_ref", "").strip()
    course_code = row.get("course_code", "").strip()
    academic_year = row.get("academic_year", "").strip()
    seat_category = row.get("seat_category", "").strip()
    entry_level = row.get("entry_level", "").strip()
    identity_status = row.get("identity_status", "").strip()

    if not local_ref:
        errors.append(f"row {row_number}: local_ref is required")
    else:
        if local_ref in seen_refs:
            errors.append(f"row {row_number}: duplicate local_ref '{local_ref}'")
        seen_refs.add(local_ref)

    if not course_code:
        errors.append(f"row {row_number}: course_code is required")

    if not academic_year:
        errors.append(f"row {row_number}: academic_year is required")
    elif academic_year != batch_academic_year:
        errors.append(
            f"row {row_number}: academic_year '{academic_year}' does not match "
            f"batch academic year '{batch_academic_year}'"
        )

    if seat_category and seat_category not in VALID_SEAT_CATEGORIES:
        errors.append(
            f"row {row_number}: invalid seat_category '{seat_category}'. "
            f"Allowed: {', '.join(sorted(VALID_SEAT_CATEGORIES))}"
        )
    elif not seat_category:
        errors.append(f"row {row_number}: seat_category is required")

    if entry_level and entry_level not in VALID_ENTRY_LEVELS:
        errors.append(
            f"row {row_number}: invalid entry_level '{entry_level}'. "
            f"Allowed: {', '.join(sorted(VALID_ENTRY_LEVELS))}"
        )
    elif not entry_level:
        errors.append(f"row {row_number}: entry_level is required")

    if identity_status and identity_status not in VALID_IDENTITY_STATUSES:
        errors.append(
            f"row {row_number}: invalid identity_status '{identity_status}'. "
            f"Allowed: {', '.join(sorted(VALID_IDENTITY_STATUSES))}"
        )
    elif not identity_status:
        errors.append(f"row {row_number}: identity_status is required")

    # Exact duplicate rows (same values across all columns).
    row_signature = tuple(
        row.get(c, "").strip() for c in REQUIRED_COLUMNS + OPTIONAL_COLUMNS
    )
    if row_signature in seen_line_refs:
        errors.append(f"row {row_number}: duplicate row data")
    seen_line_refs.add(row_signature)

    return errors


def create_batch(
    db: Session,
    institution_id: int,
    academic_year: str,
    checksum: str,
    schema_version: str,
    idempotency_key: Optional[str] = None,
    uploader_ref: Optional[str] = None,
) -> SubmissionBatch:
    """Create a new submission batch in CREATED state.

    `idempotency_key` is optional. When the client supplies one and it is
    reused with an equivalent request, the original batch is returned instead
    of creating a duplicate. Reusing it with a different request is rejected.

    `uploader_ref` is the authenticated username (FR-02 records the uploader);
    callers must pass the session identity, never a client-supplied value.
    """
    institution = db.get(Institution, institution_id)
    if not institution:
        raise RosterError(
            f"Institution {institution_id} not found.", code="NOT_FOUND"
        )

    supplied_key = bool(idempotency_key)
    key = idempotency_key or str(uuid4())

    # A declared checksum is a claim about the file the operator intends to
    # upload; it is verified against the actual bytes during validation.
    declared_checksum = checksum or ""

    if supplied_key:
        existing = db.execute(
            select(SubmissionBatch).where(SubmissionBatch.idempotency_key == key)
        ).scalar_one_or_none()
        if existing is not None:
            _assert_equivalent_create(
                existing, institution_id, academic_year, schema_version
            )
            return existing

    batch = SubmissionBatch(
        institution_id=institution_id,
        uploader_ref=uploader_ref or "unknown",
        academic_year=academic_year,
        checksum=declared_checksum,
        schema_version=schema_version,
        state=STATE_CREATED,
        idempotency_key=key,
        created_at=_utc_now(),
    )
    db.add(batch)
    try:
        db.commit()
    except IntegrityError:
        # Lost the race on the unique idempotency key: return the winner when
        # the request is equivalent, otherwise report a genuine conflict.
        db.rollback()
        winner = db.execute(
            select(SubmissionBatch).where(SubmissionBatch.idempotency_key == key)
        ).scalar_one_or_none()
        if winner is None:
            raise RosterError(
                "Could not create batch: idempotency key conflict.",
                code="IDEMPOTENCY_CONFLICT",
            )
        _assert_equivalent_create(
            winner, institution_id, academic_year, schema_version
        )
        return winner
    db.refresh(batch)
    return batch


def _assert_equivalent_create(
    batch: SubmissionBatch,
    institution_id: int,
    academic_year: str,
    schema_version: str,
) -> None:
    """Reject reuse of an idempotency key for a different create request."""
    differs = (
        batch.institution_id != institution_id
        or batch.academic_year != academic_year
        or batch.schema_version != schema_version
    )
    if differs:
        raise RosterError(
            "Idempotency key was already used for a different batch request.",
            code="IDEMPOTENCY_CONFLICT",
        )


def _replay_validate_response(db: Session, batch: SubmissionBatch) -> Dict[str, Any]:
    """Rebuild the validation response for an already-VALIDATED batch.

    A batch is VALIDATED only when every staged row passed, so the replayed
    response has no errors and no duplicates.
    """
    staged = db.execute(
        select(StagedEnrolment)
        .where(StagedEnrolment.batch_id == batch.id)
        .order_by(StagedEnrolment.row_number)
    ).scalars().all()
    return {
        "batch_id": batch.id,
        "state": batch.state,
        "total_rows": len(staged),
        "valid_rows": len(staged),
        "invalid_rows": 0,
        "duplicate_rows": 0,
        "rows": [
            {
                "row_number": r.row_number,
                "local_ref": r.local_ref,
                "valid": True,
                "errors": [],
            }
            for r in staged
        ],
    }


def validate_and_stage(
    db: Session, batch_id: int, file_content: bytes, filename: str
) -> Dict[str, Any]:
    """Parse, validate, and stage enrolment rows for a batch.

    The whole operation runs in one transaction: either every row is staged
    and the batch reaches its terminal validation state, or nothing is written
    and the batch keeps its previous state. Re-validating a failed batch
    first deletes the previous attempt's staged rows so counts cannot go stale.
    """
    batch = db.get(SubmissionBatch, batch_id)
    if not batch:
        raise RosterError(f"Batch {batch_id} not found.", code="NOT_FOUND")

    if batch.state not in (
        STATE_CREATED,
        STATE_VALIDATION_FAILED,
        STATE_VALIDATED,
    ):
        raise RosterError(
            f"Batch {batch_id} is in state '{batch.state}', which cannot be validated.",
            code="INVALID_STATE",
        )

    _validate_file(filename, file_content, settings.max_upload_size_mb)
    source_filename = _safe_filename(filename)
    text = file_content.decode("utf-8")
    headers, data_rows = _parse_csv(text)

    if not data_rows:
        raise RosterError("CSV file contains no data rows.", code="EMPTY_CSV")

    # The checksum is always derived from the bytes actually uploaded; a value
    # declared at create time is only a claim until it is verified here.
    checksum = _checksum_for(file_content)

    if batch.state == STATE_VALIDATED:
        if batch.checksum == checksum:
            return _replay_validate_response(db, batch)
        raise RosterError(
            f"Batch {batch_id} is already validated against a different file. "
            "Create a new batch for the corrected CSV.",
            code="INVALID_STATE",
        )

    try:
        # VALIDATION_FAILED -> UPLOADED for re-validation, CREATED -> UPLOADED
        # on first upload; both then enter VALIDATING.
        _transition(batch, STATE_UPLOADED)
        _transition(batch, STATE_VALIDATING)
        db.flush()

        # Re-validation must not leave the previous attempt's rows behind.
        db.execute(
            delete(StagedEnrolment).where(StagedEnrolment.batch_id == batch_id)
        )
        batch.checksum = checksum
        batch.source_filename = source_filename

        seen_refs: set = set()
        seen_line_refs: set = set()
        row_results: List[Dict[str, Any]] = []
        valid_count = 0
        invalid_count = 0
        duplicate_count = 0

        for row in data_rows:
            row_number = row.get("__row_number__", 0)
            row_error = row.get("__error__")

            if row_error:
                errors = [row_error]
                local_ref: Optional[str] = None
                course_code = academic_year = seat_category = ""
                entry_level = identity_status = ""
            else:
                errors = _validate_row(
                    row, seen_refs, seen_line_refs, batch.academic_year
                )
                local_ref = row.get("local_ref", "").strip() or None
                course_code = row.get("course_code", "").strip()
                academic_year = row.get("academic_year", "").strip()
                seat_category = row.get("seat_category", "").strip()
                entry_level = row.get("entry_level", "").strip()
                identity_status = row.get("identity_status", "").strip()

                if any("duplicate" in e.lower() for e in errors):
                    duplicate_count += 1

            if errors:
                invalid_count += 1
                validation_state = "INVALID"
            else:
                valid_count += 1
                validation_state = "VALID"

            db.add(
                StagedEnrolment(
                    batch_id=batch_id,
                    row_number=row_number,
                    local_ref=local_ref,
                    course_code=course_code,
                    academic_year=academic_year,
                    seat_category=seat_category,
                    entry_level=entry_level,
                    identity_status=identity_status,
                    validation_state=validation_state,
                    errors="|".join(errors) if errors else None,
                )
            )

            row_results.append(
                {
                    "row_number": row_number,
                    "local_ref": local_ref,
                    "valid": not errors,
                    "errors": errors,
                }
            )

        _transition(
            batch,
            STATE_VALIDATION_FAILED if invalid_count > 0 else STATE_VALIDATED,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "batch_id": batch_id,
        "state": batch.state,
        "total_rows": len(data_rows),
        "valid_rows": valid_count,
        "invalid_rows": invalid_count,
        "duplicate_rows": duplicate_count,
        "rows": row_results,
    }


def _confirm_response(db: Session, batch: SubmissionBatch) -> Dict[str, Any]:
    """The confirmation outcome, derived from staged data only.

    `persisted_count` is the number of VALID staged rows this confirmation
    commits; it is recomputed from the database rather than accepted from the
    client, so a replayed response is always identical to the original.
    """
    persisted_count = db.execute(
        select(func.count())
        .select_from(StagedEnrolment)
        .where(
            StagedEnrolment.batch_id == batch.id,
            StagedEnrolment.validation_state == "VALID",
        )
    ).scalar_one()
    return {
        "batch_id": batch.id,
        "state": batch.state,
        "persisted_count": persisted_count,
    }


def confirm_batch(
    db: Session, batch_id: int, idempotency_key: str
) -> Dict[str, Any]:
    """Confirm a validated batch.

    All-or-nothing: only a batch whose every row validated can be confirmed.
    The operation is idempotent on the batch's idempotency key - a retried
    confirmation returns the original outcome unchanged, and reusing the key
    for a different request is rejected.
    """
    batch = db.get(SubmissionBatch, batch_id)
    if not batch:
        raise RosterError(f"Batch {batch_id} not found.", code="NOT_FOUND")

    if batch.idempotency_key != idempotency_key:
        if batch.state == STATE_SUBMITTED_FOR_REVIEW:
            raise RosterError(
                "Batch was already submitted with a different idempotency key.",
                code="IDEMPOTENCY_CONFLICT",
            )
        raise RosterError("Invalid idempotency key.", code="INVALID_IDEMPOTENCY_KEY")

    # Safe replay: same key, same request, already done - return the original
    # successful outcome instead of an error or a second side effect.
    if batch.state == STATE_SUBMITTED_FOR_REVIEW:
        return _confirm_response(db, batch)

    if batch.state == STATE_VALIDATION_FAILED:
        raise RosterError(
            "Batch has validation errors. Correct the CSV and re-upload it "
            "before confirming; invalid rows are never submitted.",
            code="VALIDATION_FAILED",
        )

    if batch.state != STATE_VALIDATED:
        raise RosterError(
            f"Batch {batch_id} is in state '{batch.state}', cannot confirm.",
            code="INVALID_STATE",
        )

    confirmed_at = _utc_now()
    result = db.execute(
        update(SubmissionBatch)
        .where(
            SubmissionBatch.id == batch_id,
            SubmissionBatch.state == STATE_VALIDATED,
        )
        .values(state=STATE_SUBMITTED_FOR_REVIEW, submitted_at=confirmed_at)
        .execution_options(synchronize_session=False)
    )

    if result.rowcount != 1:
        # Another caller moved this batch first. Re-read and replay the winner's
        # outcome when the key still matches; otherwise report the conflict.
        db.rollback()
        db.expire(batch)
        if (
            batch.state == STATE_SUBMITTED_FOR_REVIEW
            and batch.idempotency_key == idempotency_key
        ):
            return _confirm_response(db, batch)
        raise RosterError(
            f"Batch {batch_id} changed state while confirming.",
            code="INVALID_STATE",
        )

    db.commit()
    db.expire(batch)
    return _confirm_response(db, batch)


def list_batch_summaries(db: Session, institution_id: int) -> Dict[str, Any]:
    """List an institution's batches, newest first, with staged-row counts.

    Counts come from the staged rows themselves (not from a cached total), so
    the dashboard cannot show a record count that disagrees with the batch.
    """
    batches = (
        db.execute(
            select(SubmissionBatch)
            .where(SubmissionBatch.institution_id == institution_id)
            .order_by(SubmissionBatch.created_at.desc(), SubmissionBatch.id.desc())
        )
        .scalars()
        .all()
    )

    counts: Dict[int, Dict[str, int]] = {}
    if batches:
        rows = db.execute(
            select(
                StagedEnrolment.batch_id,
                StagedEnrolment.validation_state,
                func.count(),
            )
            .where(StagedEnrolment.batch_id.in_([batch.id for batch in batches]))
            .group_by(StagedEnrolment.batch_id, StagedEnrolment.validation_state)
        ).all()
        for batch_id, validation_state, count in rows:
            counts.setdefault(batch_id, {})[validation_state] = count

    items: List[Dict[str, Any]] = []
    totals = {"batches": len(batches), "total_rows": 0, "valid_rows": 0, "invalid_rows": 0}
    for batch in batches:
        by_state = counts.get(batch.id, {})
        valid_rows = by_state.get("VALID", 0)
        invalid_rows = by_state.get("INVALID", 0)
        total_rows = sum(by_state.values())
        totals["total_rows"] += total_rows
        totals["valid_rows"] += valid_rows
        totals["invalid_rows"] += invalid_rows
        items.append(
            {
                "batch_id": batch.id,
                "state": batch.state,
                "academic_year": batch.academic_year,
                "source_filename": batch.source_filename,
                "uploader_ref": batch.uploader_ref,
                "created_at": batch.created_at.isoformat() if batch.created_at else "",
                "total_rows": total_rows,
                "valid_rows": valid_rows,
                "invalid_rows": invalid_rows,
            }
        )

    return {"batches": items, "totals": totals}


def get_batch_summary(db: Session, batch_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve batch status and summary."""
    batch = db.get(SubmissionBatch, batch_id)
    if not batch:
        return None

    staged = db.execute(
        select(StagedEnrolment).where(StagedEnrolment.batch_id == batch_id)
    ).scalars().all()
    valid = [r for r in staged if r.validation_state == "VALID"]
    invalid = [r for r in staged if r.validation_state == "INVALID"]
    duplicate_count = sum(
        1 for r in invalid if r.errors and "duplicate" in r.errors.lower()
    )

    return {
        "batch_id": batch.id,
        "institution_id": batch.institution_id,
        "state": batch.state,
        "academic_year": batch.academic_year,
        "checksum": batch.checksum,
        "total_rows": len(staged),
        "valid_rows": len(valid),
        "invalid_rows": len(invalid),
        "duplicate_rows": duplicate_count,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
        "submitted_at": batch.submitted_at.isoformat() if batch.submitted_at else None,
    }
