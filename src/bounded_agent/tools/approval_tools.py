import hashlib
import json
import sqlite3
from typing import Any

from bounded_agent.domain import ApprovalStatus, ErrorType
from bounded_agent.state import (
    consume_injected_failure,
    create_approval_request,
    get_idempotency_record,
    get_ticket,
    hash_arguments,
    next_matching_failure,
    record_mock_refund,
    record_or_replay_idempotency,
)
from bounded_agent.state import (
    update_ticket_status as update_ticket_status_record,
)
from bounded_agent.tools.execution import (
    ToolExecutionContext,
    error_result,
    success_result,
    tool_connection,
)
from bounded_agent.tools.failure_handling import injected_failure_result
from bounded_agent.tools.models import ToolResult
from bounded_agent.tools.schemas import (
    ApplyRefundInput,
    RequestApprovalInput,
    StrictToolSchema,
    UpdateTicketStatusInput,
)


def request_approval(context: ToolExecutionContext, tool_input: StrictToolSchema) -> ToolResult:
    typed_input = expect_input(tool_input, RequestApprovalInput)
    if context.idempotency_key is None:
        return missing_idempotency_key_result("request_approval")

    arguments = typed_input.model_dump()
    with tool_connection(context) as connection:
        ticket = get_ticket(connection, typed_input.ticket_id)
        if ticket is None:
            return not_found_result("Ticket was not found.", "ticket_id", typed_input.ticket_id)
        replay_or_conflict = get_replay_or_conflict(connection, context, arguments)
        if replay_or_conflict is not None:
            return replay_or_conflict

        approval_id = stable_id(
            "approval",
            context.idempotency_key,
        )
        approval = create_approval_request(
            connection,
            approval_id=approval_id,
            run_id=context.run_id,
            scenario_id=context.scenario_id,
            ticket_id=typed_input.ticket_id,
            action_type=typed_input.action_type,
            target=typed_input.target,
            proposed_arguments=typed_input.proposed_arguments,
            evidence_summary=typed_input.evidence_summary,
            risk_summary=typed_input.risk_summary,
            actor=context.actor,
        )
        result = {
            "approval_id": approval["approval_id"],
            "status": approval["status"],
            "ticket_id": approval["ticket_id"],
            "action_type": approval["action_type"],
        }
        record_or_replay_idempotency(
            connection,
            idempotency_key=context.idempotency_key,
            run_id=context.run_id,
            tool_name="request_approval",
            target_type="ticket",
            target_id=typed_input.ticket_id,
            arguments=arguments,
            result=result,
        )

    return success_result(result, metadata={"source": "mock_support_environment"})


def apply_refund(context: ToolExecutionContext, tool_input: StrictToolSchema) -> ToolResult:
    typed_input = expect_input(tool_input, ApplyRefundInput)
    if context.idempotency_key is None:
        return missing_idempotency_key_result("apply_refund")
    if context.approval_id is None:
        return error_result(
            ErrorType.PERMISSION_DENIED,
            "Approval-required tool needs a durable approval_id.",
            details={"action_type": "apply_refund"},
        )

    arguments = typed_input.model_dump()
    with tool_connection(context) as connection:
        replay_or_conflict = get_replay_or_conflict(connection, context, arguments)
        if replay_or_conflict is not None:
            return replay_or_conflict

        charge = get_charge(connection, typed_input.charge_id)
        if charge is None:
            return not_found_result("Charge was not found.", "charge_id", typed_input.charge_id)
        if charge["currency"] != typed_input.currency:
            return error_result(
                ErrorType.VALIDATION_ERROR,
                "Refund currency does not match charge currency.",
                details={"charge_id": typed_input.charge_id, "charge_currency": charge["currency"]},
            )

        approval_result = require_approved_action(
            connection,
            context,
            action_type="apply_refund",
            target={"charge_id": typed_input.charge_id, "order_id": charge["order_id"]},
            arguments={
                "amount": typed_input.amount,
                "currency": typed_input.currency,
                "reason": typed_input.reason,
            },
        )
        if isinstance(approval_result, ToolResult):
            return approval_result

        pre_side_effect_failure = consume_pre_side_effect_failure(
            connection,
            context,
            "apply_refund",
            {"charge_id": typed_input.charge_id},
        )
        if pre_side_effect_failure is not None:
            return pre_side_effect_failure

        try:
            refund = record_mock_refund(
                connection,
                charge_id=typed_input.charge_id,
                amount=typed_input.amount,
                run_id=context.run_id,
                scenario_id=context.scenario_id,
                idempotency_key=context.idempotency_key,
                actor=context.actor,
            )
        except ValueError as exc:
            if "does not exist" in str(exc):
                return not_found_result("Charge was not found.", "charge_id", typed_input.charge_id)
            return error_result(ErrorType.VALIDATION_ERROR, str(exc))
        result = {
            "charge_id": refund["charge_id"],
            "order_id": refund["order_id"],
            "amount": refund["amount"],
            "currency": refund["currency"],
            "status": refund["status"],
            "idempotency_key": context.idempotency_key,
        }
        record_or_replay_idempotency(
            connection,
            idempotency_key=context.idempotency_key,
            run_id=context.run_id,
            tool_name="apply_refund",
            target_type="charge",
            target_id=typed_input.charge_id,
            arguments=arguments,
            result=result,
        )
        post_side_effect_failure = consume_post_side_effect_failure(
            connection,
            context,
            "apply_refund",
            {"charge_id": typed_input.charge_id},
        )
        if post_side_effect_failure is not None:
            return post_side_effect_failure

    return success_result(result, metadata={"source": "mock_support_environment"})


