"""Milestone 6: authentication, role checks, and institution isolation."""

import hashlib
import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Institution, User
from app.db.session import get_db
from app.main import app
from app.services.auth import (
    ROLE_AUDITOR,
    ROLE_NODAL,
    ROLE_OPERATOR,
    SESSION_COOKIE,
    hash_password,
    verify_password,
)

_tmp_db_fd, _tmp_db_path = tempfile.mkstemp(suffix=".db")
os.close(_tmp_db_fd)
_AUTH_DB_URL = f"sqlite:///{_tmp_db_path}"

PASSWORD = "Correct-Horse-Battery-Staple-1"


def _override_get_db() -> Generator[Session, None, None]:
    engine = create_engine(_AUTH_DB_URL, pool_pre_ping=True)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    from app.db import models  # noqa: F401
    from app.db.base import Base

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture
def db_session() -> Session:
    """Fresh schema plus two institutions to scope against."""
    engine = create_engine(_AUTH_DB_URL, pool_pre_ping=True)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    from app.db import models  # noqa: F401
    from app.db.base import Base

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    for inst_id, code, name in (
        (1, "INST001", "Test Institution One"),
        (2, "INST002", "Test Institution Two"),
    ):
        if db.get(Institution, inst_id) is None:
            db.add(
                Institution(
                    id=inst_id, official_code=code, name=name, status="ACTIVE"
                )
            )
    db.commit()
    yield db
    db.close()
    engine.dispose()


@pytest.fixture
def auth_env(db_session: Session):
    """Point the app at this module's database, then restore whatever was there."""
    saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = _override_get_db
    yield db_session
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


def _make_account(db: Session, username: str, institution_id: int, roles):
    from app.services.auth import create_user

    existing = db.execute(
        select(User).where(User.username == username)
    ).scalar_one_or_none()
    if existing is None:
        create_user(
            db,
            username=username,
            password=PASSWORD,
            institution_id=institution_id,
            roles=roles,
        )
    return username


def _session_row(db: Session, token: str):
    """The AuthSession row for a raw cookie value (there are several per DB)."""
    from app.db.models import AuthSession

    return db.execute(
        select(AuthSession).where(
            AuthSession.token_hash == hashlib.sha256(token.encode()).hexdigest()
        )
    ).scalar_one()


def _sign_in(username: str, password: str = PASSWORD) -> TestClient:
    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return client


def _create_batch(client: TestClient, institution_id: int) -> dict:
    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": institution_id,
            "academic_year": "2026-2027",
            "schema_version": "v1",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- password storage ------------------------------------------------------


def test_password_hash_round_trip() -> None:
    encoded = hash_password(PASSWORD)
    assert verify_password(PASSWORD, encoded)
    assert not verify_password(PASSWORD + "x", encoded)
    assert PASSWORD not in encoded


@pytest.mark.real_kdf
def test_password_hash_uses_configured_work_factor() -> None:
    """The configured production work factor must actually be usable.

    Other tests lower it for speed (see conftest.py); this one pins the real
    default and proves it round-trips.
    """
    from app.config import Settings, settings

    shipped_default = Settings.model_fields["password_hash_iterations"].default
    assert shipped_default == 600_000
    assert settings.password_hash_iterations == shipped_default

    encoded = hash_password(PASSWORD)
    assert encoded.split("$")[1] == str(shipped_default)
    assert verify_password(PASSWORD, encoded)


def test_password_verification_fails_closed() -> None:
    assert verify_password(PASSWORD, "") is False
    assert verify_password(PASSWORD, "not-a-hash") is False
    assert verify_password(PASSWORD, "pbkdf2_sha256$abc$zz$zz") is False
    assert verify_password("", hash_password(PASSWORD)) is False


# --- login / logout --------------------------------------------------------


