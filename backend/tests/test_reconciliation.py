"""Phase 2: reconciliation runs, history, scoping and reproducibility."""

from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import Institution, ReconciliationPolicy
from app.db.session import get_db
from app.fixtures.demo import seed_demo
from app.main import app
from app.services.auth import ROLE_AUDITOR, ROLE_NODAL, ROLE_OPERATOR, create_user

PASSWORD = "Synthetic-Demo-Password-1"
HEADER = (
    "local_ref,course_code,academic_year,seat_category,entry_level,identity_status\n"
)


@pytest.fixture
def db_path(tmp_path) -> str:
    return f"sqlite:///{tmp_path}/reconciliation_test.db"


@pytest.fixture
def session_factory(db_path):
    engine = create_engine(db_path, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield factory
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db(session_factory) -> Session:
    session = session_factory()
    session.add_all(
        [
            Institution(id=1, official_code="INST001", name="One", status="ACTIVE"),
            Institution(id=2, official_code="INST002", name="Two", status="ACTIVE"),
        ]
    )
    session.commit()
    yield session
    session.close()


@pytest.fixture
def client(session_factory, db) -> Generator[TestClient, None, None]:
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


def _account(db: Session, username: str, institution_id: int, role: str) -> None:
    create_user(
        db,
        username=username,
        password=PASSWORD,
        institution_id=institution_id,
        roles=[role],
    )


def _sign_in(client: TestClient, username: str) -> TestClient:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return client


def _validated_batch(client: TestClient, rows: str, institution_id: int = 1) -> int:
    created = client.post(
        "/api/v1/batches",
        json={
            "institution_id": institution_id,
            "academic_year": "2026-2027",
            "schema_version": "v1",
        },
    )
    assert created.status_code == 201, created.text
    batch_id = created.json()["batch_id"]
    validated = client.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", rows.encode(), "text/csv")},
    )
    assert validated.status_code == 200, validated.text
    return batch_id


MATCHING_ROWS = (
    HEADER
    + "SYN-00001,CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
    + "SYN-00002,CS-UG-FT-S1,2026-2027,CAP_OBC,FIRST_YEAR,DOMESTIC_APAAR\n"
)
PARTIAL_ROWS = MATCHING_ROWS + (
    "SYN-00003,EE-UG-FT-S1,2026-2027,CAP_SC,FIRST_YEAR,DOMESTIC_APAAR\n"
)


@pytest.fixture
def operator(client, db) -> TestClient:
    _account(db, "operator1", 1, ROLE_OPERATOR)
    _account(db, "nodal1", 1, ROLE_NODAL)
    _account(db, "operator2", 2, ROLE_OPERATOR)
    seed_demo(db, institution_id=1)
    return _sign_in(client, "operator1")


# --- references -------------------------------------------------------------


def test_snapshots_and_policies_are_listed_for_the_session_institution(operator):
    snapshots = operator.get("/api/v1/reconciliation/snapshots")
    assert snapshots.status_code == 200, snapshots.text
    body = snapshots.json()
    assert len(body["snapshots"]) == 1
    assert body["snapshots"][0]["status"] == "APPROVED"
    assert body["snapshots"][0]["entry_count"] == 15
    assert "SYNTHETIC" in body["snapshots"][0]["source_ref"]

    policies = operator.get("/api/v1/reconciliation/policies")
    assert policies.status_code == 200, policies.text
    rules = policies.json()["policies"][0]
    assert rules["status"] == "ACTIVE"
    assert rules["rules"]["link_fields"] == [
        "course_code",
        "academic_year",
        "seat_category",
    ]


def test_references_do_not_leak_across_institutions(client, db, operator):
    _sign_in(client, "operator2")
    assert client.get("/api/v1/reconciliation/snapshots").json() == {"snapshots": []}
    assert client.get("/api/v1/reconciliation/policies").json() == {"policies": []}


# --- running ----------------------------------------------------------------


def test_run_persists_outcomes_and_summary(operator):
    batch_id = _validated_batch(operator, PARTIAL_ROWS)

    response = operator.post(f"/api/v1/batches/{batch_id}/reconcile")
    assert response.status_code == 200, response.text
    run = response.json()

    assert run["run_number"] == 1
    assert run["status"] == "SUCCEEDED"
    assert run["snapshot_version"] == 1
    assert run["policy_version"] == 1
    assert len(run["digest"]) == 64
    assert run["row_count"] == 3
    assert run["outcome_counts"] == {"MATCHED": 2, "UNMATCHED": 1}

    outcomes = {row["row_number"]: row for row in run["outcomes"]}
    assert outcomes[2]["outcome"] == "MATCHED"
    assert outcomes[2]["local_ref"] == "SYN-00001"
    assert outcomes[4]["outcome"] == "UNMATCHED"
    assert "no approved entry" in outcomes[4]["reasons"][0]

    # The digest is a real hash, and the totals line reports capacity honestly.
    assert "Approved lines underfilled" in run["totals"]

    detail = operator.get(f"/api/v1/reconciliation/runs/{run['run_id']}")
    assert detail.status_code == 200
    assert len(detail.json()["outcomes"]) == 3


