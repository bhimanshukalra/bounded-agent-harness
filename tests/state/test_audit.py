import sqlite3

import pytest

from bounded_agent.config import Settings
from bounded_agent.domain import ApprovalStatus
from bounded_agent.state import (
    connect_database,
    create_approval_request,
    create_ticket_comment,
    get_audit_events,
    get_charges_for_order,
    get_ticket,
    record_mock_refund,
    reset_scenario_environment,
    resolve_approval,
    update_ticket_status,
    write_audit_event,
)

FIXED_TIMESTAMP = "2026-08-25T00:00:00Z"


def reset_connection(tmp_path, scenario_id: str = "support_001") -> sqlite3.Connection:
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    result = reset_scenario_environment(scenario_id, f"{scenario_id}_run", settings)
    return connect_database(result.db_path)


def test_write_audit_event_records_payload(tmp_path):
    connection = reset_connection(tmp_path)

    event = write_audit_event(
        connection,
        audit_id="audit_001",
        timestamp=FIXED_TIMESTAMP,
        run_id="run_001",
        scenario_id="support_001",
        actor="test",
        action="manual_check",
        target_type="ticket",
        target_id="t_001",
        payload={"ok": True},
    )

    audit_events = get_audit_events(connection, "t_001")
    assert event["payload"] == {"ok": True}
    assert audit_events[0]["payload"] == {"ok": True}
    assert audit_events[0]["action"] == "manual_check"


def test_create_ticket_comment_writes_comment_and_audit_event(tmp_path):
    connection = reset_connection(tmp_path)

    comment = create_ticket_comment(
        connection,
        comment_id="comment_001",
        ticket_id="t_001",
        run_id="run_001",
        scenario_id="support_001",
        author="agent",
        body="Verified duplicate charges.",
        created_at=FIXED_TIMESTAMP,
    )

    saved_comment = connection.execute(
        """
        SELECT comment_id, ticket_id, body, visibility
        FROM ticket_comments
        WHERE comment_id = 'comment_001'
        """
    ).fetchone()
    audit_events = get_audit_events(connection, "t_001")

    assert comment["comment_id"] == "comment_001"
    assert dict(saved_comment) == {
        "comment_id": "comment_001",
        "ticket_id": "t_001",
        "body": "Verified duplicate charges.",
        "visibility": "internal",
    }
    assert audit_events[0]["action"] == "create_ticket_comment"
    assert audit_events[0]["payload"] == {"comment_id": "comment_001", "visibility": "internal"}


def test_create_ticket_comment_rolls_back_when_audit_id_conflicts(tmp_path):
    connection = reset_connection(tmp_path)
    write_audit_event(
        connection,
        audit_id="audit_conflict",
        timestamp=FIXED_TIMESTAMP,
        actor="test",
        action="seed_conflict",
        target_type="ticket",
        target_id="t_001",
    )

    with pytest.raises(sqlite3.IntegrityError):
        create_ticket_comment(
            connection,
            comment_id="comment_rollback",
            ticket_id="t_001",
            run_id="run_001",
            scenario_id="support_001",
            author="agent",
            body="This should roll back.",
            created_at=FIXED_TIMESTAMP,
            audit_id="audit_conflict",
        )

    row = connection.execute(
        """
        SELECT comment_id
        FROM ticket_comments
        WHERE comment_id = 'comment_rollback'
        """
    ).fetchone()
    assert row is None


def test_create_approval_request_writes_approval_and_audit_event(tmp_path):
    connection = reset_connection(tmp_path)

    approval = create_approval_request(
        connection,
        approval_id="approval_001",
        run_id="run_001",
        scenario_id="support_001",
        ticket_id="t_001",
        action_type="apply_refund",
        target={"charge_id": "ch_001_b"},
        proposed_arguments={"amount": 49.0, "currency": "USD"},
        evidence_summary=["Two successful duplicate charges found."],
        risk_summary="Refund changes billing state.",
        created_at=FIXED_TIMESTAMP,
    )

    saved_approval = connection.execute(
        """
        SELECT status, decision, target_json
        FROM approvals
        WHERE approval_id = 'approval_001'
        """
    ).fetchone()
    audit_events = get_audit_events(connection, "approval_001")

    assert approval["status"] == "pending"
    assert saved_approval["status"] == "pending"
    assert saved_approval["decision"] is None
    assert "ch_001_b" in saved_approval["target_json"]
    assert audit_events[0]["action"] == "create_approval_request"


