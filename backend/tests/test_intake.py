"""Tests for the roster intake module."""

import hashlib
import io
import os
import tempfile
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.session import get_db
from app.main import app


# Use a temporary SQLite database for intake tests
_tmp_db_fd, _tmp_db_path = tempfile.mkstemp(suffix=".db")
os.close(_tmp_db_fd)
_TEST_DB_URL = f"sqlite:///{_tmp_db_path}"


def _override_get_db() -> Generator[Session, None, None]:
    engine = create_engine(_TEST_DB_URL, pool_pre_ping=True)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    # Create all tables (including migration baseline)
    from app.db.base import Base
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    engine.dispose()


app.dependency_overrides[get_db] = _override_get_db

TEST_PASSWORD = "Correct-Horse-Battery-Staple-1"
OPERATOR_USERNAME = "operator"


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(_TEST_DB_URL, pool_pre_ping=True)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    from app.db.base import Base
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Create a default institution for tests (idempotent)
    from app.db.models import Institution
    existing = db.get(Institution, 1)
    if not existing:
        db.add(Institution(id=1, official_code="INST001", name="Test Institution", status="ACTIVE"))
        db.commit()
    yield db
    db.close()
    engine.dispose()


@pytest.fixture
def operator(db_session: Session) -> str:
    """An institution-1 account holding the roster operator role."""
    from app.db.models import User
    from app.services.auth import ROLE_OPERATOR, create_user

    existing = (
        db_session.query(User).filter(User.username == OPERATOR_USERNAME).first()
    )
    if existing is None:
        create_user(
            db_session,
            username=OPERATOR_USERNAME,
            password=TEST_PASSWORD,
            institution_id=1,
            roles=[ROLE_OPERATOR],
        )
    return OPERATOR_USERNAME


