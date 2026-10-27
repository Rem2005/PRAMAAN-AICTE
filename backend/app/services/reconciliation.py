"""Reconciliation engine: deterministic, transactional, history-preserving.

Given a submission batch, an approved intake snapshot and a reconciliation
policy package, this engine compares every staged roster row against the
approved entries and produces exactly one outcome per row plus a summary
digest.

Rules are deterministic (docs/PRD.md): same batch bytes + same snapshot
version + same policy version => identical outcomes and identical digest. No
fuzzy thresholds, no learned weights, no identity-linkage heuristics, and no
score-only adverse outcome (AGENTS.md directive 3).

Outcome vocabulary lives in `app.schemas.policy`. Capacity comparisons are
aggregate-only and are never a row outcome.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ApprovedIntakeEntry,
    ApprovedIntakeSnapshot,
    ReconciliationPolicy,
    ReconciliationResult,
    ReconciliationRun,
    StagedEnrolment,
    SubmissionBatch,
)
from app.schemas.policy import (
    CAPACITY_EXCEEDED,
    CAPACITY_MATCHED,
    CAPACITY_UNDERFILLED,
    OUTCOME_AMBIGUOUS,
    OUTCOME_DUPLICATE_CANDIDATE,
    OUTCOME_EXCLUDED_BY_POLICY,
    OUTCOME_FIELD_MISMATCH,
    OUTCOME_INVALID_INPUT,
    OUTCOME_MATCHED,
    OUTCOME_UNMATCHED,
    PolicyRules,
    normalise,
)

# Batch states a run may start from: a validated batch has staged every row,
# and a confirmed batch has the same staged rows plus the operator's explicit
# confirmation. Anything else has nothing complete to reconcile.
RECONCILABLE_STATES = ("VALIDATED", "SUBMITTED_FOR_REVIEW")


class ReconciliationError(Exception):
    """Raised when a run cannot be performed. Carries a safe, actionable code."""

    def __init__(self, message: str, code: str = "RECONCILIATION_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical(value: Optional[str], rule: str) -> Optional[str]:
    if value is None:
        return None
    trimmed = value.strip()
    if trimmed == "":
        # An empty spreadsheet cell is absence, not a value, so it must never
        # compare equal to a real value.
        return None
    return normalise(trimmed, rule)


def _row_key(
    values: Sequence[Optional[str]], fields: Sequence[str], policy: PolicyRules
) -> Tuple[Optional[str], ...]:
    return tuple(
        _canonical(value, policy.normalisation_for(field))
        for value, field in zip(values, fields)
    )


def _describe_key(fields: Sequence[str], key: Sequence[Optional[str]]) -> str:
    parts = [
        f"{field}={(value if value is not None else '∅')}"
        for field, value in zip(fields, key)
    ]
    return ", ".join(parts)


def _in_scope(scope, row: StagedEnrolment) -> bool:
    """Optional include-lists. A row outside scope is excluded, not failed."""

    if scope is None:
        return True
    if scope.course_codes and row.course_code not in scope.course_codes:
        return False
    if scope.seat_categories and row.seat_category not in scope.seat_categories:
        return False
    if scope.academic_years and row.academic_year not in scope.academic_years:
        return False
    return True


def _missing_required(row: StagedEnrolment, fields: Sequence[str]) -> List[str]:
    missing: List[str] = []
    for field in fields:
        value = getattr(row, field, None)
        if value is None or str(value).strip() == "":
            missing.append(field)
    return missing


def load_rules(policy: ReconciliationPolicy) -> PolicyRules:
    """Parse and re-validate the stored policy package.

    The stored JSON was validated when it was written; parsing it again here
    means a corrupted or hand-edited policy row fails loudly instead of being
    silently interpreted with different rules.
    """

    try:
        raw = json.loads(policy.rules)
    except (TypeError, ValueError) as exc:
        raise ReconciliationError(
            f"Policy {policy.id} rules are not valid JSON.", code="POLICY_INVALID"
        ) from exc
    try:
        return PolicyRules.model_validate(raw)
    except Exception as exc:  # pydantic ValidationError
        raise ReconciliationError(
            f"Policy {policy.id} rules failed validation: {exc}", code="POLICY_INVALID"
        ) from exc


def compute_run_number(db: Session, batch_id: int) -> int:
    """Next run number for a batch. Runs are append-only, never overwritten."""
    highest = db.execute(
        select(ReconciliationRun.run_number)
        .where(ReconciliationRun.batch_id == batch_id)
        .order_by(ReconciliationRun.run_number.desc())
        .limit(1)
    ).scalar_one_or_none()
    return int(highest or 0) + 1


def reconcile(
    db: Session,
    institution_id: int,
    batch_id: int,
    run_number: int,
    snapshot_id: int,
    snapshot_version: int,
    policy_id: int,
    policy_version: int,
    triggered_by: str,
) -> Dict[str, Any]:
    """Reconcile one batch and persist the run with its row-level outcomes."""

    batch = db.get(SubmissionBatch, batch_id)
    if not batch or batch.institution_id != institution_id:
        raise ReconciliationError(
            f"Batch {batch_id} not found.", code="NOT_FOUND"
        )
    if batch.state not in RECONCILABLE_STATES:
        raise ReconciliationError(
            f"Batch {batch_id} is in state '{batch.state}'. Reconcile a validated "
            f"or submitted batch ({', '.join(RECONCILABLE_STATES)}).",
            code="INVALID_STATE",
        )

    snapshot = db.get(ApprovedIntakeSnapshot, snapshot_id)
    if not snapshot or snapshot.institution_id != institution_id:
        raise ReconciliationError(
            f"Intake snapshot {snapshot_id} not found.", code="NOT_FOUND"
        )
    if snapshot.status != ApprovedIntakeSnapshot.STATUS_APPROVED:
        raise ReconciliationError(
            f"Snapshot {snapshot_id} is '{snapshot.status}'; only APPROVED "
            "snapshots can be reconciled against.",
            code="INVALID_SNAPSHOT_STATE",
        )

    policy = db.get(ReconciliationPolicy, policy_id)
    if not policy or policy.institution_id != institution_id:
        raise ReconciliationError(
            f"Policy {policy_id} not found.", code="NOT_FOUND"
        )
    if policy.status != ReconciliationPolicy.STATUS_ACTIVE:
        raise ReconciliationError(
            f"Policy {policy_id} is '{policy.status}'; only ACTIVE policies can "
            "be used to start a run.",
            code="INVALID_POLICY_STATE",
        )

    rules = load_rules(policy)

    staged_rows = (
        db.execute(
            select(StagedEnrolment)
            .where(StagedEnrolment.batch_id == batch_id)
            .order_by(StagedEnrolment.row_number)
        )
        .scalars()
        .all()
    )
    if not staged_rows:
        raise ReconciliationError(
            f"Batch {batch_id} has no staged rows to reconcile.",
            code="EMPTY_BATCH",
        )

    entries = (
        db.execute(
            select(ApprovedIntakeEntry)
            .where(ApprovedIntakeEntry.snapshot_id == snapshot_id)
            .order_by(ApprovedIntakeEntry.id)
        )
        .scalars()
        .all()
    )
    if not entries:
        raise ReconciliationError(
            f"Snapshot {snapshot_id} has no approved intake entries.",
            code="EMPTY_SNAPSHOT",
        )

    # Index approved entries by their normalised link key. A key with more than
    # one entry is genuinely ambiguous for the policy, not a resolved match.
    link_fields = rules.link_fields
    index: Dict[Tuple[Optional[str], ...], List[ApprovedIntakeEntry]] = {}
    for entry in entries:
        values = [getattr(entry, field, None) for field in link_fields]
        index.setdefault(_row_key(values, link_fields, rules), []).append(entry)

    outcome_counts: Dict[str, int] = {}
    outcomes: List[Dict[str, Any]] = []
    seen_duplicate_keys: set = set()

    for row in staged_rows:
        outcome = OUTCOME_INVALID_INPUT
        reasons: List[str] = []

        if not _in_scope(rules.scope, row):
            outcome = OUTCOME_EXCLUDED_BY_POLICY
            reasons.append("row is outside the policy's scope filter")
            outcomes.append(_outcome(row, outcome, reasons))
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
            continue

        missing = _missing_required(row, rules.required_fields)
        if missing:
            if rules.missing_value == "exclude":
                outcome = OUTCOME_EXCLUDED_BY_POLICY
                reasons.append(
                    "missing required field(s): " + ", ".join(missing)
                    + " (policy excludes rows with missing values)"
                )
            else:
                outcome = OUTCOME_INVALID_INPUT
                reasons.append("missing required field(s): " + ", ".join(missing))
            outcomes.append(_outcome(row, outcome, reasons))
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
            continue

        link_values = [getattr(row, field, None) for field in link_fields]
        key = _row_key(link_values, link_fields, rules)
        candidates = index.get(key, [])

        # Duplicate detection runs before match classification so a repeated
        # row is reported as a duplicate even when its entry is unambiguous.
        duplicate = False
        if rules.detect_duplicates and rules.duplicate_key_fields:
            duplicate_key = tuple(
                _canonical(getattr(row, field, None), "trim")
                for field in rules.duplicate_key_fields
            )
            if duplicate_key in seen_duplicate_keys:
                duplicate = True
            else:
                seen_duplicate_keys.add(duplicate_key)

        if not candidates:
            outcome = OUTCOME_UNMATCHED
            reasons.append(
                "no approved entry for " + _describe_key(link_fields, key)
            )
        elif duplicate:
            outcome = OUTCOME_DUPLICATE_CANDIDATE
            reasons.append(
                "row repeats an earlier row's "
                + "/".join(rules.duplicate_key_fields)
            )
        elif len(candidates) > 1:
            outcome = OUTCOME_AMBIGUOUS
            reasons.append(
                f"{len(candidates)} approved entries share "
                + _describe_key(link_fields, key)
                + "; a human must resolve which applies"
            )
        else:
            entry = candidates[0]
            mismatches: List[str] = []
            for field in rules.compare_fields:
                row_value = _canonical(
                    getattr(row, field, None), rules.normalisation_for(field)
                )
                entry_value = _canonical(
                    getattr(entry, field, None), rules.normalisation_for(field)
                )
                # Absent on both sides is not a disagreement; absent on one
                # side is, because the policy asked for that field.
                if row_value is None and entry_value is None:
                    continue
                if row_value != entry_value:
                    mismatches.append(field)
            if mismatches:
                outcome = OUTCOME_FIELD_MISMATCH
                reasons.append(
                    "field(s) differ from the approved entry: "
                    + ", ".join(mismatches)
                )
            else:
                outcome = OUTCOME_MATCHED

        outcomes.append(_outcome(row, outcome, reasons))
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

    capacity_totals, capacity_text = _capacity_summary(
        entries, outcomes, staged_rows, rules
    )

    digest = _digest(
        institution_id=institution_id,
        batch=batch,
        snapshot_version=snapshot_version,
        policy_version=policy_version,
        outcomes=outcomes,
    )

    now = _utc_now()
    run = ReconciliationRun(
        institution_id=institution_id,
        batch_id=batch_id,
        run_number=run_number,
        snapshot_id=snapshot_id,
        snapshot_version=snapshot_version,
        policy_id=policy_id,
        policy_version=policy_version,
        status=ReconciliationRun.STATUS_SUCCEEDED,
        started_at=now,
        finished_at=now,
        triggered_by=triggered_by,
        row_count=len(staged_rows),
        digest=digest,
        totals=capacity_text,
        error_code=None,
    )
    db.add(run)
    db.flush()

    for outcome in outcomes:
        db.add(
            ReconciliationResult(
                run_id=run.id,
                row_number=outcome["row_number"],
                local_ref=outcome["local_ref"],
                outcome=outcome["outcome"],
                reasons="; ".join(outcome["reasons"]),
            )
        )
    db.commit()
    db.refresh(run)

    return {
        "run": run,
        "outcomes": outcomes,
        "outcome_counts": outcome_counts,
        "capacity": capacity_totals,
    }


def _outcome(
    row: StagedEnrolment, outcome: str, reasons: List[str]
) -> Dict[str, Any]:
    return {
        "row_number": row.row_number,
        "local_ref": row.local_ref,
        "outcome": outcome,
        "reasons": reasons,
    }


def _capacity_summary(
    entries: Sequence[ApprovedIntakeEntry],
    outcomes: Sequence[Dict[str, Any]],
    staged_rows: Sequence[StagedEnrolment],
    rules: PolicyRules,
) -> Tuple[Dict[str, int], str]:
    """Compare matched volume against approved capacity, per entry.

    Charged rows are the ones that matched an approved entry; unmatched,
    mismatched, invalid and duplicate rows never consume capacity. This is a
    summary only — it never changes a row outcome.
    """

    counts: Dict[str, int] = {
        CAPACITY_MATCHED: 0,
        CAPACITY_UNDERFILLED: 0,
        CAPACITY_EXCEEDED: 0,
    }
    if not rules.check_capacity:
        return counts, "Capacity comparison disabled by policy"

    matched_rows = {
        outcome["row_number"]
        for outcome in outcomes
        if outcome["outcome"] == OUTCOME_MATCHED
    }
    by_row_number = {row.row_number: row for row in staged_rows}

    submitted: Dict[Tuple[str, str, str], int] = {}
    for row_number in matched_rows:
        row = by_row_number.get(row_number)
        if row is None:
            continue
        key = (
            (row.course_code or "").strip().upper(),
            (row.academic_year or "").strip().upper(),
            (row.seat_category or "").strip().upper(),
        )
        submitted[key] = submitted.get(key, 0) + 1

    for entry in entries:
        key = (
            (entry.course_code or "").strip().upper(),
            (entry.academic_year or "").strip().upper(),
            (entry.seat_category or "").strip().upper(),
        )
        actual = submitted.get(key, 0)
        approved = entry.approved_count
        if actual > approved:
            counts[CAPACITY_EXCEEDED] += 1
        elif actual < approved:
            counts[CAPACITY_UNDERFILLED] += 1
        else:
            counts[CAPACITY_MATCHED] += 1

    # Deliberately not worded like a row outcome: these counts are approved
    # capacity lines, not roster rows, and mixing the two reads as a
    # contradiction to anyone looking at matched rows alongside them.
    text = (
        f"Approved lines underfilled: {counts[CAPACITY_UNDERFILLED]}; "
        f"exactly filled: {counts[CAPACITY_MATCHED]}; "
        f"over capacity: {counts[CAPACITY_EXCEEDED]}"
    )
    return counts, text


def _digest(
    institution_id: int,
    batch: SubmissionBatch,
    snapshot_version: int,
    policy_version: int,
    outcomes: Sequence[Dict[str, Any]],
) -> str:
    """SHA-256 over the inputs and every row outcome.

    Same batch bytes, snapshot version and policy version must produce the same
    digest, which is what makes a run reproducible and comparable.
    """

    lines = [
        f"institution={institution_id}",
        f"batch={batch.id}",
        f"checksum={batch.checksum}",
        f"snapshot_version={snapshot_version}",
        f"policy_version={policy_version}",
    ]
    for outcome in sorted(outcomes, key=lambda item: item["row_number"]):
        lines.append(
            f"{outcome['row_number']}|{outcome['local_ref'] or ''}|"
            f"{outcome['outcome']}"
        )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def run_to_dict(
    run: ReconciliationRun, outcomes: Sequence[Dict[str, Any]]
) -> Dict[str, Any]:
    """Serialise a run plus its computed outcome counts."""

    counts: Dict[str, int] = {}
    for outcome in outcomes:
        key = outcome["outcome"]
        counts[key] = counts.get(key, 0) + 1

    return {
        "run_id": run.id,
        "batch_id": run.batch_id,
        "run_number": run.run_number,
        "snapshot_id": run.snapshot_id,
        "snapshot_version": run.snapshot_version,
        "policy_id": run.policy_id,
        "policy_version": run.policy_version,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "triggered_by": run.triggered_by,
        "row_count": run.row_count,
        "digest": run.digest,
        "totals": run.totals,
        "error_code": run.error_code,
        "outcome_counts": counts,
    }


def load_outcomes(db: Session, run_id: int) -> List[Dict[str, Any]]:
    rows = (
        db.execute(
            select(ReconciliationResult)
            .where(ReconciliationResult.run_id == run_id)
            .order_by(ReconciliationResult.row_number)
        )
        .scalars()
        .all()
    )
    return [
        {
            "row_number": row.row_number,
            "local_ref": row.local_ref,
            "outcome": row.outcome,
            "reasons": [part for part in row.reasons.split("; ") if part],
        }
        for row in rows
    ]