def update_ticket_status(context: ToolExecutionContext, tool_input: StrictToolSchema) -> ToolResult:
    typed_input = expect_input(tool_input, UpdateTicketStatusInput)
    if context.idempotency_key is None:
        return missing_idempotency_key_result("update_ticket_status")
    if context.approval_id is None:
        return error_result(
            ErrorType.PERMISSION_DENIED,
            "Approval-required tool needs a durable approval_id.",
            details={"action_type": "update_ticket_status"},
        )

    arguments = typed_input.model_dump()
    with tool_connection(context) as connection:
        replay_or_conflict = get_replay_or_conflict(connection, context, arguments)
        if replay_or_conflict is not None:
            return replay_or_conflict

        approval_result = require_approved_action(
            connection,
            context,
            action_type="update_ticket_status",
            target={"ticket_id": typed_input.ticket_id},
            arguments={"status": typed_input.status},
        )
        if isinstance(approval_result, ToolResult):
            return approval_result

        try:
            updated = update_ticket_status_record(
                connection,
                ticket_id=typed_input.ticket_id,
                status=typed_input.status,
                run_id=context.run_id,
                scenario_id=context.scenario_id,
                actor=context.actor,
            )
        except ValueError:
            return not_found_result("Ticket was not found.", "ticket_id", typed_input.ticket_id)
        result = {
            "ticket_id": updated["ticket_id"],
            "status": updated["status"],
            "updated_at": updated["updated_at"],
        }
        record_or_replay_idempotency(
            connection,
            idempotency_key=context.idempotency_key,
            run_id=context.run_id,
            tool_name="update_ticket_status",
            target_type="ticket",
            target_id=typed_input.ticket_id,
            arguments=arguments,
            result=result,
        )

    return success_result(result, metadata={"source": "mock_support_environment"})


def get_replay_or_conflict(
    connection: sqlite3.Connection,
    context: ToolExecutionContext,
    arguments: dict[str, Any],
) -> ToolResult | None:
    if context.idempotency_key is None:
        return None

    existing_record = get_idempotency_record(connection, context.idempotency_key)
    if existing_record is None:
        return None
    if existing_record["argument_hash"] == hash_arguments(arguments):
        return success_result(
            existing_record["result"],
            metadata={"source": "idempotency_replay"},
        )
    return error_result(
        ErrorType.CONFLICT,
        "Idempotency key was reused with different arguments.",
        details={
            "idempotency_key": context.idempotency_key,
            "original_argument_hash": existing_record["argument_hash"],
            "new_argument_hash": hash_arguments(arguments),
        },
    )