@pytest.fixture
def client(db_session: Session, operator: str) -> TestClient:
    """A client already signed in as the institution-1 roster operator."""
    c = TestClient(app)
    resp = c.post(
        "/api/v1/auth/login",
        json={"username": operator, "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return c


@pytest.fixture
def anonymous_client() -> TestClient:
    """A client with no session cookie at all."""
    return TestClient(app)


def _make_csv(rows: list) -> str:
    header = "local_ref,course_code,academic_year,seat_category,entry_level,identity_status,apaar_id\n"
    lines = [header]
    for r in rows:
        lines.append(",".join(str(v) for v in r) + "\n")
    return "".join(lines)


VALID_ROWS = [
    ["SYN-00001", "CE-UG-FT-S1", "2026-2027", "CAP_GENERAL", "FIRST_YEAR", "DOMESTIC_APAAR", "9990000000001"],
    ["SYN-00002", "CE-UG-FT-S1", "2026-2027", "CAP_OBC", "SECOND_YEAR", "DOMESTIC_APAAR", "9990000000002"],
    ["SYN-00003", "CE-UG-FT-S1", "2026-2027", "CAP_SC", "THIRD_YEAR", "DOMESTIC_APAAR", "9990000000003"],
]


def test_upload_valid_roster(client: TestClient, db_session: Session) -> None:
    """T-01: Valid synthetic roster upload creates batch and validates."""
    # Create batch
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    batch_id = data["batch_id"]
    idempotency_key = data["idempotency_key"]
    assert data["state"] == "CREATED"

    # Upload valid CSV
    csv_content = _make_csv(VALID_ROWS)
    resp = client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["batch_id"] == batch_id
    assert data["total_rows"] == 3
    assert data["valid_rows"] == 3
    assert data["invalid_rows"] == 0
    assert data["duplicate_rows"] == 0
    assert data["state"] == "VALIDATED"
    assert all(r["valid"] for r in data["rows"])

    # Confirm
    resp = client.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": idempotency_key},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["state"] == "SUBMITTED_FOR_REVIEW"


def test_upload_empty_file(client: TestClient, db_session: Session) -> None:
    """Empty file is rejected."""
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    batch_id = resp.json()["batch_id"]

    resp = client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_upload_malformed_csv(client: TestClient, db_session: Session) -> None:
    """Malformed CSV (wrong column count) is handled safely."""
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    batch_id = resp.json()["batch_id"]

    # Row with wrong number of columns
    csv_content = (
        "local_ref,course_code,academic_year,seat_category,entry_level,identity_status\n"
        "SYN-00001,CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
        "SYN-00002,CE-UG-FT-S1\n"  # missing columns
    )
    resp = client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 2
    assert data["invalid_rows"] == 1
    assert not data["rows"][1]["valid"]
    assert any("columns" in e for e in data["rows"][1]["errors"])


def test_upload_incorrect_encoding(client: TestClient, db_session: Session) -> None:
    """Incorrectly encoded file is rejected."""
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    batch_id = resp.json()["batch_id"]

    resp = client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={
            "file": ("roster.csv", io.BytesIO(b"\xff\xfe bad"), "text/csv")
        },
    )
    assert resp.status_code == 400
    assert "utf-8" in resp.json()["detail"].lower() or "encoding" in resp.json()["detail"].lower()


def test_upload_missing_required_columns(client: TestClient, db_session: Session) -> None:
    """Missing required columns produces actionable schema error."""
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    batch_id = resp.json()["batch_id"]

    csv_content = "local_ref,course_code\nSYN-00001,CE-UG-FT-S1\n"
    resp = client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 400
    assert "missing required columns" in resp.json()["detail"].lower()


def test_upload_duplicate_headers(client: TestClient, db_session: Session) -> None:
    """Duplicate column headers produce actionable error."""
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    batch_id = resp.json()["batch_id"]

    csv_content = (
        "local_ref,course_code,academic_year,seat_category,entry_level,identity_status,local_ref\n"
        "SYN-00001,CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR,EXTRA\n"
    )
    resp = client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 400
    assert "duplicate" in resp.json()["detail"].lower()


def test_upload_missing_required_fields(client: TestClient, db_session: Session) -> None:
    """Missing required fields produce row-level errors."""
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    batch_id = resp.json()["batch_id"]

    csv_content = (
        "local_ref,course_code,academic_year,seat_category,entry_level,identity_status\n"
        ",CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
        "SYN-00002,,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
    )
    resp = client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["invalid_rows"] == 2
    assert not data["rows"][0]["valid"]
    assert not data["rows"][1]["valid"]
    assert any("local_ref" in e for e in data["rows"][0]["errors"])
    assert any("course_code" in e for e in data["rows"][1]["errors"])


def test_upload_invalid_values(client: TestClient, db_session: Session) -> None:
    """Invalid values for constrained fields produce row-level errors."""
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    batch_id = resp.json()["batch_id"]

    csv_content = (
        "local_ref,course_code,academic_year,seat_category,entry_level,identity_status\n"
        "SYN-00001,CE-UG-FT-S1,2026-2027,INVALID_CATEGORY,FIRST_YEAR,DOMESTIC_APAAR\n"
    )
    resp = client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["invalid_rows"] == 1
    assert any("seat_category" in e for e in data["rows"][0]["errors"])


def test_upload_duplicate_rows_and_identifiers(client: TestClient, db_session: Session) -> None:
    """Duplicate rows and duplicate local_ref values are detected."""
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    batch_id = resp.json()["batch_id"]

    csv_content = (
        "local_ref,course_code,academic_year,seat_category,entry_level,identity_status\n"
        "SYN-00001,CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
        "SYN-00001,CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
        "SYN-00002,CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
    )
    resp = client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["duplicate_rows"] >= 1
    assert data["invalid_rows"] >= 1


def test_preview_does_not_persist_student_records(
    client: TestClient, db_session: Session
) -> None:
    """Preview (validate) does not persist final student records; confirmation is required."""
    from app.db.models import StagedEnrolment

    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    batch_id = resp.json()["batch_id"]

    csv_content = _make_csv(VALID_ROWS)
    client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )

    # Staged enrolments exist (validation staging), but batch is not yet submitted
    from app.db.models import SubmissionBatch
    batch = db_session.get(SubmissionBatch, batch_id)
    assert batch.state == "VALIDATED"
    assert batch.submitted_at is None

    # Staged records exist with validation_state
    staged = (
        db_session.query(StagedEnrolment)
        .filter(StagedEnrolment.batch_id == batch_id)
        .all()
    )
    assert len(staged) == 3
    assert all(s.validation_state == "VALID" for s in staged)


def test_invalid_batch_cannot_be_confirmed(client: TestClient, db_session: Session) -> None:
    """Invalid batches cannot be submitted/confirmed."""
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    batch_id = data["batch_id"]
    idempotency_key = data["idempotency_key"]

    # CSV with invalid rows
    csv_content = (
        "local_ref,course_code,academic_year,seat_category,entry_level,identity_status\n"
        ",CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
    )
    client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )

    # Confirmation should fail due to validation errors
    resp = client.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": idempotency_key},
    )
    assert resp.status_code == 400


