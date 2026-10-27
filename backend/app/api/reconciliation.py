"""Reconciliation API: approved snapshots, policy packages, runs, outcomes, and identity review.

All reads are institution-scoped from the session. A batch, snapshot, policy
or run belonging to another institution reports 404 rather than 403 so the
response never confirms that another institution's record exists.

The reconciliation itself is synchronous and deterministic; there is no
background job or external integration behind this endpoint (AGENTS.md
directive 13).
"""

import json
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_scoped_batch, require_roles
from app.db.models import (
    ApprovedIntakeEntry,
    ApprovedIntakeSnapshot,
    MatchCandidate,
    ReviewerAssignment,
    AdjudicationCase,
    DecisionHistory,
    ReconciliationPolicy,
    ReconciliationRun,
    SubmissionBatch,
)
from app.db.session import get_db
from app.schemas.policy import (
    MatchCandidateOut,
    MatchCandidateListResponse,
    MatchCandidateSearch,
    ReviewerAssignmentOut,
    ReviewerAssignmentCreate,
    ReviewerAssignmentListResponse,
    AdjudicationCaseOut,
    AdjudicationCaseCreate,
    AdjudicationCaseListResponse,
    DecisionHistoryOut,
    DecisionHistoryListResponse,
    DecisionCreate,
)
from app.services.auth import (
    ROLE_AUDITOR,
    ROLE_NODAL,
    ROLE_OPERATOR,
    AuthContext,
)
from app.services.reconciliation import (
    ReconciliationError,
    compute_run_number,
    load_outcomes,
    reconcile,
    run_to_dict,
)

router = APIRouter(prefix="/api/v1", tags=["reconciliation"])

# Anyone who works with batches may read reconciliation evidence. Starting a
# run is limited to the roles that own intake and review.
READ_ROLES = (ROLE_OPERATOR, ROLE_NODAL, ROLE_AUDITOR)
RUN_ROLES = (ROLE_OPERATOR, ROLE_NODAL)

_IDENTITY_REVIEW_ROLES = (ROLE_OPERATOR, ROLE_NODAL, "IDENTITY_REVIEW_OFFICER")
_IDENTITY_REVIEW_OFFICER_ONLY = ("IDENTITY_REVIEW_OFFICER",)