def test_login_returns_identity_and_sets_httponly_cookie(auth_env) -> None:
    _make_account(auth_env, "operator1", 1, [ROLE_OPERATOR])
    client = _sign_in("operator1")

    cookie = client.cookies.get(SESSION_COOKIE)
    assert cookie, "session cookie was not set"

    me = client.get("/api/v1/auth/me").json()
    assert me["authenticated"] is True
    assert me["username"] == "operator1"
    assert me["institution_id"] == 1
    assert me["institution_name"] == "Test Institution One"
    assert ROLE_OPERATOR in me["roles"]

    # The cookie must not be readable from JavaScript.
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "operator1", "password": PASSWORD},
    )
    set_cookie = resp.headers.get("set-cookie", "").lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie

    # No credential material is ever echoed back.
    body = resp.text.lower()
    assert "password_hash" not in body
    assert PASSWORD.lower() not in body


def test_me_is_unauthenticated_without_a_cookie(auth_env) -> None:
    client = TestClient(app)
    me = client.get("/api/v1/auth/me").json()
    assert me["authenticated"] is False
    assert me["roles"] == []
    assert me["institution_id"] == 0


def test_unknown_user_and_wrong_password_are_indistinguishable(auth_env) -> None:
    _make_account(auth_env, "operator1", 1, [ROLE_OPERATOR])
    client = TestClient(app)

    wrong = client.post(
        "/api/v1/auth/login",
        json={"username": "operator1", "password": "nope"},
    )
    missing = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "password": "nope"},
    )

    assert wrong.status_code == missing.status_code == 401
    assert wrong.json()["detail"] == missing.json()["detail"]
    assert not client.cookies.get(SESSION_COOKIE)


def test_logout_revokes_the_session_server_side(auth_env) -> None:
    _make_account(auth_env, "operator1", 1, [ROLE_OPERATOR])
    client = _sign_in("operator1")
    stolen_token = client.cookies.get(SESSION_COOKIE)

    assert client.post("/api/v1/auth/logout").status_code == 200

    # Replaying the original cookie must not restore the session: revocation
    # lives in the database, not just in the browser.
    replay = TestClient(app)
    replay.cookies.set(SESSION_COOKIE, stolen_token)
    assert replay.get("/api/v1/auth/me").json()["authenticated"] is False
    assert replay.get("/api/v1/batches/1").status_code == 401


def test_session_token_is_stored_hashed(auth_env) -> None:
    from app.db.models import AuthSession

    _make_account(auth_env, "operator1", 1, [ROLE_OPERATOR])
    client = _sign_in("operator1")
    raw = client.cookies.get(SESSION_COOKIE)

    row = _session_row(auth_env, raw)
    assert row.token_hash == hashlib.sha256(raw.encode()).hexdigest()
    # The raw token appears nowhere in the table.
    all_hash_text = " ".join(
        r.token_hash
        for r in auth_env.execute(select(AuthSession)).scalars()
    )
    assert raw not in all_hash_text


def test_expired_session_is_rejected(auth_env) -> None:
    from app.db.models import AuthSession

    _make_account(auth_env, "operator1", 1, [ROLE_OPERATOR])
    client = _sign_in("operator1")

    row = _session_row(auth_env, client.cookies.get(SESSION_COOKIE))
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    auth_env.commit()

    assert client.get("/api/v1/auth/me").json()["authenticated"] is False
    assert client.get("/api/v1/batches/1").status_code == 401


# --- role checks -----------------------------------------------------------