def test_confirmation_persists_eligible_records(client: TestClient, db_session: Session) -> None:
    """Explicit confirmation persists eligible (valid) records."""
    from app.db.models import StagedEnrolment, SubmissionBatch

    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    batch_id = data["batch_id"]
    idempotency_key = data["idempotency_key"]

    csv_content = _make_csv(VALID_ROWS)
    client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )

    resp = client.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": idempotency_key},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["state"] == "SUBMITTED_FOR_REVIEW"
    assert data["persisted_count"] == 3

    # Batch is submitted
    batch = db_session.get(SubmissionBatch, batch_id)
    assert batch.state == "SUBMITTED_FOR_REVIEW"
    assert batch.submitted_at is not None


def test_repeated_confirmation_is_idempotent(client: TestClient, db_session: Session) -> None:
    """Retrying a confirmation with the same key replays the original outcome.

    Covers the lost-response case: the client never sees the first success and
    repeats the request. It must get the same result back, not an error and not
    a second side effect.
    """
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    batch_id = data["batch_id"]
    idempotency_key = data["idempotency_key"]

    csv_content = _make_csv(VALID_ROWS)
    client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )

    # First confirmation
    resp = client.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": idempotency_key},
    )
    assert resp.status_code == 200
    first = resp.json()
    assert first["state"] == "SUBMITTED_FOR_REVIEW"
    assert first["persisted_count"] == 3

    # Second confirmation with the same key: identical successful outcome.
    resp = client.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": idempotency_key},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == first

    # No duplicate side effect: counts unchanged and submitted_at stable.
    resp = client.get(f"/api/v1/batches/{batch_id}")
    summary = resp.json()
    assert summary["total_rows"] == 3
    assert summary["state"] == "SUBMITTED_FOR_REVIEW"


def test_confirmation_with_conflicting_key_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    """Reusing a submitted batch's slot with a different key is a conflict."""
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    batch_id = data["batch_id"]
    idempotency_key = data["idempotency_key"]

    client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", io.BytesIO(_make_csv(VALID_ROWS).encode()), "text/csv")},
    )
    resp = client.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": idempotency_key},
    )
    assert resp.status_code == 200

    resp = client.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": "a-different-key"},
    )
    assert resp.status_code == 409
    assert "different idempotency key" in resp.json()["detail"].lower()


def test_confirmation_with_unknown_key_is_rejected(client: TestClient) -> None:
    """A wrong key on an unconfirmed batch is rejected before any state change."""
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    batch_id = resp.json()["batch_id"]

    resp = client.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": "not-the-key"},
    )
    assert resp.status_code == 400
    assert "idempotency key" in resp.json()["detail"].lower()

    resp = client.get(f"/api/v1/batches/{batch_id}")
    assert resp.json()["state"] == "CREATED"


def test_batch_status_and_counts_consistent(client: TestClient, db_session: Session) -> None:
    """Batch status and counts remain consistent after confirmation."""
    from app.db.models import SubmissionBatch

    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    batch_id = data["batch_id"]
    idempotency_key = data["idempotency_key"]

    csv_content = _make_csv(VALID_ROWS)
    client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    client.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": idempotency_key},
    )

    # Read batch status
    resp = client.get(f"/api/v1/batches/{batch_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["batch_id"] == batch_id
    assert data["state"] == "SUBMITTED_FOR_REVIEW"
    assert data["total_rows"] == 3
    assert data["valid_rows"] == 3
    assert data["invalid_rows"] == 0

    # Verify via direct DB query
    batch = db_session.get(SubmissionBatch, batch_id)
    assert batch.state == "SUBMITTED_FOR_REVIEW"


def test_nonexistent_batch_returns_404(client: TestClient) -> None:
    """Reading a nonexistent batch returns 404."""
    resp = client.get("/api/v1/batches/99999")
    assert resp.status_code == 404


def test_validate_nonexistent_batch_returns_404(client: TestClient) -> None:
    """Validating a nonexistent batch returns 404."""
    resp = client.post(
        "/api/v1/batches/99999/validate",
        files={"file": ("roster.csv", io.BytesIO(b"local_ref\nSYN-00001\n"), "text/csv")},
    )
    assert resp.status_code == 404


def test_create_batch_for_another_institution_is_rejected(
    client: TestClient,
) -> None:
    """A body naming another institution cannot widen the session's scope.

    Previously the client-supplied `institution_id` *was* the authorization:
    any caller could file a batch against any institution.
    """
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 99999,
            "academic_year": "2026-2027",
            "checksum": "abc123",
            "schema_version": "v1",
        },
    )
    assert resp.status_code == 403