_ERROR_STATUS = {
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "INVALID_STATE": status.HTTP_400_BAD_REQUEST,
    "INVALID_SNAPSHOT_STATE": status.HTTP_400_BAD_REQUEST,
    "INVALID_POLICY_STATE": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "EMPTY_BATCH": status.HTTP_400_BAD_REQUEST,
    "EMPTY_SNAPSHOT": status.HTTP_400_BAD_REQUEST,
    "POLICY_INVALID": status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def _error_to_http(exc: ReconciliationError) -> HTTPException:
    return HTTPException(
        status_code=_ERROR_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail=exc.message,
    )


def _iso(value) -> Optional[str]:
    return value.isoformat() if value else None


def _batch_fields(db: Session, batch_id: int) -> dict:
    batch = db.get(SubmissionBatch, batch_id)
    if batch is None:
        return {"source_filename": None, "academic_year": None, "batch_state": None}
    return {
        "source_filename": batch.source_filename,
        "academic_year": batch.academic_year,
        "batch_state": batch.state,
    }


def _run_payload(db: Session, run: ReconciliationRun, outcomes: List[dict]) -> dict:
    payload = run_to_dict(run, outcomes)
    payload.update(_batch_fields(db, run.batch_id))
    return payload


@router.get("/reconciliation/snapshots", response_model=dict)
def list_snapshots(
    auth: AuthContext = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> Any:
    """Approved-intake snapshots for the session institution, newest first."""
    snapshots = (
        db.execute(
            select(ApprovedIntakeSnapshot)
            .where(ApprovedIntakeSnapshot.institution_id == auth.institution_id)
            .order_by(
                ApprovedIntakeSnapshot.version.desc(),
                ApprovedIntakeSnapshot.id.desc(),
            )
        )
        .scalars()
        .all()
    )

    counts = {}
    if snapshots:
        counts = dict(
            db.execute(
                select(
                    ApprovedIntakeEntry.snapshot_id,
                    func.count(),
                )
                .where(
                    ApprovedIntakeEntry.snapshot_id.in_(
                        [snapshot.id for snapshot in snapshots]
                    )
                )
                .group_by(ApprovedIntakeEntry.snapshot_id)
            )
            .all()
        )

    return {
        "snapshots": [
            {
                "snapshot_id": snapshot.id,
                "version": snapshot.version,
                "status": snapshot.status,
                "source_ref": snapshot.source_ref,
                "created_at": _iso(snapshot.created_at) or "",
                "approved_at": _iso(snapshot.approved_at),
                "approved_by": snapshot.approved_by,
                "entry_count": counts.get(snapshot.id, 0),
            }
            for snapshot in snapshots
        ]
    }


@router.get("/reconciliation/policies", response_model=dict)
def list_policies(
    auth: AuthContext = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> Any:
    """Policy packages for the session institution, newest version first."""
    policies = (
        db.execute(
            select(ReconciliationPolicy)
            .where(ReconciliationPolicy.institution_id == auth.institution_id)
            .order_by(
                ReconciliationPolicy.version.desc(), ReconciliationPolicy.id.desc()
            )
        )
        .scalars()
        .all()
    )

    response = []
    for policy in policies:
        try:
            rules = json.loads(policy.rules)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Policy {policy.id} (version {policy.version}) has unreadable "
                    "rules. Repair the policy package before running a reconciliation."
                ),
            ) from exc
        response.append(
            {
                "policy_id": policy.id,
                "version": policy.version,
                "name": policy.name,
                "description": policy.description,
                "status": policy.status,
                "rules": rules,
                "rules_checksum": policy.rules_checksum,
                "created_at": _iso(policy.created_at) or "",
                "activated_at": _iso(policy.activated_at),
            }
        )
    return {"policies": response}


@router.post(
    "/batches/{batch_id}/reconcile",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def reconcile_batch(
    batch_id: int,
    snapshot_id: Optional[int] = Query(
        None, gt=0, description="Approved snapshot; defaults to the latest approved"
    ),
    policy_id: Optional[int] = Query(
        None, gt=0, description="Policy package; defaults to the latest active"
    ),
    auth: AuthContext = Depends(require_roles(*RUN_ROLES)),
    db: Session = Depends(get_db),
) -> Any:
    """Run deterministic reconciliation and return the persisted run.

    The run is synchronous: when this returns, the run and every row outcome
    are committed. Each call appends a new run, so previous results stay
    inspectable.
    """
    batch = get_scoped_batch(db, batch_id, auth)

    snapshot_query = select(ApprovedIntakeSnapshot).where(
        ApprovedIntakeSnapshot.institution_id == auth.institution_id,
        ApprovedIntakeSnapshot.status == ApprovedIntakeSnapshot.STATUS_APPROVED,
    )
    if snapshot_id is not None:
        snapshot_query = snapshot_query.where(
            ApprovedIntakeSnapshot.id == snapshot_id
        )
    snapshot = (
        db.execute(
            snapshot_query.order_by(ApprovedIntakeSnapshot.version.desc()).limit(1)
        )
        .scalars()
        .first()
    )
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No approved intake snapshot is available for this institution. "
            "Reconciliation needs an approved snapshot to compare against.",
        )

    policy_query = select(ReconciliationPolicy).where(
        ReconciliationPolicy.institution_id == auth.institution_id,
        ReconciliationPolicy.status == ReconciliationPolicy.STATUS_ACTIVE,
    )
    if policy_id is not None:
        policy_query = policy_query.where(ReconciliationPolicy.id == policy_id)
    policy = (
        db.execute(
            policy_query.order_by(ReconciliationPolicy.version.desc()).limit(1)
        )
        .scalars()
        .first()
    )
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active reconciliation policy is available for this institution. "
            "Reconciliation needs an active policy package.",
        )

    try:
        result = reconcile(
            db=db,
            institution_id=auth.institution_id,
            batch_id=batch_id,
            run_number=compute_run_number(db, batch.id),
            snapshot_id=snapshot.id,
            snapshot_version=snapshot.version,
            policy_id=policy.id,
            policy_version=policy.version,
            triggered_by=auth.username,
        )
    except ReconciliationError as exc:
        raise _error_to_http(exc) from exc

    payload = _run_payload(db, result["run"], result["outcomes"])
    payload["outcomes"] = result["outcomes"]
    return payload


