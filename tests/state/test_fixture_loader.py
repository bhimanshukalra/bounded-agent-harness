import sqlite3

import pytest

from bounded_agent.config import Settings
from bounded_agent.state import (
    connect_database,
    initialize_schema,
    load_fixture_file,
    require_sections,
    seed_base_fixtures,
    seed_policy_fixture,
    seed_support_fixture,
)


def count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    return connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def test_load_fixture_file_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="fixture file not found"):
        load_fixture_file(tmp_path / "missing.json")


def test_require_sections_rejects_malformed_fixture():
    with pytest.raises(ValueError, match="customers"):
        require_sections({"orders": []}, {"customers", "orders"})


def test_seed_base_fixtures_loads_support_and_policy_data(tmp_path):
    settings = Settings(_env_file=None)
    connection = connect_database(tmp_path / "state.db")
    initialize_schema(connection)

    seed_base_fixtures(
        connection,
        settings.fixtures_dir / "support_seed.json",
        settings.fixtures_dir / "policies.json",
    )

    assert count_rows(connection, "customers") == 9
    assert count_rows(connection, "orders") == 9
    assert count_rows(connection, "charges") == 14
    assert count_rows(connection, "tickets") == 10
    assert count_rows(connection, "policies") == 6


def test_seed_support_fixture_persists_json_fields_deterministically(tmp_path):
    settings = Settings(_env_file=None)
    connection = connect_database(tmp_path / "state.db")
    initialize_schema(connection)

    seed_support_fixture(connection, load_fixture_file(settings.fixtures_dir / "support_seed.json"))

    customer = connection.execute(
        "SELECT risk_flags_json FROM customers WHERE customer_id = 'c_005'"
    ).fetchone()
    ticket = connection.execute(
        "SELECT metadata_json FROM tickets WHERE ticket_id = 't_003'"
    ).fetchone()

    assert customer["risk_flags_json"] == '["manual_policy_review"]'
    assert ticket["metadata_json"] == '{"requested_order_id": "o_missing"}'


def test_seed_policy_fixture_persists_policy_hints(tmp_path):
    settings = Settings(_env_file=None)
    connection = connect_database(tmp_path / "state.db")
    initialize_schema(connection)

    seed_policy_fixture(connection, load_fixture_file(settings.fixtures_dir / "policies.json"))

    policy = connection.execute(
        """
        SELECT eligibility_hints_json
        FROM policies
        WHERE policy_id = 'policy_duplicate_charge_refund_v1'
        """
    ).fetchone()

    assert "approval required" in policy["eligibility_hints_json"]


def test_duplicate_primary_keys_fail_clearly(tmp_path):
    settings = Settings(_env_file=None)
    connection = connect_database(tmp_path / "state.db")
    initialize_schema(connection)
    fixture = load_fixture_file(settings.fixtures_dir / "support_seed.json")

    seed_support_fixture(connection, fixture)

    with pytest.raises(sqlite3.IntegrityError):
        seed_support_fixture(connection, fixture)


def test_loading_same_fixture_after_reset_produces_same_counts(tmp_path):
    settings = Settings(_env_file=None)
    db_path = tmp_path / "state.db"

    first = connect_database(db_path)
    initialize_schema(first)
    seed_base_fixtures(
        first,
        settings.fixtures_dir / "support_seed.json",
        settings.fixtures_dir / "policies.json",
    )
    first_counts = {
        table: count_rows(first, table)
        for table in ["customers", "orders", "charges", "tickets", "policies"]
    }
    first.close()

    db_path.unlink()

    second = connect_database(db_path)
    initialize_schema(second)
    seed_base_fixtures(
        second,
        settings.fixtures_dir / "support_seed.json",
        settings.fixtures_dir / "policies.json",
    )
    second_counts = {
        table: count_rows(second, table)
        for table in ["customers", "orders", "charges", "tickets", "policies"]
    }

    assert second_counts == first_counts
