from app.fixtures.synthetic import SYNTHETIC_ID_PREFIX, generate_synthetic_intake_records


def test_generate_synthetic_intake_records_is_deterministic() -> None:
    assert generate_synthetic_intake_records(5) == generate_synthetic_intake_records(5)


def test_generate_synthetic_intake_records_respects_count() -> None:
    assert len(generate_synthetic_intake_records(3)) == 3
    assert generate_synthetic_intake_records(0) == []


def test_synthetic_fixtures_use_synthetic_identifier_prefix() -> None:
    records = generate_synthetic_intake_records(2)
    assert all(record["apaar_id"].startswith(SYNTHETIC_ID_PREFIX) for record in records)
    assert all(record["validation_state"] == "SYNTHETIC" for record in records)
