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
    assert rows[0][0] == "0001_initial_schema"


def test_settings_read_database_url_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    assert Settings().database_url == "sqlite:///:memory:"
