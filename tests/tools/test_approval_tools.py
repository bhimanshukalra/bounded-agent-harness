import sqlite3

from bounded_agent.config import Settings
from bounded_agent.domain import ApprovalStatus, ErrorType
from bounded_agent.state import (
    connect_database,
    create_approval_request,
    get_audit_events,
    get_charges_for_order,
    get_ticket,
    reset_scenario_environment,
    resolve_approval,
)
from bounded_agent.tools import ToolCall, ToolExecutionContext, build_default_registry


def reset_connection(tmp_path, scenario_id: str = "support_001") -> sqlite3.Connection:
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    result = reset_scenario_environment(scenario_id, f"{scenario_id}_run", settings)
    return connect_database(result.db_path)


def execute_tool(connection: sqlite3.Connection, tool_name: str, arguments: dict, **context_kwargs):
    registry = build_default_registry()
    context = ToolExecutionContext(
        run_id=context_kwargs.pop("run_id", "run_001"),
        connection=connection,
        **context_kwargs,
    )
    return registry.execute(ToolCall(tool_name=tool_name, arguments=arguments), context)


def test_request_approval_creates_pending_approval_and_audit_event(tmp_path):
    connection = reset_connection(tmp_path)

    result = execute_tool(
        connection,
        "request_approval",
        {
            "ticket_id": "t_001",
            "action_type": "apply_refund",
            "target": {"charge_id": "ch_001_b", "order_id": "o_001"},
            "proposed_arguments": {
                "amount": 49.0,
                "currency": "USD",
                "reason": "duplicate_charge",
            },
            "evidence_summary": ["Two successful charges with same amount and currency."],
            "risk_summary": "Refund changes mock billing state.",
        },
        scenario_id="support_001",
        actor="agent",
        idempotency_key="approval:key:001",
    )
    approval = connection.execute("SELECT approval_id, status FROM approvals").fetchone()
    audit_events = get_audit_events(connection, approval["approval_id"])

    assert result.ok is True
    assert result.result == {
        "approval_id": approval["approval_id"],
        "status": "pending",
        "ticket_id": "t_001",
        "action_type": "apply_refund",
    }
    assert approval["status"] == "pending"
    assert audit_events[0]["action"] == "create_approval_request"


def test_apply_refund_rejects_missing_approval_id(tmp_path):
    connection = reset_connection(tmp_path)

    result = execute_tool(
        connection,
        "apply_refund",
        {
            "charge_id": "ch_001_b",
            "amount": 49.0,
            "currency": "USD",
            "reason": "duplicate_charge",
        },
        idempotency_key="refund:key:001",
    )

    assert result.ok is False
    assert result.error.type is ErrorType.PERMISSION_DENIED
    assert result.error.details == {"action_type": "apply_refund"}


def test_apply_refund_rejects_denied_approval_fixture(tmp_path):
    connection = reset_connection(tmp_path, "support_007")

    result = execute_tool(
        connection,
        "apply_refund",
        {
            "charge_id": "ch_007_b",
            "amount": 49.0,
            "currency": "USD",
            "reason": "duplicate_charge",
        },
        run_id="support_007_run",
        scenario_id="support_007",
        approval_id="support_007:approval:refund",
        idempotency_key="refund:key:007",
    )

    assert result.ok is False
    assert result.error.type is ErrorType.PERMISSION_DENIED
    assert result.error.details == {
        "approval_id": "support_007:approval:refund",
        "status": "denied",
    }


def test_apply_refund_executes_with_approved_fixture_and_writes_audit(tmp_path):
    connection = reset_connection(tmp_path, "support_009")

    result = execute_tool(
        connection,
        "apply_refund",
        {
            "charge_id": "ch_009_b",
            "amount": 49.0,
            "currency": "USD",
            "reason": "duplicate_charge",
        },
        run_id="support_009_run",
        scenario_id="support_009",
        actor="agent",
        approval_id="support_009:approval:refund",
        idempotency_key="refund:key:009",
    )
    charge = get_charges_for_order(connection, "o_009")[1]
    audit_events = get_audit_events(connection, "ch_009_b")

    assert result.ok is True
    assert result.result == {
        "charge_id": "ch_009_b",
        "order_id": "o_009",
        "amount": 49.0,
        "currency": "USD",
        "status": "refunded",
        "idempotency_key": "refund:key:009",
    }
    assert charge["status"] == "refunded"
    assert charge["refunded_amount"] == 49.0
    assert audit_events[0]["action"] == "record_mock_refund"
    assert audit_events[0]["idempotency_key"] == "refund:key:009"


def test_apply_refund_rejects_approval_target_mismatch(tmp_path):
    connection = reset_connection(tmp_path, "support_009")

    result = execute_tool(
        connection,
        "apply_refund",
        {
            "charge_id": "ch_009_a",
            "amount": 49.0,
            "currency": "USD",
            "reason": "duplicate_charge",
        },
        run_id="support_009_run",
        scenario_id="support_009",
        approval_id="support_009:approval:refund",
        idempotency_key="refund:key:009",
    )

    assert result.ok is False
    assert result.error.type is ErrorType.PERMISSION_DENIED
    assert result.error.details["approval_id"] == "support_009:approval:refund"


def test_update_ticket_status_executes_with_matching_approved_action(tmp_path):
    connection = reset_connection(tmp_path)
    create_approval_request(
        connection,
        approval_id="approval_status_001",
        run_id="run_001",
        scenario_id="support_001",
        ticket_id="t_001",
        action_type="update_ticket_status",
        target={"ticket_id": "t_001"},
        proposed_arguments={"status": "resolved"},
        evidence_summary=["Refund approval flow is complete."],
        risk_summary="Closing ticket changes support state.",
    )
    resolve_approval(
        connection,
        approval_id="approval_status_001",
        status=ApprovalStatus.APPROVED,
        decision="approved",
    )

    result = execute_tool(
        connection,
        "update_ticket_status",
        {"ticket_id": "t_001", "status": "resolved"},
        scenario_id="support_001",
        approval_id="approval_status_001",
        idempotency_key="status:key:001",
    )

    assert result.ok is True
    assert result.result["ticket_id"] == "t_001"
    assert result.result["status"] == "resolved"
    assert get_ticket(connection, "t_001")["status"] == "resolved"
    assert get_audit_events(connection, "t_001")[-1]["action"] == "update_ticket_status"


def test_update_ticket_status_rejects_pending_approval(tmp_path):
    connection = reset_connection(tmp_path)
    create_approval_request(
        connection,
        approval_id="approval_status_001",
        run_id="run_001",
        scenario_id="support_001",
        ticket_id="t_001",
        action_type="update_ticket_status",
        target={"ticket_id": "t_001"},
        proposed_arguments={"status": "resolved"},
        evidence_summary=["Refund approval flow is complete."],
        risk_summary="Closing ticket changes support state.",
    )

    result = execute_tool(
        connection,
        "update_ticket_status",
        {"ticket_id": "t_001", "status": "resolved"},
        scenario_id="support_001",
        approval_id="approval_status_001",
        idempotency_key="status:key:001",
    )

    assert result.ok is False
    assert result.error.type is ErrorType.PERMISSION_DENIED
    assert result.error.details == {"approval_id": "approval_status_001", "status": "pending"}