def consume_pre_side_effect_failure(
    connection: sqlite3.Connection,
    context: ToolExecutionContext,
    tool_name: str,
    target: dict[str, Any],
) -> ToolResult | None:
    if context.scenario_id is None:
        return None

    failure = next_matching_failure(
        connection,
        scenario_id=context.scenario_id,
        tool_name=tool_name,
        target=target,
    )
    if failure is None or failure["failure_type"] == "transient_error_after_side_effect":
        return None

    consumed_failure = consume_injected_failure(
        connection,
        scenario_id=context.scenario_id,
        tool_name=tool_name,
        target=target,
    )
    if consumed_failure is None:
        return None
    return injected_failure_result(consumed_failure)


def consume_post_side_effect_failure(
    connection: sqlite3.Connection,
    context: ToolExecutionContext,
    tool_name: str,
    target: dict[str, Any],
) -> ToolResult | None:
    if context.scenario_id is None:
        return None

    failure = next_matching_failure(
        connection,
        scenario_id=context.scenario_id,
        tool_name=tool_name,
        target=target,
    )
    if failure is None or failure["failure_type"] != "transient_error_after_side_effect":
        return None

    consumed_failure = consume_injected_failure(
        connection,
        scenario_id=context.scenario_id,
        tool_name=tool_name,
        target=target,
    )
    if consumed_failure is None:
        return None
    return injected_failure_result(consumed_failure)


def require_approved_action(
    connection: sqlite3.Connection,
    context: ToolExecutionContext,
    *,
    action_type: str,
    target: dict[str, Any],
    arguments: dict[str, Any],
) -> dict[str, Any] | ToolResult:
    if context.approval_id is None:
        return error_result(
            ErrorType.PERMISSION_DENIED,
            "Approval-required tool needs a durable approval_id.",
            details={"action_type": action_type},
        )

    approval = get_approval(connection, context.approval_id)
    if approval is None:
        return error_result(
            ErrorType.PERMISSION_DENIED,
            "Approval was not found.",
            details={"approval_id": context.approval_id},
        )
    if approval["status"] != ApprovalStatus.APPROVED.value:
        return error_result(
            ErrorType.PERMISSION_DENIED,
            "Approval is not approved.",
            details={"approval_id": context.approval_id, "status": approval["status"]},
        )
    if approval["action_type"] != action_type:
        return error_result(
            ErrorType.PERMISSION_DENIED,
            "Approval action does not match requested tool.",
            details={"approval_id": context.approval_id, "approved_action": approval["action_type"]},
        )
    if not expected_items_match(approval["target"], target):
        return error_result(
            ErrorType.PERMISSION_DENIED,
            "Approval target does not match requested arguments.",
            details={"approval_id": context.approval_id, "approved_target": approval["target"]},
        )
    if not expected_items_match(approval["proposed_arguments"], arguments):
        return error_result(
            ErrorType.PERMISSION_DENIED,
            "Approval arguments do not match requested arguments.",
            details={
                "approval_id": context.approval_id,
                "approved_arguments": approval["proposed_arguments"],
            },
        )
    return approval


def get_charge(connection: sqlite3.Connection, charge_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT charge_id, order_id, amount, currency, status, refunded_amount
        FROM charges
        WHERE charge_id = ?
        """,
        (charge_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def get_approval(connection: sqlite3.Connection, approval_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT *
        FROM approvals
        WHERE approval_id = ?
        """,
        (approval_id,),
    ).fetchone()
    if row is None:
        return None

    approval = dict(row)
    approval["target"] = json.loads(approval.pop("target_json"))
    approval["proposed_arguments"] = json.loads(approval.pop("proposed_arguments_json"))
    approval["evidence_summary"] = json.loads(approval.pop("evidence_summary_json"))
    return approval


def expected_items_match(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def not_found_result(message: str, field_name: str, field_value: str) -> ToolResult:
    return error_result(
        ErrorType.NOT_FOUND,
        message,
        details={field_name: field_value},
        metadata={"source": "mock_support_environment"},
    )


def missing_idempotency_key_result(tool_name: str) -> ToolResult:
    return error_result(
        ErrorType.VALIDATION_ERROR,
        "Mutating tool requires an idempotency key.",
        details={"tool_name": tool_name},
    )


def expect_input[SchemaT: StrictToolSchema](
    tool_input: StrictToolSchema,
    schema_type: type[SchemaT],
) -> SchemaT:
    if not isinstance(tool_input, schema_type):
        raise TypeError(f"expected {schema_type.__name__}, got {type(tool_input).__name__}")
    return tool_input