def test_batch_endpoints_require_authentication(
    anonymous_client: TestClient,
) -> None:
    """Unauthenticated requests are rejected before any work happens (FR-01)."""
    resp = anonymous_client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "schema_version": "v1",
        },
    )
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate")

    assert anonymous_client.get("/api/v1/batches/1").status_code == 401
    assert (
        anonymous_client.post(
            "/api/v1/batches/1/validate",
            files={"file": ("roster.csv", io.BytesIO(b"local_ref\n"), "text/csv")},
        ).status_code
        == 401
    )
    assert (
        anonymous_client.post(
            "/api/v1/batches/1/confirm", json={"idempotency_key": "x"}
        ).status_code
        == 401
    )


# ---------------------------------------------------------------------------
# Milestone 5.1 — integrity review regressions
# ---------------------------------------------------------------------------


def _create_batch(client: TestClient, **overrides):
    payload = {
        "institution_id": 1,
        "academic_year": "2026-2027",
        "schema_version": "v1",
    }
    payload.update(overrides)
    resp = client.post("/api/v1/batches", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _upload(client: TestClient, batch_id: int, csv_content: str):
    return client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )


def test_create_batch_accepts_client_without_declared_checksum(
    client: TestClient,
) -> None:
    """The client no longer has to invent a checksum; the server derives it.

    Regression: `checksum` was required and never verified, so the frontend's
    empty payload was rejected with 422 while the value that *was* accepted was
    trusted verbatim.
    """
    data = _create_batch(client, idempotency_key="upload-abc")
    assert data["state"] == "CREATED"
    assert data["idempotency_key"] == "upload-abc"

    csv_content = _make_csv(VALID_ROWS)
    resp = _upload(client, data["batch_id"], csv_content)
    assert resp.status_code == 200, resp.text

    summary = client.get(f"/api/v1/batches/{data['batch_id']}").json()
    expected = hashlib.sha256(csv_content.encode()).hexdigest()
    assert summary["checksum"] == expected


def test_create_batch_persists_academic_year(client: TestClient) -> None:
    """Regression: `academic_year` was accepted at create and then dropped."""
    data = _create_batch(client, academic_year="2027-2028")
    summary = client.get(f"/api/v1/batches/{data['batch_id']}").json()
    assert summary["academic_year"] == "2027-2028"


