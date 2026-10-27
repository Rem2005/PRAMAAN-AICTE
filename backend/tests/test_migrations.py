from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config import Settings

EXPECTED_TABLES = {
    "institutions",
    "users",
    "user_role_assignments",
    "approved_intake_snapshots",
    "submission_batches",
    "staged_enrolments",
}


def _migration_config(tmp_path) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_path}/pramaan_migration_test.db")
    return cfg


def test_migration_upgrade_creates_expected_tables(tmp_path) -> None:
    cfg = _migration_config(tmp_path)
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{tmp_path}/pramaan_migration_test.db")
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"Missing expected tables: {sorted(missing)}"


def test_migration_creates_unique_constraint_on_institutions_official_code(tmp_path) -> None:
    cfg = _migration_config(tmp_path)
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{tmp_path}/pramaan_migration_test.db")
    inspector = inspect(engine)
    constraints = inspector.get_unique_constraints("institutions")
    assert any(constraint.get("column_names") == ["official_code"] for constraint in constraints)


def test_migration_downgrade_and_upgrade_are_repeatable(tmp_path) -> None:
    cfg = _migration_config(tmp_path)
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")  # second upgrade against head is a no-op success
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


def test_migration_version_tracking(tmp_path) -> None:
    cfg = _migration_config(tmp_path)
    command.upgrade(cfg, "head")
    engine = create_engine(f"sqlite:///{tmp_path}/pramaan_migration_test.db")
    with engine.begin() as connection:
        result = connection.execute(text("SELECT version_num FROM alembic_version"))
        rows = list(result)
    assert len(rows) == 1
    assert rows[0][0] in ("0007_batch_source_filename", "0008_identity_review_models")


def test_migration_adds_batch_academic_year_and_staged_indexes(tmp_path) -> None:
    cfg = _migration_config(tmp_path)
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{tmp_path}/pramaan_migration_test.db")
    inspector = inspect(engine)

    batch_columns = {c["name"] for c in inspector.get_columns("submission_batches")}
    assert "academic_year" in batch_columns
    assert "source_filename" in batch_columns

    staged_indexes = {i["name"] for i in inspector.get_indexes("staged_enrolments")}
    assert "uq_staged_enrolments_batch_row" in staged_indexes
    # Partial index: only VALID rows are unique on (batch_id, local_ref).
    assert "uq_staged_enrolments_batch_valid_local_ref" in staged_indexes

    local_ref = [
        c
        for c in inspector.get_columns("staged_enrolments")
        if c["name"] == "local_ref"
    ][0]
    assert local_ref["nullable"] is True


def test_migration_creates_auth_schema(tmp_path) -> None:
    cfg = _migration_config(tmp_path)
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{tmp_path}/pramaan_migration_test.db")
    inspector = inspect(engine)

    assert "auth_sessions" in set(inspector.get_table_names())

    user_columns = {c["name"] for c in inspector.get_columns("users")}
    assert {"username", "password_hash"} <= user_columns

    user_indexes = {i["name"] for i in inspector.get_indexes("users")}
    assert "uq_users_username" in user_indexes

    session_indexes = {
        i["name"] for i in inspector.get_indexes("auth_sessions")
    }
    assert "uq_auth_sessions_token_hash" in session_indexes


def test_settings_read_database_url_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    assert Settings().database_url == "sqlite:///:memory:"