def test_resolve_approval_updates_approval_and_writes_audit_event(tmp_path):
    connection = reset_connection(tmp_path)
    create_approval_request(
        connection,
        approval_id="approval_001",
        run_id="run_001",
        scenario_id="support_001",
        ticket_id="t_001",
        action_type="apply_refund",
        target={"charge_id": "ch_001_b"},
        proposed_arguments={"amount": 49.0, "currency": "USD"},
        evidence_summary=["Two successful duplicate charges found."],
        risk_summary="Refund changes billing state.",
        created_at=FIXED_TIMESTAMP,
    )

    result = resolve_approval(
        connection,
        approval_id="approval_001",
        status=ApprovalStatus.APPROVED,
        decision="approved",
        resolved_at="2026-08-25T00:01:00Z",
    )

    saved_approval = connection.execute(
        """
        SELECT status, decision, resolved_at
        FROM approvals
        WHERE approval_id = 'approval_001'
        """
    ).fetchone()
    audit_events = get_audit_events(connection, "approval_001")

    assert result["status"] == "approved"
    assert dict(saved_approval) == {
        "status": "approved",
        "decision": "approved",
        "resolved_at": "2026-08-25T00:01:00Z",
    }
    assert [event["action"] for event in audit_events] == [
        "create_approval_request",
        "resolve_approval",
    ]


def test_resolve_approval_rejects_pending_status(tmp_path):
    connection = reset_connection(tmp_path)

    with pytest.raises(ValueError, match="cannot be pending"):
        resolve_approval(
            connection,
            approval_id="approval_001",
            status=ApprovalStatus.PENDING,
            decision="pending",
        )


def test_update_ticket_status_writes_status_and_audit_event(tmp_path):
    connection = reset_connection(tmp_path)

    result = update_ticket_status(
        connection,
        ticket_id="t_001",
        status="resolved",
        run_id="run_001",
        scenario_id="support_001",
        updated_at=FIXED_TIMESTAMP,
    )

    assert result["status"] == "resolved"
    assert get_ticket(connection, "t_001")["status"] == "resolved"
    assert get_audit_events(connection, "t_001")[0]["action"] == "update_ticket_status"


def test_record_mock_refund_updates_charge_order_and_audit_event(tmp_path):
    connection = reset_connection(tmp_path)

    refund = record_mock_refund(
        connection,
        charge_id="ch_001_b",
        amount=49.0,
        run_id="run_001",
        scenario_id="support_001",
        refunded_at=FIXED_TIMESTAMP,
        idempotency_key="refund:key:001",
    )

    charge = get_charges_for_order(connection, "o_001")[1]
    order = connection.execute(
        """
        SELECT refund_status
        FROM orders
        WHERE order_id = 'o_001'
        """
    ).fetchone()
    audit_events = get_audit_events(connection, "ch_001_b")

    assert refund["status"] == "refunded"
    assert charge["status"] == "refunded"
    assert charge["refunded_amount"] == 49.0
    assert order["refund_status"] == "partial"
    assert audit_events[0]["action"] == "record_mock_refund"
    assert audit_events[0]["idempotency_key"] == "refund:key:001"


def test_record_mock_refund_rejects_over_refund(tmp_path):
    connection = reset_connection(tmp_path)

    with pytest.raises(ValueError, match="exceeds remaining"):
        record_mock_refund(
            connection,
            charge_id="ch_001_b",
            amount=50.0,
            run_id="run_001",
            scenario_id="support_001",
            refunded_at=FIXED_TIMESTAMP,
        )
