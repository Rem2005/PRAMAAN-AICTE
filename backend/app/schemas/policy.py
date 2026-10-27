"""Policy-package schemas.

`PolicyRules` is the machine-checked contract for what a reconciliation policy
may say. It deliberately contains only deterministic, documented rules: no
fuzzy thresholds, no learned weights, no identity-linkage heuristics.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Fields that exist on BOTH a staged roster row and an approved intake entry,
# so they are the only values that can be linked on or compared across.
COMPARABLE_FIELDS = ("course_code", "academic_year", "seat_category")

# Fields that exist only on a roster row. They may be required or used for
# duplicate detection, but they can never be compared against an entry.
ROSTER_ONLY_FIELDS = ("local_ref", "entry_level", "identity_status")

ROSTER_FIELDS = COMPARABLE_FIELDS + ROSTER_ONLY_FIELDS

# Exact, documented transforms. Nothing here is fuzzy or statistical.
NORMALISATIONS = ("none", "trim", "upper", "trim_upper")

# The outcome vocabulary. Reconciliation emits only these.
OUTCOME_MATCHED = "MATCHED"
OUTCOME_UNMATCHED = "UNMATCHED"
OUTCOME_FIELD_MISMATCH = "FIELD_MISMATCH"
OUTCOME_AMBIGUOUS = "AMBIGUOUS"
OUTCOME_DUPLICATE_CANDIDATE = "DUPLICATE_CANDIDATE"
OUTCOME_INVALID_INPUT = "INVALID_INPUT"
OUTCOME_EXCLUDED_BY_POLICY = "EXCLUDED_BY_POLICY"

OUTCOMES = (
    OUTCOME_MATCHED,
    OUTCOME_UNMATCHED,
    OUTCOME_FIELD_MISMATCH,
    OUTCOME_AMBIGUOUS,
    OUTCOME_DUPLICATE_CANDIDATE,
    OUTCOME_INVALID_INPUT,
    OUTCOME_EXCLUDED_BY_POLICY,
)

# Capacity comparison statuses used in the run summary (aggregate only; these
# are never a row outcome).
CAPACITY_MATCHED = "MATCHED"
CAPACITY_UNDERFILLED = "UNDERFILLED"
CAPACITY_EXCEEDED = "EXCEEDED"


class ScopeFilter(BaseModel):
    """Optional include-lists. Rows outside the scope are excluded, not failed."""

    model_config = ConfigDict(extra="forbid")

    course_codes: Optional[List[str]] = None
    seat_categories: Optional[List[str]] = None
    academic_years: Optional[List[str]] = None


class PolicyRules(BaseModel):
    """A deterministic reconciliation policy package."""

    model_config = ConfigDict(extra="forbid")

    # Coarse key used to locate candidate entries for a row.
    link_fields: List[str] = Field(..., min_length=1)
    # Fields checked once a single candidate has been located. May include
    # fields that are not part of link_fields, which is what makes a field
    # mismatch observable rather than collapsing it into "unmatched".
    compare_fields: List[str] = Field(..., min_length=1)
    # field -> one of NORMALISATIONS. Missing entries default to trim_upper.
    normalisation: Dict[str, str] = Field(default_factory=dict)
    # Fields that must be present and non-empty on a roster row.
    required_fields: List[str] = Field(default_factory=list)
    # Compared only when present on both sides; absence is not a mismatch.
    optional_fields: List[str] = Field(default_factory=list)
    # What to do when a required field is missing on a row.
    missing_value: Literal["invalid", "exclude"] = "invalid"
    # Detect rows that collapse to the same normalised identity.
    detect_duplicates: bool = True
    duplicate_key_fields: List[str] = Field(default_factory=lambda: ["local_ref"])
    scope: Optional[ScopeFilter] = None
    # Compare submitted volume against approved capacity in the summary.
    check_capacity: bool = True

    @model_validator(mode="after")
    def _check_rules(self) -> "PolicyRules":
        for name in ("link_fields", "compare_fields"):
            values = getattr(self, name)
            unknown = [f for f in values if f not in COMPARABLE_FIELDS]
            if unknown:
                raise ValueError(
                    f"{name} may only contain comparable fields "
                    f"{COMPARABLE_FIELDS}; got {unknown}"
                )
            if len(set(values)) != len(values):
                raise ValueError(f"{name} contains duplicate entries")

        for field_name, rule in self.normalisation.items():
            if field_name not in ROSTER_FIELDS:
                raise ValueError(
                    f"normalisation refers to unknown field '{field_name}'"
                )
            if rule not in NORMALISATIONS:
                raise ValueError(
                    f"normalisation for '{field_name}' must be one of {NORMALISATIONS}"
                )

        overlap = set(self.required_fields) & set(self.optional_fields)
        if overlap:
            raise ValueError(
                f"fields cannot be both required and optional: {sorted(overlap)}"
            )
        for name in ("required_fields", "optional_fields"):
            values = getattr(self, name)
            unknown = [f for f in values if f not in ROSTER_FIELDS]
            if unknown:
                raise ValueError(f"{name} contains unknown fields {unknown}")

        if self.detect_duplicates:
            if not self.duplicate_key_fields:
                raise ValueError("duplicate_key_fields cannot be empty")
            unknown = [
                f for f in self.duplicate_key_fields if f not in ROSTER_FIELDS
            ]
            if unknown:
                raise ValueError(
                    f"duplicate_key_fields contains unknown fields {unknown}"
                )

        return self

    def normalisation_for(self, field_name: str) -> str:
        return self.normalisation.get(field_name, "trim_upper")


def normalise(value: Optional[str], rule: str) -> Optional[str]:
    """Apply one documented transform. None stays None (absence is not '')."""
    if value is None:
        return None
    if rule == "none":
        return value
    if rule == "trim":
        return value.strip()
    if rule == "upper":
        return value.upper()
    if rule == "trim_upper":
        return value.strip().upper()
    raise ValueError(f"unknown normalisation rule '{rule}'")


# --------------------------------------------------------------- API schemas


class PolicyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    rules: PolicyRules


class PolicyUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    rules: Optional[PolicyRules] = None


class PolicyValidateRequest(BaseModel):
    """Dry-run validation; persists nothing."""

    rules: PolicyRules


class PolicyValidateResponse(BaseModel):
    valid: bool
    rules_checksum: str
    errors: List[str] = Field(default_factory=list)


class PolicyResponse(BaseModel):
    policy_id: int
    institution_id: int
    version: int
    name: str
    description: Optional[str]
    status: str
    rules: PolicyRules
    rules_checksum: str
    created_at: str
    created_by: str
    activated_at: Optional[str] = None
    activated_by: Optional[str] = None
# --------------------------------------------------------------- Identity Review Schemas


class MatchCandidateOut(BaseModel):
    id: int
    institution_id: int
    record_ref: str
    method: str
    version: str
    score: Optional[float] = None
    reasons: Optional[List[str]] = None
    state: str
    created_at: str
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[int] = None
    assigned_reviewer_id: Optional[int] = None
    assigned_at: Optional[str] = None


class MatchCandidateListResponse(BaseModel):
    candidates: List[MatchCandidateOut]


class MatchCandidateSearch(BaseModel):
    query: Optional[str] = Field(None, description="Search against record_ref")
    state: Optional[str] = Field(None, description="Filter by state")
    method: Optional[str] = Field(None, description="Filter by method")


class ReviewerAssignmentOut(BaseModel):
    id: int
    candidate_id: int
    reviewer_id: int
    assigned_at: str
    status: str
    reviewer_institution_id: int


class ReviewerAssignmentCreate(BaseModel):
    reviewer_id: int
    reviewer_institution_id: int


class ReviewerAssignmentListResponse(BaseModel):
    assignments: List[ReviewerAssignmentOut]


class AdjudicationCaseOut(BaseModel):
    id: int
    candidate_id: int
    reviewer_id: int
    policy_version: int
    outcome: Optional[str] = None
    decision_reason_code: Optional[str] = None
    decision_reason_text: Optional[str] = None
    confirmed_at: Optional[str] = None
    confirmed_by: Optional[int] = None
    created_at: str
    resolved_at: Optional[str] = None
    resolution_notes: Optional[str] = None
    state: str


class AdjudicationCaseCreate(BaseModel):
    policy_version: int = Field(1, gt=0)
    outcome: Optional[str] = None
    decision_reason_code: Optional[str] = None
    decision_reason_text: Optional[str] = None


class AdjudicationCaseListResponse(BaseModel):
    cases: List[AdjudicationCaseOut]


class DecisionHistoryOut(BaseModel):
    id: int
    case_id: int
    outcome: Optional[str] = None
    decision_reason_code: Optional[str] = None
    decision_reason_text: Optional[str] = None
    changed_by: int
    changed_at: str
    parent_id: Optional[int] = None
    notes: Optional[str] = None


class DecisionHistoryListResponse(BaseModel):
    history: List[DecisionHistoryOut]


class DecisionCreate(BaseModel):
    outcome: str = Field(..., description="One of: CONFIRMED, REJECTED, UNABLE_TO_DETERMINE")
    decision_reason_code: str = Field(..., min_length=1)
    decision_reason_text: str = Field(..., min_length=1)
