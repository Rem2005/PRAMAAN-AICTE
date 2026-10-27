"""Pydantic schemas for reconciliation: snapshots, policies, runs, outcomes."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SnapshotOut(BaseModel):
    snapshot_id: int
    version: int
    status: str
    source_ref: str
    created_at: str
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    entry_count: int


class SnapshotListResponse(BaseModel):
    snapshots: List[SnapshotOut]


class PolicyOut(BaseModel):
    policy_id: int
    version: int
    name: str
    description: Optional[str] = None
    status: str
    rules: Dict[str, Any]
    rules_checksum: str
    created_at: str
    activated_at: Optional[str] = None


class PolicyListResponse(BaseModel):
    policies: List[PolicyOut]


class ReconciliationOutcomeOut(BaseModel):
    row_number: int
    local_ref: Optional[str] = None
    outcome: str
    reasons: List[str] = []


class ReconciliationRunOut(BaseModel):
    run_id: int
    batch_id: int
    run_number: int
    snapshot_id: int
    snapshot_version: int
    policy_id: int
    policy_version: int
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    triggered_by: str
    row_count: int
    digest: Optional[str] = None
    totals: Optional[str] = None
    error_code: Optional[str] = None
    outcome_counts: Dict[str, int] = {}
    # Denormalised from the batch so a report stays readable on its own.
    source_filename: Optional[str] = None
    academic_year: Optional[str] = None
    batch_state: Optional[str] = None


class ReconciliationRunDetailResponse(ReconciliationRunOut):
    outcomes: List[ReconciliationOutcomeOut] = []


class ReconciliationRunListResponse(BaseModel):
    runs: List[ReconciliationRunOut]
