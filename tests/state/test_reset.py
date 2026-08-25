import sqlite3
from pathlib import Path

from bounded_agent.config import Settings
from bounded_agent.state import connect_database, reset_scenario_environment, run_database_path


def count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    return connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def open_reset_db(path: Path) -> sqlite3.Connection:
    return connect_database(path)


def test_run_database_path_uses_run_directory(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")

    assert run_database_path("run_001", settings) == tmp_path / "runs" / "run_001" / "state.db"


def test_reset_scenario_environment_creates_seeded_database(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")

    result = reset_scenario_environment("support_001", "run_001", settings)
    connection = open_reset_db(result.db_path)

    assert result.scenario_id == "support_001"
    assert result.run_id == "run_001"
    assert count_rows(connection, "tickets") == 10
    assert count_rows(connection, "customers") == 9
    assert count_rows(connection, "orders") == 9
    assert count_rows(connection, "policies") == 6


def test_reset_scenario_environment_clears_stale_mutation_state(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    first = reset_scenario_environment("support_001", "run_001", settings)
    connection = open_reset_db(first.db_path)
    connection.execute(
        """
        INSERT INTO audit_log (
            audit_id,
            timestamp,
            actor,
            action,
            target_type,
            target_id
        )
        VALUES ('audit_001', '2026-08-25T00:00:00Z', 'test', 'mutate', 'ticket', 't_001')
        """
    )
    connection.commit()
    connection.close()

    second = reset_scenario_environment("support_001", "run_001", settings)
    connection = open_reset_db(second.db_path)

    assert count_rows(connection, "audit_log") == 0
    assert count_rows(connection, "idempotency_keys") == 0


def test_reset_configures_scenario_injected_failures(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    result = reset_scenario_environment("support_006", "run_006", settings)
    connection = open_reset_db(result.db_path)

    failure = connection.execute(
        """
        SELECT scenario_id, tool_name, failure_type, remaining_count
        FROM injected_failures
        WHERE scenario_id = 'support_006'
        """
    ).fetchone()

    assert dict(failure) == {
        "scenario_id": "support_006",
        "tool_name": "fetch_order",
        "failure_type": "timeout",
        "remaining_count": 1,
    }


def test_reset_preloads_denied_approval_fixture(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    result = reset_scenario_environment("support_007", "run_007", settings)
    connection = open_reset_db(result.db_path)

    approval = connection.execute(
        """
        SELECT action_type, status, decision
        FROM approvals
        WHERE scenario_id = 'support_007'
        """
    ).fetchone()

    assert dict(approval) == {
        "action_type": "apply_refund",
        "status": "denied",
        "decision": "denied",
    }


def test_reset_preloads_approved_approval_fixture(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    result = reset_scenario_environment("support_009", "run_009", settings)
    connection = open_reset_db(result.db_path)

    approval = connection.execute(
        """
        SELECT action_type, status, decision, target_json
        FROM approvals
        WHERE scenario_id = 'support_009'
        """
    ).fetchone()

    assert approval["action_type"] == "apply_refund"
    assert approval["status"] == "approved"
    assert approval["decision"] == "approved"
    assert "ch_009_b" in approval["target_json"]


def test_reset_same_scenario_twice_produces_identical_initial_counts(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    first = reset_scenario_environment("support_008", "run_008", settings)
    first_connection = open_reset_db(first.db_path)
    first_counts = {
        table: count_rows(first_connection, table)
        for table in ["tickets", "customers", "orders", "charges", "policies", "injected_failures"]
    }
    first_connection.close()

    second = reset_scenario_environment("support_008", "run_008", settings)
    second_connection = open_reset_db(second.db_path)
    second_counts = {
        table: count_rows(second_connection, table)
        for table in ["tickets", "customers", "orders", "charges", "policies", "injected_failures"]
    }

    assert second_counts == first_counts
