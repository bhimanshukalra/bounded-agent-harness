import sqlite3

import pytest

from bounded_agent.state import REQUIRED_TABLES, connect_database, initialize_schema, list_tables


def table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def test_initialize_schema_creates_required_tables(tmp_path):
    connection = connect_database(tmp_path / "state.db")
    initialize_schema(connection)

    assert REQUIRED_TABLES.issubset(list_tables(connection))


def test_initialize_schema_is_idempotent(tmp_path):
    connection = connect_database(tmp_path / "state.db")

    initialize_schema(connection)
    initialize_schema(connection)

    assert REQUIRED_TABLES.issubset(list_tables(connection))


def test_schema_enables_foreign_keys(tmp_path):
    connection = connect_database(tmp_path / "state.db")
    initialize_schema(connection)

    enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]

    assert enabled == 1


def test_core_tables_have_expected_columns(tmp_path):
    connection = connect_database(tmp_path / "state.db")
    initialize_schema(connection)

    assert {
        "ticket_id",
        "customer_id",
        "order_id",
        "category",
        "status",
        "subject",
        "body",
        "untrusted_content",
    }.issubset(table_columns(connection, "tickets"))
    assert {
        "customer_id",
        "account_status",
        "support_tier",
        "risk_flags_json",
        "masked_email",
    }.issubset(table_columns(connection, "customers"))
    assert {
        "order_id",
        "customer_id",
        "status",
        "refund_status",
    }.issubset(table_columns(connection, "orders"))
    assert {
        "charge_id",
        "order_id",
        "amount",
        "currency",
        "status",
        "refunded_amount",
    }.issubset(table_columns(connection, "charges"))


def test_supporting_tables_have_expected_columns(tmp_path):
    connection = connect_database(tmp_path / "state.db")
    initialize_schema(connection)

    assert {
        "policy_id",
        "category",
        "title",
        "body",
        "version",
        "eligibility_hints_json",
    }.issubset(table_columns(connection, "policies"))
    assert {
        "approval_id",
        "run_id",
        "ticket_id",
        "action_type",
        "status",
        "target_json",
        "proposed_arguments_json",
    }.issubset(table_columns(connection, "approvals"))
    assert {
        "audit_id",
        "timestamp",
        "actor",
        "action",
        "target_type",
        "target_id",
        "payload_json",
        "idempotency_key",
    }.issubset(table_columns(connection, "audit_log"))
    assert {
        "idempotency_key",
        "tool_name",
        "target_type",
        "target_id",
        "argument_hash",
        "result_json",
    }.issubset(table_columns(connection, "idempotency_keys"))
    assert {
        "failure_id",
        "scenario_id",
        "tool_name",
        "failure_type",
        "remaining_count",
    }.issubset(table_columns(connection, "injected_failures"))


def test_foreign_key_constraints_are_enforced(tmp_path):
    connection = connect_database(tmp_path / "state.db")
    initialize_schema(connection)

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT INTO orders (order_id, customer_id, status)
            VALUES ('o_missing_customer', 'c_missing', 'paid')
            """
        )


def test_check_constraints_are_enforced(tmp_path):
    connection = connect_database(tmp_path / "state.db")
    initialize_schema(connection)

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT INTO injected_failures (
                failure_id,
                scenario_id,
                tool_name,
                failure_type,
                remaining_count
            )
            VALUES ('failure_001', 'support_001', 'fetch_order', 'timeout', -1)
            """
        )


def test_connect_database_creates_parent_directories(tmp_path):
    db_path = tmp_path / "nested" / "run" / "state.db"

    connection = connect_database(db_path)
    initialize_schema(connection)

    assert db_path.exists()
