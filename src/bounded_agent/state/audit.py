import sqlite3
from datetime import UTC, datetime
from typing import Any

from bounded_agent.domain import ApprovalStatus
from bounded_agent.state.fixtures import json_dump


def current_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_audit_event(
    connection: sqlite3.Connection,
    *,
    audit_id: str,
    timestamp: str,
    actor: str,
    action: str,
    target_type: str,
    target_id: str,
    payload: dict[str, Any] | None = None,
    run_id: str | None = None,
    scenario_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    with connection:
        insert_audit_event(
            connection,
            audit_id=audit_id,
            timestamp=timestamp,
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            payload=payload,
            run_id=run_id,
            scenario_id=scenario_id,
            idempotency_key=idempotency_key,
        )
    return {
        "audit_id": audit_id,
        "timestamp": timestamp,
        "run_id": run_id,
        "scenario_id": scenario_id,
        "actor": actor,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "payload": payload or {},
        "idempotency_key": idempotency_key,
    }


def create_ticket_comment(
    connection: sqlite3.Connection,
    *,
    comment_id: str,
    ticket_id: str,
    run_id: str,
    scenario_id: str | None,
    author: str,
    body: str,
    visibility: str = "internal",
    created_at: str | None = None,
    idempotency_key: str | None = None,
    audit_id: str | None = None,
    actor: str = "environment",
) -> dict[str, Any]:
    timestamp = created_at or current_timestamp()
    audit_event_id = audit_id or f"audit:{comment_id}"
    payload = {"comment_id": comment_id, "visibility": visibility}

    with connection:
        connection.execute(
            """
            INSERT INTO ticket_comments (
                comment_id,
                ticket_id,
                run_id,
                author,
                body,
                visibility,
                created_at,
                idempotency_key
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                comment_id,
                ticket_id,
                run_id,
                author,
                body,
                visibility,
                timestamp,
                idempotency_key,
            ),
        )
        insert_audit_event(
            connection,
            audit_id=audit_event_id,
            timestamp=timestamp,
            run_id=run_id,
            scenario_id=scenario_id,
            actor=actor,
            action="create_ticket_comment",
            target_type="ticket",
            target_id=ticket_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )

    return {
        "comment_id": comment_id,
        "ticket_id": ticket_id,
        "run_id": run_id,
        "author": author,
        "body": body,
        "visibility": visibility,
        "created_at": timestamp,
        "idempotency_key": idempotency_key,
    }


def create_approval_request(
    connection: sqlite3.Connection,
    *,
    approval_id: str,
    run_id: str,
    scenario_id: str | None,
    ticket_id: str,
    action_type: str,
    target: dict[str, Any],
    proposed_arguments: dict[str, Any],
    evidence_summary: list[str],
    risk_summary: str,
    created_at: str | None = None,
    audit_id: str | None = None,
    actor: str = "environment",
) -> dict[str, Any]:
    timestamp = created_at or current_timestamp()
    audit_event_id = audit_id or f"audit:{approval_id}:created"

    with connection:
        connection.execute(
            """
            INSERT INTO approvals (
                approval_id,
                run_id,
                scenario_id,
                ticket_id,
                action_type,
                target_json,
                proposed_arguments_json,
                evidence_summary_json,
                risk_summary,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id,
                run_id,
                scenario_id,
                ticket_id,
                action_type,
                json_dump(target),
                json_dump(proposed_arguments),
                json_dump(evidence_summary),
                risk_summary,
                ApprovalStatus.PENDING,
                timestamp,
            ),
        )
        insert_audit_event(
            connection,
            audit_id=audit_event_id,
            timestamp=timestamp,
            run_id=run_id,
            scenario_id=scenario_id,
            actor=actor,
            action="create_approval_request",
            target_type="approval",
            target_id=approval_id,
            payload={"ticket_id": ticket_id, "action_type": action_type, "target": target},
        )

    return {
        "approval_id": approval_id,
        "run_id": run_id,
        "scenario_id": scenario_id,
        "ticket_id": ticket_id,
        "action_type": action_type,
        "target": target,
        "proposed_arguments": proposed_arguments,
        "evidence_summary": evidence_summary,
        "risk_summary": risk_summary,
        "status": ApprovalStatus.PENDING.value,
        "decision": None,
        "created_at": timestamp,
        "resolved_at": None,
    }


def resolve_approval(
    connection: sqlite3.Connection,
    *,
    approval_id: str,
    status: ApprovalStatus,
    decision: str,
    resolved_at: str | None = None,
    audit_id: str | None = None,
    actor: str = "environment",
) -> dict[str, Any]:
    if status is ApprovalStatus.PENDING:
        raise ValueError("resolved approval status cannot be pending")

    timestamp = resolved_at or current_timestamp()
    approval = connection.execute(
        """
        SELECT run_id, scenario_id
        FROM approvals
        WHERE approval_id = ?
        """,
        (approval_id,),
    ).fetchone()
    if approval is None:
        raise ValueError(f"approval does not exist: {approval_id}")

    with connection:
        connection.execute(
            """
            UPDATE approvals
            SET status = ?, decision = ?, resolved_at = ?
            WHERE approval_id = ?
            """,
            (status, decision, timestamp, approval_id),
        )
        insert_audit_event(
            connection,
            audit_id=audit_id or f"audit:{approval_id}:resolved",
            timestamp=timestamp,
            run_id=approval["run_id"],
            scenario_id=approval["scenario_id"],
            actor=actor,
            action="resolve_approval",
            target_type="approval",
            target_id=approval_id,
            payload={"status": status.value, "decision": decision},
        )

    return {
        "approval_id": approval_id,
        "status": status.value,
        "decision": decision,
        "resolved_at": timestamp,
    }


def update_ticket_status(
    connection: sqlite3.Connection,
    *,
    ticket_id: str,
    status: str,
    run_id: str,
    scenario_id: str | None,
    updated_at: str | None = None,
    audit_id: str | None = None,
    actor: str = "environment",
) -> dict[str, Any]:
    timestamp = updated_at or current_timestamp()

    with connection:
        cursor = connection.execute(
            """
            UPDATE tickets
            SET status = ?
            WHERE ticket_id = ?
            """,
            (status, ticket_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"ticket does not exist: {ticket_id}")
        insert_audit_event(
            connection,
            audit_id=audit_id or f"audit:{ticket_id}:status:{status}",
            timestamp=timestamp,
            run_id=run_id,
            scenario_id=scenario_id,
            actor=actor,
            action="update_ticket_status",
            target_type="ticket",
            target_id=ticket_id,
            payload={"status": status},
        )

    return {"ticket_id": ticket_id, "status": status, "updated_at": timestamp}


def record_mock_refund(
    connection: sqlite3.Connection,
    *,
    charge_id: str,
    amount: float,
    run_id: str,
    scenario_id: str | None,
    refunded_at: str | None = None,
    idempotency_key: str | None = None,
    audit_id: str | None = None,
    actor: str = "environment",
) -> dict[str, Any]:
    if amount <= 0:
        raise ValueError("refund amount must be positive")

    timestamp = refunded_at or current_timestamp()
    charge = connection.execute(
        """
        SELECT charge_id, order_id, amount, currency, refunded_amount
        FROM charges
        WHERE charge_id = ?
        """,
        (charge_id,),
    ).fetchone()
    if charge is None:
        raise ValueError(f"charge does not exist: {charge_id}")

    new_refunded_amount = charge["refunded_amount"] + amount
    if new_refunded_amount > charge["amount"]:
        raise ValueError("refund amount exceeds remaining charge amount")

    charge_status = "refunded" if new_refunded_amount == charge["amount"] else "partially_refunded"

    with connection:
        connection.execute(
            """
            UPDATE charges
            SET status = ?, refunded_amount = ?
            WHERE charge_id = ?
            """,
            (charge_status, new_refunded_amount, charge_id),
        )
        connection.execute(
            """
            UPDATE orders
            SET refund_status = 'partial'
            WHERE order_id = ?
            """,
            (charge["order_id"],),
        )
        insert_audit_event(
            connection,
            audit_id=audit_id or f"audit:{charge_id}:refund",
            timestamp=timestamp,
            run_id=run_id,
            scenario_id=scenario_id,
            actor=actor,
            action="record_mock_refund",
            target_type="charge",
            target_id=charge_id,
            payload={
                "amount": amount,
                "currency": charge["currency"],
                "order_id": charge["order_id"],
                "refunded_amount": new_refunded_amount,
            },
            idempotency_key=idempotency_key,
        )

    return {
        "charge_id": charge_id,
        "order_id": charge["order_id"],
        "amount": amount,
        "currency": charge["currency"],
        "refunded_amount": new_refunded_amount,
        "status": charge_status,
        "refunded_at": timestamp,
        "idempotency_key": idempotency_key,
    }


def insert_audit_event(
    connection: sqlite3.Connection,
    *,
    audit_id: str,
    timestamp: str,
    actor: str,
    action: str,
    target_type: str,
    target_id: str,
    payload: dict[str, Any] | None = None,
    run_id: str | None = None,
    scenario_id: str | None = None,
    idempotency_key: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO audit_log (
            audit_id,
            timestamp,
            run_id,
            scenario_id,
            actor,
            action,
            target_type,
            target_id,
            payload_json,
            idempotency_key
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            audit_id,
            timestamp,
            run_id,
            scenario_id,
            actor,
            action,
            target_type,
            target_id,
            json_dump(payload or {}),
            idempotency_key,
        ),
    )
