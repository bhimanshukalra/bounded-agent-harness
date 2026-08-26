import sqlite3

from bounded_agent.config import Settings
from bounded_agent.domain import ApprovalStatus, ErrorType
from bounded_agent.state import (
    connect_database,
    create_approval_request,
    get_idempotency_record,
    reset_scenario_environment,
    resolve_approval,
)
from bounded_agent.tools import ToolCall, ToolExecutionContext, build_default_registry


def reset_connection(tmp_path, scenario_id: str = "support_001") -> sqlite3.Connection:
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


def approve_status_update(connection: sqlite3.Connection) -> None:
    create_approval_request(
        connection,
        approval_id="approval_status_001",
        run_id="run_001",
        scenario_id="support_001",
        ticket_id="t_001",
        action_type="update_ticket_status",
        target={"ticket_id": "t_001"},
        proposed_arguments={"status": "resolved"},
        evidence_summary=["Approved ticket status update."],
        risk_summary="Closing ticket changes support state.",
    )
    resolve_approval(
        connection,
        approval_id="approval_status_001",
        status=ApprovalStatus.APPROVED,
        decision="approved",
    )


def test_request_approval_requires_idempotency_key(tmp_path):
    connection = reset_connection(tmp_path)

    result = execute(
        connection,
        "request_approval",
        {
            "ticket_id": "t_001",
            "action_type": "apply_refund",
            "target": {"charge_id": "ch_001_b", "order_id": "o_001"},
            "proposed_arguments": {"amount": 49.0, "currency": "USD", "reason": "duplicate_charge"},
            "evidence_summary": ["Duplicate charge evidence."],
            "risk_summary": "Refund changes billing state.",
        },
    )

    assert result.ok is False
    assert result.error.type is ErrorType.VALIDATION_ERROR
    assert result.error.details == {"tool_name": "request_approval"}


def test_request_approval_replays_matching_retry(tmp_path):
    connection = reset_connection(tmp_path)
    arguments = {
        "ticket_id": "t_001",
        "action_type": "apply_refund",
        "target": {"charge_id": "ch_001_b", "order_id": "o_001"},
        "proposed_arguments": {"amount": 49.0, "currency": "USD", "reason": "duplicate_charge"},
        "evidence_summary": ["Duplicate charge evidence."],
        "risk_summary": "Refund changes billing state.",
    }

    first = execute(
        connection,
        "request_approval",
        arguments,
        idempotency_key="approval:key:001",
    )
    second = execute(
        connection,
        "request_approval",
        arguments,
        idempotency_key="approval:key:001",
    )

    assert first.ok is True
    assert second.ok is True
    assert second.result == first.result
    assert second.metadata == {"source": "idempotency_replay"}
    assert count_rows(connection, "approvals") == 1
    assert count_rows(connection, "idempotency_keys") == 1


def test_request_approval_conflicts_when_retry_arguments_change(tmp_path):
    connection = reset_connection(tmp_path)
    execute(
        connection,
        "request_approval",
        {
            "ticket_id": "t_001",
            "action_type": "apply_refund",
            "target": {"charge_id": "ch_001_b", "order_id": "o_001"},
            "proposed_arguments": {"amount": 49.0, "currency": "USD", "reason": "duplicate_charge"},
            "evidence_summary": ["Duplicate charge evidence."],
            "risk_summary": "Refund changes billing state.",
        },
        idempotency_key="approval:key:001",
    )

    conflict = execute(
        connection,
        "request_approval",
        {
            "ticket_id": "t_001",
            "action_type": "apply_refund",
            "target": {"charge_id": "ch_001_b", "order_id": "o_001"},
            "proposed_arguments": {"amount": 25.0, "currency": "USD", "reason": "duplicate_charge"},
            "evidence_summary": ["Duplicate charge evidence."],
            "risk_summary": "Refund changes billing state.",
        },
        idempotency_key="approval:key:001",
    )

    assert conflict.ok is False
    assert conflict.error.type is ErrorType.CONFLICT
    assert conflict.error.details["idempotency_key"] == "approval:key:001"
    assert count_rows(connection, "approvals") == 1


def test_apply_refund_replays_matching_retry_without_duplicate_refund(tmp_path):
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
        approval_id="support_009:approval:refund",
        idempotency_key="refund:key:009",
    )
    second = execute(
        connection,
        "apply_refund",
        arguments,
        run_id="support_009_run",
        approval_id="support_009:approval:refund",
        idempotency_key="refund:key:009",
    )
    charge = connection.execute(
        "SELECT refunded_amount FROM charges WHERE charge_id = 'ch_009_b'"
    ).fetchone()

    assert first.ok is True
    assert second.ok is True
    assert second.result == first.result
    assert second.metadata == {"source": "idempotency_replay"}
    assert charge["refunded_amount"] == 49.0
    assert count_rows(connection, "idempotency_keys") == 1


def test_apply_refund_conflicts_when_retry_arguments_change(tmp_path):
    connection = reset_connection(tmp_path, "support_009")
    execute(
        connection,
        "apply_refund",
        {
            "charge_id": "ch_009_b",
            "amount": 49.0,
            "currency": "USD",
            "reason": "duplicate_charge",
        },
        run_id="support_009_run",
        approval_id="support_009:approval:refund",
        idempotency_key="refund:key:009",
    )

    conflict = execute(
        connection,
        "apply_refund",
        {
            "charge_id": "ch_009_b",
            "amount": 25.0,
            "currency": "USD",
            "reason": "duplicate_charge",
        },
        run_id="support_009_run",
        approval_id="support_009:approval:refund",
        idempotency_key="refund:key:009",
    )

    assert conflict.ok is False
    assert conflict.error.type is ErrorType.CONFLICT
    assert count_rows(connection, "idempotency_keys") == 1


def test_update_ticket_status_requires_idempotency_key(tmp_path):
    connection = reset_connection(tmp_path)
    approve_status_update(connection)

    result = execute(
        connection,
        "update_ticket_status",
        {"ticket_id": "t_001", "status": "resolved"},
        scenario_id="support_001",
        approval_id="approval_status_001",
    )

    assert result.ok is False
    assert result.error.type is ErrorType.VALIDATION_ERROR
    assert result.error.details == {"tool_name": "update_ticket_status"}


def test_update_ticket_status_replays_matching_retry(tmp_path):
    connection = reset_connection(tmp_path)
    approve_status_update(connection)
    arguments = {"ticket_id": "t_001", "status": "resolved"}

    first = execute(
        connection,
        "update_ticket_status",
        arguments,
        scenario_id="support_001",
        approval_id="approval_status_001",
        idempotency_key="status:key:001",
    )
    second = execute(
        connection,
        "update_ticket_status",
        arguments,
        scenario_id="support_001",
        approval_id="approval_status_001",
        idempotency_key="status:key:001",
    )

    assert first.ok is True
    assert second.ok is True
    assert second.result == first.result
    assert second.metadata == {"source": "idempotency_replay"}
    assert get_idempotency_record(connection, "status:key:001")["result"] == first.result
