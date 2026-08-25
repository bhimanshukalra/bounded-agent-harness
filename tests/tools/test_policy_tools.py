import sqlite3

from bounded_agent.config import Settings
from bounded_agent.domain import ErrorType
from bounded_agent.state import connect_database, reset_scenario_environment
from bounded_agent.tools import ToolCall, ToolExecutionContext, build_default_registry


def reset_connection(tmp_path, scenario_id: str = "support_001") -> sqlite3.Connection:
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    result = reset_scenario_environment(scenario_id, f"{scenario_id}_run", settings)
    return connect_database(result.db_path)


def check_refund_policy(connection: sqlite3.Connection, ticket_id: str, order_id: str):
    registry = build_default_registry()
    context = ToolExecutionContext(run_id="run_001", connection=connection)
    call = ToolCall(
        tool_name="check_refund_policy",
        arguments={"ticket_id": ticket_id, "order_id": order_id},
    )
    return registry.execute(call, context)


def test_check_refund_policy_marks_duplicate_successful_charges_eligible(tmp_path):
    connection = reset_connection(tmp_path)

    result = check_refund_policy(connection, "t_001", "o_001")

    assert result.ok is True
    assert result.result["eligible"] is True
    assert result.result["decision"] == "eligible"
    assert result.result["approval_required"] is True
    assert result.result["policy_references"] == [
        "policy_duplicate_charge_refund_v1",
        "policy_approval_required_v1",
    ]
    assert result.result["recommended_next_action"] == "request_approval"
    assert result.metadata == {"source": "deterministic_policy_engine"}


def test_check_refund_policy_marks_old_refund_request_ineligible(tmp_path):
    connection = reset_connection(tmp_path)

    result = check_refund_policy(connection, "t_002", "o_002")

    assert result.ok is True
    assert result.result["eligible"] is False
    assert result.result["decision"] == "ineligible"
    assert result.result["approval_required"] is False
    assert result.result["policy_references"] == ["policy_refund_window_v1"]
    assert result.result["recommended_next_action"] == "draft_customer_response"


def test_check_refund_policy_marks_bundled_promotion_for_manual_review(tmp_path):
    connection = reset_connection(tmp_path)

    result = check_refund_policy(connection, "t_005", "o_005")

    assert result.ok is True
    assert result.result["eligible"] is False
    assert result.result["decision"] == "manual_review"
    assert result.result["approval_required"] is False
    assert result.result["policy_references"] == ["policy_bundle_partial_refund_v1"]
    assert result.result["recommended_next_action"] == "escalate"


def test_check_refund_policy_returns_missing_information_when_evidence_is_insufficient(tmp_path):
    connection = reset_connection(tmp_path)

    result = check_refund_policy(connection, "t_010", "o_010")

    assert result.ok is True
    assert result.result["eligible"] is False
    assert result.result["decision"] == "missing_information"
    assert result.result["approval_required"] is False
    assert result.result["recommended_next_action"] == "gather_more_evidence"


def test_check_refund_policy_returns_not_found_for_missing_ticket(tmp_path):
    connection = reset_connection(tmp_path)

    result = check_refund_policy(connection, "t_missing", "o_001")

    assert result.ok is False
    assert result.error.type is ErrorType.NOT_FOUND
    assert result.error.details == {"ticket_id": "t_missing"}
    assert result.metadata == {"source": "deterministic_policy_engine"}


def test_check_refund_policy_returns_not_found_for_missing_order(tmp_path):
    connection = reset_connection(tmp_path)

    result = check_refund_policy(connection, "t_003", "o_missing")

    assert result.ok is False
    assert result.error.type is ErrorType.NOT_FOUND
    assert result.error.details == {"order_id": "o_missing"}


def test_check_refund_policy_does_not_mutate_environment(tmp_path):
    connection = reset_connection(tmp_path)
    before_counts = {
        table_name: connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        for table_name in ["audit_log", "idempotency_keys", "ticket_comments", "approvals"]
    }

    check_refund_policy(connection, "t_001", "o_001")
    after_counts = {
        table_name: connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        for table_name in ["audit_log", "idempotency_keys", "ticket_comments", "approvals"]
    }

    assert after_counts == before_counts
