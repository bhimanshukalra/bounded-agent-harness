import sqlite3

from bounded_agent.config import Settings
from bounded_agent.domain import ErrorType
from bounded_agent.state import connect_database, list_injected_failures, reset_scenario_environment
from bounded_agent.tools import ToolCall, ToolExecutionContext, build_default_registry


def reset_connection(tmp_path, scenario_id: str = "support_001") -> sqlite3.Connection:
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    result = reset_scenario_environment(scenario_id, f"{scenario_id}_run", settings)
    return connect_database(result.db_path)


def count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    return connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def test_fetch_ticket_returns_ticket_from_default_registry(tmp_path):
    connection = reset_connection(tmp_path)
    registry = build_default_registry()
    context = ToolExecutionContext(run_id="run_001", connection=connection)
    call = ToolCall(tool_name="fetch_ticket", arguments={"ticket_id": "t_001"})

    result = registry.execute(call, context)

    assert result.ok is True
    assert result.result["ticket"]["ticket_id"] == "t_001"
    assert result.result["ticket"]["untrusted_content"] is True
    assert result.metadata == {"source": "mock_support_environment"}


def test_fetch_customer_returns_customer_from_default_registry(tmp_path):
    connection = reset_connection(tmp_path)
    registry = build_default_registry()
    context = ToolExecutionContext(run_id="run_001", connection=connection)
    call = ToolCall(tool_name="fetch_customer", arguments={"customer_id": "c_005"})

    result = registry.execute(call, context)

    assert result.ok is True
    assert result.result["customer"]["customer_id"] == "c_005"
    assert result.result["customer"]["risk_flags"] == ["manual_policy_review"]


def test_fetch_order_returns_order_and_charges_from_default_registry(tmp_path):
    connection = reset_connection(tmp_path)
    registry = build_default_registry()
    context = ToolExecutionContext(run_id="run_001", connection=connection)
    call = ToolCall(tool_name="fetch_order", arguments={"order_id": "o_001"})

    result = registry.execute(call, context)

    assert result.ok is True
    assert result.result["order"]["order_id"] == "o_001"
    assert [charge["charge_id"] for charge in result.result["charges"]] == ["ch_001_a", "ch_001_b"]


def test_search_policy_returns_matching_policies_from_default_registry(tmp_path):
    connection = reset_connection(tmp_path)
    registry = build_default_registry()
    context = ToolExecutionContext(run_id="run_001", connection=connection)
    call = ToolCall(tool_name="search_policy", arguments={"query": "approval required"})

    result = registry.execute(call, context)

    assert result.ok is True
    assert [policy["policy_id"] for policy in result.result["policies"]] == [
        "policy_approval_required_v1",
        "policy_duplicate_charge_refund_v1",
    ]


def test_read_tools_return_structured_not_found_errors(tmp_path):
    connection = reset_connection(tmp_path)
    registry = build_default_registry()
    context = ToolExecutionContext(run_id="run_001", connection=connection)
    call = ToolCall(tool_name="fetch_order", arguments={"order_id": "o_missing"})

    result = registry.execute(call, context)

    assert result.ok is False
    assert result.error.type is ErrorType.NOT_FOUND
    assert result.error.details == {"order_id": "o_missing"}
    assert result.metadata == {"source": "mock_support_environment"}


def test_read_tools_do_not_write_audit_or_idempotency_records(tmp_path):
    connection = reset_connection(tmp_path)
    registry = build_default_registry()
    context = ToolExecutionContext(run_id="run_001", connection=connection)

    before_counts = {
        "audit_log": count_rows(connection, "audit_log"),
        "idempotency_keys": count_rows(connection, "idempotency_keys"),
        "ticket_comments": count_rows(connection, "ticket_comments"),
    }
    registry.execute(ToolCall(tool_name="fetch_ticket", arguments={"ticket_id": "t_001"}), context)
    registry.execute(ToolCall(tool_name="fetch_customer", arguments={"customer_id": "c_001"}), context)
    registry.execute(ToolCall(tool_name="fetch_order", arguments={"order_id": "o_001"}), context)
    registry.execute(ToolCall(tool_name="search_policy", arguments={"query": "refund"}), context)
    after_counts = {
        "audit_log": count_rows(connection, "audit_log"),
        "idempotency_keys": count_rows(connection, "idempotency_keys"),
        "ticket_comments": count_rows(connection, "ticket_comments"),
    }

    assert after_counts == before_counts


def test_fetch_order_consumes_one_injected_timeout_then_succeeds(tmp_path):
    connection = reset_connection(tmp_path, "support_006")
    registry = build_default_registry()
    context = ToolExecutionContext(
        run_id="run_006",
        scenario_id="support_006",
        connection=connection,
    )
    call = ToolCall(tool_name="fetch_order", arguments={"order_id": "o_006"})

    first = registry.execute(call, context)
    second = registry.execute(call, context)
    failures = list_injected_failures(connection, scenario_id="support_006")

    assert first.ok is False
    assert first.error.type is ErrorType.TIMEOUT
    assert first.error.retryable is True
    assert first.metadata == {"source": "injected_failure"}
    assert second.ok is True
    assert second.result["order"]["order_id"] == "o_006"
    assert failures[0]["remaining_count"] == 0