def test_rerunning_same_inputs_produces_the_same_digest(operator):
    batch_id = _validated_batch(operator, PARTIAL_ROWS)

    first = operator.post(f"/api/v1/batches/{batch_id}/reconcile").json()
    second = operator.post(f"/api/v1/batches/{batch_id}/reconcile").json()

    assert first["digest"] == second["digest"]
    assert second["run_number"] == first["run_number"] + 1

    history = operator.get(
        "/api/v1/reconciliation/runs", params={"batch_id": batch_id}
    ).json()["runs"]
    assert [run["run_number"] for run in history] == [2, 1]
    assert len({run["run_id"] for run in history}) == 2


def _policy_with_different_duplicate_key(db: Session) -> int:
    """A v2 policy that treats repeated course/entry-level pairs as duplicates."""
    import json

    from app.fixtures.demo import DEMO_POLICY_RULES, rules_checksum

    from datetime import datetime, timezone

    rules = dict(DEMO_POLICY_RULES)
    rules["duplicate_key_fields"] = ["course_code", "entry_level"]
    policy = ReconciliationPolicy(
        institution_id=1,
        version=2,
        name="Synthetic demo policy v2",
        description="Synthetic duplicate-key variant for tests.",
        status=ReconciliationPolicy.STATUS_ACTIVE,
        rules=json.dumps(rules, sort_keys=True, separators=(",", ":")),
        rules_checksum=rules_checksum(rules),
        created_at=datetime.now(timezone.utc),
        created_by="test",
        activated_at=datetime.now(timezone.utc),
        activated_by="test",
    )
    db.add(policy)
    db.commit()
    return policy.id


def test_duplicate_rows_are_reported_not_dropped(operator, db):
    rows = (
        HEADER
        + "SYN-00001,CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
        + "SYN-00002,CE-UG-FT-S1,2026-2027,CAP_OBC,FIRST_YEAR,DOMESTIC_APAAR\n"
    )
    batch_id = _validated_batch(operator, rows)
    policy_id = _policy_with_different_duplicate_key(db)

    run = operator.post(
        f"/api/v1/batches/{batch_id}/reconcile", params={"policy_id": policy_id}
    ).json()
    assert run["policy_version"] == 2
    assert run["row_count"] == 2
    assert run["outcome_counts"]["DUPLICATE_CANDIDATE"] == 1
    assert len(run["outcomes"]) == 2


def test_confirmed_batch_can_be_reconciled(operator):
    created = operator.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "schema_version": "v1",
        },
    ).json()
    batch_id = created["batch_id"]
    operator.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", MATCHING_ROWS.encode(), "text/csv")},
    )
    confirm = operator.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": created["idempotency_key"]},
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["state"] == "SUBMITTED_FOR_REVIEW"

    run = operator.post(f"/api/v1/batches/{batch_id}/reconcile")
    assert run.status_code == 200, run.text
    assert run.json()["batch_state"] == "SUBMITTED_FOR_REVIEW"


# --- refusal paths ----------------------------------------------------------


def test_unvalidated_batch_is_refused_with_an_actionable_message(operator):
    created = operator.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "schema_version": "v1",
        },
    ).json()

    response = operator.post(f"/api/v1/batches/{created['batch_id']}/reconcile")
    assert response.status_code == 400
    assert "CREATED" in response.json()["detail"]
    assert "VALIDATED" in response.json()["detail"]


def test_missing_snapshot_explains_what_is_needed(client, db):
    _account(db, "operator3", 2, ROLE_OPERATOR)
    sign_in = _sign_in(client, "operator3")
    batch_id = _validated_batch(sign_in, MATCHING_ROWS, institution_id=2)

    response = sign_in.post(f"/api/v1/batches/{batch_id}/reconcile")
    assert response.status_code == 400
    assert "snapshot" in response.json()["detail"].lower()


def test_inactive_policy_cannot_be_used(operator, db):
    batch_id = _validated_batch(operator, MATCHING_ROWS)
    policy = db.query(ReconciliationPolicy).one()
    policy.status = ReconciliationPolicy.STATUS_DRAFT
    db.commit()

    response = operator.post(
        f"/api/v1/batches/{batch_id}/reconcile",
        params={"policy_id": policy.id},
    )
    assert response.status_code == 400
    assert "policy" in response.json()["detail"].lower()


def test_cross_institution_reconciliation_is_denied(client, db, operator):
    batch_id = _validated_batch(operator, MATCHING_ROWS)
    _sign_in(client, "operator2")

    assert (
        client.post(f"/api/v1/batches/{batch_id}/reconcile").status_code == 404
    )
    assert (
        client.get(
            "/api/v1/reconciliation/runs", params={"batch_id": batch_id}
        ).status_code
        == 404
    )


def test_auditor_can_read_but_not_run(client, db, operator):
    batch_id = _validated_batch(operator, MATCHING_ROWS)
    run = operator.post(f"/api/v1/batches/{batch_id}/reconcile").json()

    _account(db, "auditor1", 1, ROLE_AUDITOR)
    auditor = _sign_in(client, "auditor1")

    assert auditor.get("/api/v1/reconciliation/runs").status_code == 200
    assert (
        auditor.get(f"/api/v1/reconciliation/runs/{run['run_id']}").status_code == 200
    )
    assert (
        auditor.post(f"/api/v1/batches/{batch_id}/reconcile").status_code == 403
    )
