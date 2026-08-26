import sqlite3

from bounded_agent.config import Settings
from bounded_agent.domain import ErrorType
from bounded_agent.state import connect_database, list_injected_failures, reset_scenario_environment
from bounded_agent.tools import ToolCall, ToolExecutionContext, build_default_registry


def reset_connection(tmp_path, scenario_id: str) -> sqlite3.Connection:
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    result = reset_scenario_environment(scenario_id, f"{scenario_id}_run", settings)
    return connect_database(result.db_path)


def execute(connection: sqlite3.Connection, tool_name: str, arguments: dict, **context_kwargs):
    context = ToolExecutionContext(
        run_id=context_kwargs.pop("run_id", "run_001"),
        connection=connection,
        **context_kwargs,
    )
    return build_default_registry().execute(ToolCall(tool_name=tool_name, arguments=arguments), context)


def count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    return connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def test_support_006_forces_one_fetch_order_timeout_through_registry(tmp_path):
    connection = reset_connection(tmp_path, "support_006")
    arguments = {"order_id": "o_006"}

    first = execute(
        connection,
        "fetch_order",
        arguments,
        run_id="support_006_run",
        scenario_id="support_006",
    )
    second = execute(
        connection,
        "fetch_order",
        arguments,
        run_id="support_006_run",
        scenario_id="support_006",
    )
    failures = list_injected_failures(connection, scenario_id="support_006")

    assert first.ok is False
    assert first.error.type is ErrorType.TIMEOUT
    assert first.error.retryable is True
    assert first.error.details["failure_type"] == "timeout"
    assert second.ok is True
    assert second.result["order"]["order_id"] == "o_006"
    assert failures[0]["remaining_count"] == 0


def test_support_009_post_side_effect_refund_failure_replays_without_duplicate_refund(tmp_path):
    connection = reset_connection(tmp_path, "support_009")
    arguments = {
        "charge_id": "ch_009_b",
        "amount": 49.0,
        "currency": "USD",
        "reason": "duplicate_charge",
    }

    first = execute(
        connection,
        "apply_refund",
        arguments,
        run_id="support_009_run",
        scenario_id="support_009",
        approval_id="support_009:approval:refund",
        idempotency_key="refund:key:009",
    )
    second = execute(
        connection,
        "apply_refund",
        arguments,
        run_id="support_009_run",
        scenario_id="support_009",
        approval_id="support_009:approval:refund",
        idempotency_key="refund:key:009",
    )
    charge = connection.execute(
        "SELECT status, refunded_amount FROM charges WHERE charge_id = 'ch_009_b'"
    ).fetchone()
    failures = list_injected_failures(connection, scenario_id="support_009")

    assert first.ok is False
    assert first.error.type is ErrorType.TRANSIENT_ERROR
    assert first.error.retryable is True
    assert first.error.details["failure_type"] == "transient_error_after_side_effect"
    assert first.metadata == {"source": "injected_failure"}
    assert charge["status"] == "refunded"
    assert charge["refunded_amount"] == 49.0
    assert count_rows(connection, "idempotency_keys") == 1
    assert second.ok is True
    assert second.metadata == {"source": "idempotency_replay"}
    assert second.result["charge_id"] == "ch_009_b"
    assert failures[0]["remaining_count"] == 0