@router.get("/reconciliation/runs", response_model=dict)
def list_runs(
    batch_id: Optional[int] = Query(None, gt=0),
    limit: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> Any:
    """Reconciliation history for the session institution, newest first."""
    query = select(ReconciliationRun).where(
        ReconciliationRun.institution_id == auth.institution_id
    )
    if batch_id is not None:
        from app.api.deps import get_scoped_batch as _gcb
        _gcb(db, batch_id, auth)
        query = query.where(ReconciliationRun.batch_id == batch_id)

    runs = (
        db.execute(
            query.order_by(
                ReconciliationRun.started_at.desc(), ReconciliationRun.id.desc()
            ).limit(limit)
        )
        .scalars()
        .all()
    )

    payloads = []
    for run in runs:
        outcomes = load_outcomes(db, run.id)
        payloads.append(_run_payload(db, run, outcomes))
    return {"runs": payloads}


@router.get("/reconciliation/runs/{run_id}", response_model=dict)
def read_run(
    run_id: int,
    auth: AuthContext = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> Any:
    """One run with every row-level outcome, in row order."""
    run = db.get(ReconciliationRun, run_id)
    if run is None or run.institution_id != auth.institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reconciliation run {run_id} not found.",
        )
    outcomes = load_outcomes(db, run.id)
    payload = _run_payload(db, run, outcomes)
    payload["outcomes"] = outcomes
    return payload


# ---- Identity Review Endpoints ----

@router.get(
    "/identity-review/candidates",
    response_model=MatchCandidateListResponse,
)
def list_candidates(
    auth: AuthContext = Depends(require_roles(*_IDENTITY_REVIEW_ROLES)),
    db: Session = Depends(get_db),
    query: Optional[str] = Query(None, description="Search against record_ref"),
    state: Optional[str] = Query(None, description="Filter by state"),
    method: Optional[str] = Query(None, description="Filter by method"),
) -> Any:
    """List match candidates for the session institution.

    Candidates are synthetic records flagged during reconciliation or linkage.
    A score is recorded but never used as the sole basis for an adverse outcome.
    """
    db_query = select(MatchCandidate).where(
        MatchCandidate.institution_id == auth.institution_id
    )

    if query:
        db_query = db_query.where(MatchCandidate.record_ref.contains(query))
    if state:
        db_query = db_query.where(MatchCandidate.state == state)
    if method:
        db_query = db_query.where(MatchCandidate.method == method)

    candidates = db.execute(db_query.order_by(MatchCandidate.created_at.desc())).scalars().all()

    return {
        "candidates": [
            {
                "id": c.id,
                "institution_id": c.institution_id,
                "record_ref": c.record_ref,
                "method": c.method,
                "version": c.version,
                "score": c.score,
                "reasons": c.reasons.split("; ") if c.reasons else None,
                "state": c.state,
                "created_at": c.created_at.isoformat() if c.created_at else "",
                "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
                "reviewed_by": c.reviewed_by,
                "assigned_reviewer_id": c.assigned_reviewer_id,
                "assigned_at": c.assigned_at.isoformat() if c.assigned_at else None,
            }
            for c in candidates
        ]
    }


@router.get(
    "/identity-review/candidates/{candidate_id}",
    response_model=MatchCandidateOut,
)
def get_candidate(
    candidate_id: int,
    auth: AuthContext = Depends(require_roles(*_IDENTITY_REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> Any:
    """Get a single match candidate by ID."""
    candidate = db.get(MatchCandidate, candidate_id)
    if candidate is None or candidate.institution_id != auth.institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match candidate {candidate_id} not found.",
        )
    return {
        "id": candidate.id,
        "institution_id": candidate.institution_id,
        "record_ref": candidate.record_ref,
        "method": candidate.method,
        "version": candidate.version,
        "score": candidate.score,
        "reasons": candidate.reasons.split("; ") if candidate.reasons else None,
        "state": candidate.state,
        "created_at": candidate.created_at.isoformat() if candidate.created_at else "",
        "reviewed_at": candidate.reviewed_at.isoformat() if candidate.reviewed_at else None,
        "reviewed_by": candidate.reviewed_by,
        "assigned_reviewer_id": candidate.assigned_reviewer_id,
        "assigned_at": candidate.assigned_at.isoformat() if candidate.assigned_at else None,
    }


@router.post(
    "/identity-review/candidates/{candidate_id}/assign-reviewer",
    response_model=ReviewerAssignmentOut,
)
def assign_reviewer(
    candidate_id: int,
    payload: ReviewerAssignmentCreate,
    auth: AuthContext = Depends(require_roles(*_IDENTITY_REVIEW_OFFICER_ONLY)),
    db: Session = Depends(get_db),
) -> Any:
    """Assign a reviewer to a match candidate.

    Only IDENTITY_REVIEW_OFFICER role can assign reviewers. The reviewer must
    belong to the same institution as the candidate.
    """
    from app.db.models import User

    # Verify candidate exists and belongs to the session institution
    candidate = db.get(MatchCandidate, candidate_id)
    if candidate is None or candidate.institution_id != auth.institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match candidate {candidate_id} not found.",
        )

    # Verify reviewer exists and belongs to the same institution
    reviewer = db.get(User, payload.reviewer_id)
    if reviewer is None or reviewer.institution_id != auth.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer not found or does not belong to your institution.",
        )

    # Check if candidate already has an active assignment
    existing = (
        db.execute(
            select(ReviewerAssignment).where(
                ReviewerAssignment.candidate_id == candidate_id,
                ReviewerAssignment.status == "ACTIVE",
            )
        )
        .scalars()
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Candidate {candidate_id} already has an active reviewer assignment.",
        )

    from sqlalchemy import func as sq_func
    now = sq_func.now()
    assignment = ReviewerAssignment(
        candidate_id=candidate_id,
        reviewer_id=payload.reviewer_id,
        assigned_at=now,
        status="ACTIVE",
        reviewer_institution_id=auth.institution_id,
    )
    db.add(assignment)
    db.flush()

    # Update candidate's assigned reviewer
    candidate.assigned_reviewer_id = payload.reviewer_id
    candidate.reviewed_at = now
    candidate.state = "ASSIGNED"

    db.commit()
    db.refresh(assignment)

    return {
        "id": assignment.id,
        "candidate_id": assignment.candidate_id,
        "reviewer_id": assignment.reviewer_id,
        "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else "",
        "status": assignment.status,
        "reviewer_institution_id": assignment.reviewer_institution_id,
    }


@router.get(
    "/identity-review/candidates/{candidate_id}/reviewer-assignments",
    response_model=ReviewerAssignmentListResponse,
)
def list_reviewer_assignments(
    candidate_id: int,
    auth: AuthContext = Depends(require_roles(*_IDENTITY_REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> Any:
    """List reviewer assignments for a candidate."""
    candidate = db.get(MatchCandidate, candidate_id)
    if candidate is None or candidate.institution_id != auth.institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match candidate {candidate_id} not found.",
        )

    assignments = (
        db.execute(
            select(ReviewerAssignment).where(
                ReviewerAssignment.candidate_id == candidate_id
            )
        )
        .scalars()
        .all()
    )

    return {
        "assignments": [
            {
                "id": a.id,
                "candidate_id": a.candidate_id,
                "reviewer_id": a.reviewer_id,
                "assigned_at": a.assigned_at.isoformat() if a.assigned_at else "",
                "status": a.status,
                "reviewer_institution_id": a.reviewer_institution_id,
            }
            for a in assignments
        ]
    }


@router.post(
    "/identity-review/candidates/{candidate_id}/adjudicate",
    response_model=AdjudicationCaseOut,
)
def adjudicate_case(
    candidate_id: int,
    payload: AdjudicationCaseCreate,
    auth: AuthContext = Depends(require_roles(*_IDENTITY_REVIEW_OFFICER_ONLY)),
    db: Session = Depends(get_db),
) -> Any:
    """Record an adjudication decision for a candidate.

    Only IDENTITY_REVIEW_OFFICER can record the final decision. This creates
    a case and an entry in the decision history.
    """
    from app.db.models import User
    from sqlalchemy import func as sq_func

    # Verify candidate exists and belongs to the session institution
    candidate = db.get(MatchCandidate, candidate_id)
    if candidate is None or candidate.institution_id != auth.institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match candidate {candidate_id} not found.",
        )

    # Verify the assigned reviewer exists and belongs to the same institution
    if candidate.assigned_reviewer_id:
        reviewer = db.get(User, candidate.assigned_reviewer_id)
        if reviewer is None or reviewer.institution_id != auth.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Assigned reviewer not found or does not belong to your institution.",
            )

    now = sq_func.now()
    policy_version = getattr(payload, "policy_version", 1) or 1
    outcome = getattr(payload, "outcome", None)
    decision_reason_code = getattr(payload, "decision_reason_code", None)
    decision_reason_text = getattr(payload, "decision_reason_text", None)
    case = AdjudicationCase(
        candidate_id=candidate_id,
        reviewer_id=getattr(auth, "user_id", auth.institution_id) if hasattr(auth, "user_id") or hasattr(auth, "institution_id") else 1,
        policy_version=policy_version,
        outcome=outcome,
        decision_reason_code=decision_reason_code,
        decision_reason_text=decision_reason_text,
        created_at=now,
        state="DECIDED",
    )
    db.add(case)
    db.flush()

    # Create decision history entry
    history = DecisionHistory(
        case_id=case.id,
        outcome=outcome,
        decision_reason_code=decision_reason_code,
        decision_reason_text=decision_reason_text,
        changed_by=getattr(auth, "user_id", 1),
        changed_at=now,
        parent_id=None,
        notes="Initial adjudication decision",
    )
    db.add(history)

    # Update candidate state
    candidate.state = "DECIDED"

    db.commit()
    db.refresh(case)

    return {
        "id": case.id,
        "candidate_id": case.candidate_id,
        "reviewer_id": case.reviewer_id,
        "policy_version": case.policy_version,
        "outcome": case.outcome,
        "decision_reason_code": case.decision_reason_code,
        "decision_reason_text": case.decision_reason_text,
        "confirmed_at": case.confirmed_at.isoformat() if case.confirmed_at else None,
        "confirmed_by": case.confirmed_by,
        "created_at": case.created_at.isoformat() if case.created_at else "",
        "resolved_at": case.resolved_at.isoformat() if case.resolved_at else None,
        "resolution_notes": case.resolution_notes,
        "state": case.state,
    }


@router.get(
    "/identity-review/candidates/{candidate_id}/adjudication-cases",
    response_model=AdjudicationCaseListResponse,
)
def list_adjudication_cases(
    candidate_id: int,
    auth: AuthContext = Depends(require_roles(*_IDENTITY_REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> Any:
    """List adjudication cases for a candidate."""
    candidate = db.get(MatchCandidate, candidate_id)
    if candidate is None or candidate.institution_id != auth.institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match candidate {candidate_id} not found.",
        )

    cases = (
        db.execute(
            select(AdjudicationCase).where(AdjudicationCase.candidate_id == candidate_id)
        )
        .scalars()
        .all()
    )

    return {
        "cases": [
            {
                "id": c.id,
                "candidate_id": c.candidate_id,
                "reviewer_id": c.reviewer_id,
                "policy_version": c.policy_version,
                "outcome": c.outcome,
                "decision_reason_code": c.decision_reason_code,
                "decision_reason_text": c.decision_reason_text,
                "confirmed_at": c.confirmed_at.isoformat() if c.confirmed_at else None,
                "confirmed_by": c.confirmed_by,
                "created_at": c.created_at.isoformat() if c.created_at else "",
                "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
                "resolution_notes": c.resolution_notes,
                "state": c.state,
            }
            for c in cases
        ]
    }


@router.get(
    "/identity-review/candidates/{candidate_id}/decision-history",
    response_model=DecisionHistoryListResponse,
)
def list_decision_history(
    candidate_id: int,
    auth: AuthContext = Depends(require_roles(*_IDENTITY_REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> Any:
    """List the append-only decision history for a case."""
    from app.db.models import AdjudicationCase

    case = db.get(AdjudicationCase, candidate_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No adjudication case found for candidate {candidate_id}.",
        )

    history = (
        db.execute(
            select(DecisionHistory)
            .where(DecisionHistory.case_id == case.id)
            .order_by(DecisionHistory.changed_at.desc())
        )
        .scalars()
        .all()
    )

    return {
        "history": [
            {
                "id": h.id,
                "case_id": h.case_id,
                "outcome": h.outcome,
                "decision_reason_code": h.decision_reason_code,
                "decision_reason_text": h.decision_reason_text,
                "changed_by": h.changed_by,
                "changed_at": h.changed_at.isoformat() if h.changed_at else "",
                "parent_id": h.parent_id,
                "notes": h.notes,
            }
            for h in history
        ]
    }