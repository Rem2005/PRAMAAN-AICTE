"""Synthetic demo data: an approved snapshot and an active policy package.

Everything created here is SYNTHETIC demonstration data. There is no real
AICTE/APAAR data and no approved institutional intake behind these numbers
(AGENTS.md directives 1, 10 and 17). The seed exists so the reconciliation
workflow can be demonstrated end to end against real persisted rows rather
than placeholder values.

Idempotent: running it twice creates nothing new.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ApprovedIntakeEntry,
    ApprovedIntakeSnapshot,
    ReconciliationPolicy,
)
from app.schemas.policy import PolicyRules

# Course codes match the synthetic fixture used by the roster sample CSV, so an
# uploaded synthetic roster can actually match approved capacity lines.
SYNTHETIC_COURSES = ("CE-UG-FT-S1", "CS-UG-FT-S1", "ME-UG-FT-S1")

# (seat category, approved places). Synthetic, round numbers: not a claim about
# any real institution's sanctioned intake.
SYNTHETIC_CAPACITY = (
    ("CAP_GENERAL", 60),
    ("CAP_OBC", 30),
    ("CAP_SC", 20),
    ("CAP_ST", 10),
    ("CAP_EWS", 10),
)

DEMO_POLICY_RULES: Dict[str, Any] = {
    "link_fields": ["course_code", "academic_year", "seat_category"],
    "compare_fields": ["course_code", "academic_year"],
    "normalisation": {
        "course_code": "trim_upper",
        "academic_year": "trim_upper",
        "seat_category": "trim_upper",
    },
    "required_fields": ["local_ref", "course_code", "academic_year", "seat_category"],
    "optional_fields": ["entry_level", "identity_status"],
    "missing_value": "invalid",
    "detect_duplicates": True,
    "duplicate_key_fields": ["local_ref"],
    "scope": None,
    "check_capacity": True,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def rules_checksum(rules: Dict[str, Any]) -> str:
    """Stable checksum of a policy package (sorted keys, no whitespace)."""
    canonical = json.dumps(rules, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def seed_demo(
    db: Session,
    institution_id: int,
    academic_year: str = "2026-2027",
    created_by: str = "seed-demo",
) -> Dict[str, Any]:
    """Create the synthetic snapshot and policy if they are missing."""

    now = _utc_now()
    created: List[str] = []
    existing: List[str] = []

    snapshot = db.execute(
        select(ApprovedIntakeSnapshot).where(
            ApprovedIntakeSnapshot.institution_id == institution_id,
            ApprovedIntakeSnapshot.version == 1,
        )
    ).scalar_one_or_none()

    if snapshot is None:
        snapshot = ApprovedIntakeSnapshot(
            institution_id=institution_id,
            version=1,
            status=ApprovedIntakeSnapshot.STATUS_APPROVED,
            # Explicit provenance marker: this is not an official intake file.
            source_ref=f"SYNTHETIC-DEMO-SNAPSHOT-{academic_year}",
            effective_from=now,
            effective_to=now + timedelta(days=365),
            created_at=now,
            approved_at=now,
            approved_by=f"{created_by} (synthetic)",
        )
        db.add(snapshot)
        db.flush()
        for course_code in SYNTHETIC_COURSES:
            for seat_category, capacity in SYNTHETIC_CAPACITY:
                db.add(
                    ApprovedIntakeEntry(
                        snapshot_id=snapshot.id,
                        course_code=course_code,
                        academic_year=academic_year,
                        seat_category=seat_category,
                        approved_count=capacity,
                    )
                )
        created.append("approved snapshot v1 (synthetic)")
    else:
        existing.append("approved snapshot v1")

    # Validate before persisting so a broken seed cannot be stored.
    PolicyRules.model_validate(DEMO_POLICY_RULES)

    policy = db.execute(
        select(ReconciliationPolicy).where(
            ReconciliationPolicy.institution_id == institution_id,
            ReconciliationPolicy.version == 1,
        )
    ).scalar_one_or_none()

    if policy is None:
        policy = ReconciliationPolicy(
            institution_id=institution_id,
            version=1,
            name="Synthetic demo policy v1",
            description=(
                "Deterministic link on course/year/category with an exact "
                "capacity comparison. Synthetic demonstration policy, not an "
                "approved AICTE rule set."
            ),
            status=ReconciliationPolicy.STATUS_ACTIVE,
            rules=json.dumps(DEMO_POLICY_RULES, sort_keys=True, separators=(",", ":")),
            rules_checksum=rules_checksum(DEMO_POLICY_RULES),
            created_at=now,
            created_by=f"{created_by} (synthetic)",
            activated_at=now,
            activated_by=f"{created_by} (synthetic)",
        )
        db.add(policy)
        created.append("active policy v1 (synthetic)")
    else:
        existing.append("policy v1")

    db.commit()
    db.refresh(snapshot)
    db.refresh(policy)

    return {
        "institution_id": institution_id,
        "academic_year": academic_year,
        "snapshot_id": snapshot.id,
        "snapshot_version": snapshot.version,
        "policy_id": policy.id,
        "policy_version": policy.version,
        "created": created,
        "existing": existing,
    }