def test_create_batch_is_idempotent_on_client_key(client: TestClient) -> None:
    """A retried create returns the original batch instead of a duplicate."""
    payload = {
        "institution_id": 1,
        "academic_year": "2026-2027",
        "schema_version": "v1",
        "idempotency_key": "retry-me",
    }
    first = client.post("/api/v1/batches", json=payload)
    second = client.post("/api/v1/batches", json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["batch_id"] == second.json()["batch_id"]


def test_create_batch_rejects_conflicting_key_reuse(client: TestClient) -> None:
    """The same key with a different request must not silently succeed."""
    base = {
        "institution_id": 1,
        "academic_year": "2026-2027",
        "schema_version": "v1",
        "idempotency_key": "shared-key",
    }
    assert client.post("/api/v1/batches", json=base).status_code == 201

    conflicting = dict(base, academic_year="2028-2029")
    resp = client.post("/api/v1/batches", json=conflicting)
    assert resp.status_code == 409


def test_revalidation_replaces_stale_staged_rows(
    client: TestClient, db_session: Session
) -> None:
    """Re-validating a failed batch must not leave the previous rows behind."""
    from app.db.models import StagedEnrolment, SubmissionBatch

    data = _create_batch(client)
    batch_id = data["batch_id"]

    bad_csv = (
        "local_ref,course_code,academic_year,seat_category,entry_level,identity_status\n"
        "SYN-00001,CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
        ",CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
        ",CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
    )
    resp = _upload(client, batch_id, bad_csv)
    assert resp.status_code == 200
    assert resp.json()["state"] == "VALIDATION_FAILED"
    assert resp.json()["total_rows"] == 3

    # Operator corrects the CSV and re-uploads it to the same batch.
    good_csv = _make_csv(VALID_ROWS[:1])
    resp = _upload(client, batch_id, good_csv)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["state"] == "VALIDATED"
    assert data["total_rows"] == 1

    db_session.expire_all()
    staged = (
        db_session.query(StagedEnrolment)
        .filter(StagedEnrolment.batch_id == batch_id)
        .all()
    )
    assert len(staged) == 1, "stale rows survived revalidation"
    assert staged[0].local_ref == "SYN-00001"
    assert db_session.get(SubmissionBatch, batch_id).state == "VALIDATED"


def test_validated_batch_reupload_of_same_file_replays(
    client: TestClient, db_session: Session
) -> None:
    """A lost-response retry of validate returns the original result."""
    from app.db.models import StagedEnrolment

    data = _create_batch(client)
    batch_id = data["batch_id"]
    csv_content = _make_csv(VALID_ROWS)

    first = _upload(client, batch_id, csv_content)
    assert first.status_code == 200
    second = _upload(client, batch_id, csv_content)
    assert second.status_code == 200, second.text
    assert second.json() == first.json()

    db_session.expire_all()
    staged = (
        db_session.query(StagedEnrolment)
        .filter(StagedEnrolment.batch_id == batch_id)
        .all()
    )
    assert len(staged) == len(VALID_ROWS), "replay staged duplicate rows"


def test_validated_batch_cannot_be_overwritten_by_a_different_file(
    client: TestClient,
) -> None:
    """Swapping the file under an already-validated batch is rejected."""
    data = _create_batch(client)
    batch_id = data["batch_id"]
    assert _upload(client, batch_id, _make_csv(VALID_ROWS)).status_code == 200

    other = _make_csv(VALID_ROWS[:1])
    resp = _upload(client, batch_id, other)
    assert resp.status_code == 400
    assert "new batch" in resp.json()["detail"].lower()


def test_validation_failure_leaves_batch_and_rows_untouched(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    """A failure part-way through staging writes nothing at all."""
    import app.services.roster as roster
    from app.db.models import StagedEnrolment, SubmissionBatch

    original = roster._validate_row
    calls = {"n": 0}

    def boom(row, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("simulated staging failure")
        return original(row, *args, **kwargs)

    monkeypatch.setattr(roster, "_validate_row", boom)

    data = _create_batch(client)
    batch_id = data["batch_id"]
    resp = _upload(client, batch_id, _make_csv(VALID_ROWS))
    assert resp.status_code == 500

    db_session.expire_all()
    batch = db_session.get(SubmissionBatch, batch_id)
    assert batch.state == "CREATED", "batch state was left mid-transaction"
    staged = (
        db_session.query(StagedEnrolment)
        .filter(StagedEnrolment.batch_id == batch_id)
        .all()
    )
    assert staged == [], "partial staged rows were committed"


def test_row_academic_year_must_match_batch(client: TestClient) -> None:
    """Rows from another academic period cannot be staged under this batch."""
    data = _create_batch(client, academic_year="2026-2027")
    csv_content = (
        "local_ref,course_code,academic_year,seat_category,entry_level,identity_status\n"
        "SYN-00001,CE-UG-FT-S1,2025-2026,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
    )
    resp = _upload(client, data["batch_id"], csv_content)
    assert resp.status_code == 200
    body = resp.json()
    assert body["invalid_rows"] == 1
    assert any("does not match batch academic year" in e for e in body["rows"][0]["errors"])


def test_oversized_file_is_rejected(client: TestClient) -> None:
    """Files above the configured limit are rejected before parsing."""
    data = _create_batch(client)
    oversized = b"x" * (settings.max_upload_size_mb * 1024 * 1024 + 1)
    resp = client.post(
        f"/api/v1/batches/{data['batch_id']}/validate",
        files={"file": ("roster.csv", io.BytesIO(oversized), "text/csv")},
    )
    assert resp.status_code == 400
    assert "too large" in resp.json()["detail"].lower()


def test_confirm_rejected_in_non_validated_states(client: TestClient) -> None:
    """Confirmation is reachable only from VALIDATED."""
    data = _create_batch(client)
    batch_id = data["batch_id"]

    resp = client.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": data["idempotency_key"]},
    )
    assert resp.status_code == 400

    assert _upload(client, batch_id, _make_csv(VALID_ROWS)).status_code == 200
    resp = client.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": data["idempotency_key"]},
    )
    assert resp.status_code == 200

    # Re-validating a submitted batch is no longer a legal transition.
    resp = _upload(client, batch_id, _make_csv(VALID_ROWS))
    assert resp.status_code == 400


def test_stale_session_confirmation_replays_the_winning_outcome(
    client: TestClient, db_session: Session
) -> None:
    """Two sessions that both read VALIDATED cannot both win the transition.

    `db_session` loads the batch while it is still VALIDATED, then the API
    confirms it from a different session. The stale session's confirm hits the
    compare-and-set, finds the row already moved, and replays the winner's
    outcome rather than reporting an error or applying a second side effect.
    This exercises the single-writer branch deterministically; it is not a
    claim about multi-process concurrency, which is untested here.
    """
    from app.db.models import SubmissionBatch
    from app.services.roster import confirm_batch

    data = _create_batch(client)
    batch_id = data["batch_id"]
    key = data["idempotency_key"]
    assert _upload(client, batch_id, _make_csv(VALID_ROWS)).status_code == 200

    stale = db_session.get(SubmissionBatch, batch_id)
    assert stale.state == "VALIDATED"

    winner = client.post(
        f"/api/v1/batches/{batch_id}/confirm", json={"idempotency_key": key}
    )
    assert winner.status_code == 200

    replayed = confirm_batch(db=db_session, batch_id=batch_id, idempotency_key=key)
    assert replayed == winner.json()

    db_session.expire_all()
    assert db_session.get(SubmissionBatch, batch_id).state == "SUBMITTED_FOR_REVIEW"


# ---------------------------------------------------------------------------
# Institution batch list (dashboard data source)
# ---------------------------------------------------------------------------


def test_list_batches_requires_authentication(anonymous_client: TestClient) -> None:
    """The institution list is not readable without a session."""
    assert anonymous_client.get("/api/v1/batches").status_code == 401


def test_list_batches_scoped_to_session_institution(
    client: TestClient, db_session: Session
) -> None:
    """Only the session institution's batches are returned, with real counts."""
    from app.db.models import Institution, SubmissionBatch, User

    data = _create_batch(client, idempotency_key="list-scope-1")
    resp = _upload(client, data["batch_id"], _make_csv(VALID_ROWS))
    assert resp.status_code == 200, resp.text

    # A batch filed under a different institution must not appear.
    other = db_session.get(Institution, 2)
    if other is None:
        db_session.add(
            Institution(id=2, official_code="INST002", name="Other Institution", status="ACTIVE")
        )
        db_session.commit()
    from datetime import datetime, timezone

    foreign = SubmissionBatch(
        institution_id=2,
        uploader_ref="someone-else",
        academic_year="2026-2027",
        source_filename="other.csv",
        checksum="x" * 64,
        schema_version="v1",
        state="CREATED",
        idempotency_key="list-scope-other",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(foreign)
    db_session.commit()
    foreign_id = foreign.id

    body = client.get("/api/v1/batches").json()
    ids = [item["batch_id"] for item in body["batches"]]
    assert data["batch_id"] in ids
    assert foreign_id not in ids
    assert all(item["source_filename"] != "other.csv" for item in body["batches"])

    item = next(i for i in body["batches"] if i["batch_id"] == data["batch_id"])
    assert item["state"] == "VALIDATED"
    assert item["source_filename"] == "roster.csv"
    assert item["uploader_ref"] == OPERATOR_USERNAME
    assert item["total_rows"] == len(VALID_ROWS)
    assert item["valid_rows"] == len(VALID_ROWS)
    assert item["invalid_rows"] == 0

    # Totals are the sum of what the response lists, not a separate estimate.
    assert body["totals"]["batches"] == len(body["batches"])
    assert body["totals"]["valid_rows"] == sum(i["valid_rows"] for i in body["batches"])
    assert body["totals"]["invalid_rows"] == sum(i["invalid_rows"] for i in body["batches"])


def test_list_batches_preserves_invalid_row_counts(
    client: TestClient, db_session: Session
) -> None:
    """Invalid rows are counted, never dropped from the batch listing."""
    data = _create_batch(client, idempotency_key="list-invalid-1")
    bad_csv = (
        "local_ref,course_code,academic_year,seat_category,entry_level,identity_status\n"
        "SYN-00001,CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
        ",CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
    )
    assert _upload(client, data["batch_id"], bad_csv).status_code == 200

    body = client.get("/api/v1/batches").json()
    item = next(i for i in body["batches"] if i["batch_id"] == data["batch_id"])
    assert item["state"] == "VALIDATION_FAILED"
    assert item["total_rows"] == 2
    assert item["valid_rows"] == 1
    assert item["invalid_rows"] == 1


def test_list_batches_denied_to_a_role_without_batch_access(
    client: TestClient, db_session: Session
) -> None:
    """Role checks are server-side: an auditor cannot read batch listing."""
    from app.db.models import User
    from app.services.auth import ROLE_AUDITOR, create_user

    if db_session.query(User).filter_by(username="auditor1").first() is None:
        create_user(
            db_session,
            username="auditor1",
            password=TEST_PASSWORD,
            institution_id=1,
            roles=[ROLE_AUDITOR],
        )

    other_client = TestClient(app)
    login = other_client.post(
        "/api/v1/auth/login",
        json={"username": "auditor1", "password": TEST_PASSWORD},
    )
    assert login.status_code == 200, login.text
    assert other_client.get("/api/v1/batches").status_code == 403


# ---- The checked-in sample rosters (docs/samples/) ----
#
# These are the files the Roster Intake screen offers for download. They are
# uploaded here through the real create/validate/confirm endpoints so the
# documented sample cannot silently stop matching the parser.

SAMPLE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "samples"
)


def _sample_bytes(filename: str) -> bytes:
    with open(os.path.join(SAMPLE_DIR, filename), "rb") as handle:
        return handle.read()


def _upload_sample(client: TestClient, batch_id: int, filename: str):
    """Upload a checked-in sample file by name (distinct from `_upload`)."""
    return client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": (filename, io.BytesIO(_sample_bytes(filename)), "text/csv")},
    )