def test_role_without_write_permission_cannot_modify_batches(auth_env) -> None:
    _make_account(auth_env, "operator1", 1, [ROLE_OPERATOR])
    _make_account(auth_env, "nodal1", 1, [ROLE_NODAL])
    batch = _create_batch(_sign_in("operator1"), 1)

    nodal = _sign_in("nodal1")

    # A Nodal Officer may read the batch...
    assert nodal.get(f"/api/v1/batches/{batch['batch_id']}").status_code == 200
    # ...but may not upload or confirm it.
    resp = nodal.post(
        f"/api/v1/batches/{batch['batch_id']}/validate",
        files={"file": ("roster.csv", b"local_ref\nX\n", "text/csv")},
    )
    assert resp.status_code == 403
    assert "role" in resp.json()["detail"].lower()

    resp = nodal.post(
        f"/api/v1/batches/{batch['batch_id']}/confirm",
        json={"idempotency_key": batch["idempotency_key"]},
    )
    assert resp.status_code == 403

    resp = nodal.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "schema_version": "v1",
        },
    )
    assert resp.status_code == 403


def test_account_with_no_roles_can_do_nothing(auth_env) -> None:
    _make_account(auth_env, "auditor1", 1, [ROLE_AUDITOR])
    client = _sign_in("auditor1")
    assert client.get("/api/v1/auth/me").json()["authenticated"] is True

    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "schema_version": "v1",
        },
    )
    assert resp.status_code == 403
    assert client.get("/api/v1/batches/1").status_code == 403


# --- institution isolation -------------------------------------------------


def _csv() -> bytes:
    return (
        b"local_ref,course_code,academic_year,seat_category,entry_level,identity_status\n"
        b"SYN-00001,CE-UG-FT-S1,2026-2027,CAP_GENERAL,FIRST_YEAR,DOMESTIC_APAAR\n"
    )


def test_cross_institution_access_is_denied(auth_env) -> None:
    """T-07: another institution cannot read, modify, or confirm a batch."""
    _make_account(auth_env, "operator1", 1, [ROLE_OPERATOR])
    _make_account(auth_env, "operator2", 2, [ROLE_OPERATOR])

    owner = _sign_in("operator1")
    batch = _create_batch(owner, 1)
    batch_id = batch["batch_id"]
    owner.post(
        f"/api/v1/batches/{batch_id}/validate",
        files={"file": ("roster.csv", _csv(), "text/csv")},
    )

    intruder = _sign_in("operator2")

    # Reading another institution's batch reports 404, not 403, so the
    # response does not confirm the record exists.
    read = intruder.get(f"/api/v1/batches/{batch_id}")
    assert read.status_code == 404
    assert read.json()["detail"] == f"Batch {batch_id} not found."

    # Writes are refused before any row is staged or any state changes.
    assert (
        intruder.post(
            f"/api/v1/batches/{batch_id}/validate",
            files={"file": ("roster.csv", _csv(), "text/csv")},
        ).status_code
        == 404
    )
    assert (
        intruder.post(
            f"/api/v1/batches/{batch_id}/confirm",
            json={"idempotency_key": batch["idempotency_key"]},
        ).status_code
        == 404
    )
    # Naming institution 1 in the body cannot widen scope either.
    assert (
        intruder.post(
            "/api/v1/batches",
            json={
                "institution_id": 1,
                "academic_year": "2026-2027",
                "schema_version": "v1",
            },
        ).status_code
        == 403
    )

    # The victim's batch is untouched and still confirmable by its owner.
    owner_state = owner.get(f"/api/v1/batches/{batch_id}").json()
    assert owner_state["state"] == "VALIDATED"
    assert owner_state["institution_id"] == 1
    confirm = owner.post(
        f"/api/v1/batches/{batch_id}/confirm",
        json={"idempotency_key": batch["idempotency_key"]},
    )
    assert confirm.status_code == 200


def test_batches_are_filed_under_the_session_institution(auth_env) -> None:
    """The body cannot file a batch under an institution the caller lacks."""
    _make_account(auth_env, "operator2", 2, [ROLE_OPERATOR])
    client = _sign_in("operator2")

    batch = _create_batch(client, 2)
    assert batch["batch_id"] > 0

    resp = client.post(
        "/api/v1/batches",
        json={
            "institution_id": 1,
            "academic_year": "2026-2027",
            "schema_version": "v1",
        },
    )
    assert resp.status_code == 403
