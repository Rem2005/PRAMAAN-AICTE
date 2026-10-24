"""Deterministic synthetic fixtures for PRAMAAN-AICTE development and tests."""

from typing import Any

SYNTHETIC_ID_PREFIX = "999"


def _synthetic_apaar_id(seed: int) -> str:
    return f"{SYNTHETIC_ID_PREFIX}{seed:010d}"


def generate_synthetic_intake_records(count: int = 5) -> list[dict[str, Any]]:
    """Generate deterministic, clearly synthetic enrolment records.

    All identifiers and values produced here are SYNTHETIC. They must never be
    populated with real student data. See docs/PRD.md, docs/security-privacy.md,
    and ADR-0002 (institution-side identity boundary).
    """
    records: list[dict[str, Any]] = []
    for i in range(max(0, count)):
        records.append(
            {
                "record_ref": f"SYN-{i + 1:05d}",
                "academic_year": "2026-2027",
                "course_code": "CE-UG-FT-S1",
                "entry_level": "FIRST_YEAR",
                "seat_category": "CAP_GENERAL",
                "identity_track": "DOMESTIC_APAAR",
                "apaar_id": _synthetic_apaar_id(i + 1),
                "validation_state": "SYNTHETIC",
            }
        )
    return records