def test_sample_roster_file_validates_and_confirms(client: TestClient) -> None:
    """docs/samples/sample-roster.csv is 10 valid rows and can be submitted."""
    batch = _create_batch(client)
    batch_id = batch["batch_id"]
    idempotency_key = batch["idempotency_key"]

    resp = _upload_sample(client, batch_id, "sample-roster.csv")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_rows"] == 10
    assert data["valid_rows"] == 10
    assert data["invalid_rows"] == 0
    assert data["duplicate_rows"] == 0
    assert data["state"] == "VALIDATED"
    assert all(row["valid"] for row in data["rows"])

    resp = client.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": idempotency_key},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["state"] == "SUBMITTED_FOR_REVIEW"
    assert resp.json()["persisted_count"] == 10


def test_sample_roster_with_errors_file_reports_each_bad_row(client: TestClient) -> None:
    """docs/samples/sample-roster-with-errors.csv is 10 valid / 3 invalid rows."""
    batch = _create_batch(client)
    batch_id = batch["batch_id"]
    idempotency_key = batch["idempotency_key"]

    resp = _upload_sample(client, batch_id, "sample-roster-with-errors.csv")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_rows"] == 13
    assert data["valid_rows"] == 10
    assert data["invalid_rows"] == 3
    assert data["duplicate_rows"] == 1
    assert data["state"] == "VALIDATION_FAILED"

    errors = {
        row["row_number"]: row["errors"] for row in data["rows"] if not row["valid"]
    }
    # Header is row 1, so the three appended rows are 12, 13 and 14.
    assert sorted(errors) == [12, 13, 14]
    assert "seat_category is required" in errors[12][0]
    assert "invalid entry_level 'YEAR_ONE'" in errors[13][0]
    assert "duplicate local_ref 'SYN-00001'" in errors[14][0]

    # An invalid row is never submitted.
    resp = client.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": idempotency_key},
    )
    assert resp.status_code == 400
    assert "invalid rows" in resp.json()["detail"].lower()


def test_sample_roster_academic_year_mismatch_is_reported(client: TestClient) -> None:
    """The sample's academic_year is part of the contract, not decoration."""
    batch = _create_batch(client, academic_year="2027-2028")

    resp = _upload_sample(client, batch["batch_id"], "sample-roster.csv")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["state"] == "VALIDATION_FAILED"
    assert data["valid_rows"] == 0
    assert all(
        "does not match batch academic year" in row["errors"][0]
        for row in data["rows"]
    )
