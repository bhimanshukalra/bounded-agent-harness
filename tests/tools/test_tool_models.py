import pytest
from pydantic import ValidationError

from bounded_agent.domain import ErrorType, PermissionLevel
from bounded_agent.tools import Observation, ToolCall, ToolError, ToolResult, ToolSpec


def test_tool_spec_accepts_read_only_tool():
    spec = ToolSpec(
        name="fetch_ticket",
        description="Fetch scoped ticket details.",
        input_schema="FetchTicketInput",
        output_schema="FetchTicketOutput",
        permission_level="read_only",
        mutates_state=False,
        approval_required=False,
        idempotency_required=False,
        error_types=["not_found", "validation_error", "timeout"],
    )

    assert spec.permission_level is PermissionLevel.READ_ONLY
    assert spec.error_types == [
        ErrorType.NOT_FOUND,
        ErrorType.VALIDATION_ERROR,
        ErrorType.TIMEOUT,
    ]


def test_tool_spec_rejects_approval_required_permission_without_approval_flag():
    with pytest.raises(ValidationError, match="approval_required=true"):
        ToolSpec(
            name="apply_refund",
            description="Apply approved refund.",
            input_schema="ApplyRefundInput",
            output_schema="ApplyRefundOutput",
            permission_level="approval_required",
            mutates_state=True,
            approval_required=False,
            idempotency_required=True,
            idempotency_key_rule="ticket:approval:charge",
            error_types=["permission_denied"],
        )


def test_tool_spec_rejects_mutating_tool_without_idempotency_rule():
    with pytest.raises(ValidationError, match="idempotency_key_rule"):
        ToolSpec(
            name="add_ticket_comment",
            description="Add internal note.",
            input_schema="AddTicketCommentInput",
            output_schema="AddTicketCommentOutput",
            permission_level="low_risk_write",
            mutates_state=True,
            approval_required=False,
            idempotency_required=True,
            error_types=["validation_error"],
        )


def test_tool_spec_rejects_forbidden_tool_registration():
    with pytest.raises(ValidationError, match="forbidden tools"):
        ToolSpec(
            name="run_shell",
            description="Forbidden shell access.",
            input_schema="RunShellInput",
            output_schema="RunShellOutput",
            permission_level="forbidden",
            mutates_state=False,
            approval_required=False,
            idempotency_required=False,
            error_types=["policy_violation"],
        )


def test_tool_call_holds_arguments_and_execution_context():
    call = ToolCall(
        tool_name="apply_refund",
        arguments={"charge_id": "ch_001", "amount": 49.0},
        run_id="run_001",
        approval_id="appr_001",
        idempotency_key="support_001:appr_001:refund:ch_001",
    )

    assert call.arguments["charge_id"] == "ch_001"


def test_tool_result_success_requires_result_and_no_error():
    result = ToolResult(
        ok=True,
        result={"ticket_id": "t_001"},
        metadata={"source": "mock_support_backend"},
    )

    assert result.error is None


def test_tool_result_rejects_success_with_error():
    with pytest.raises(ValidationError, match="successful tool results cannot include error"):
        ToolResult(
            ok=True,
            result={"ticket_id": "t_001"},
            error=ToolError(type="timeout", message="Timed out", retryable=True),
        )


def test_tool_result_failure_requires_error_and_no_result():
    result = ToolResult(
        ok=False,
        error={
            "type": "not_found",
            "message": "Ticket was not found.",
            "retryable": False,
        },
    )

    assert result.error is not None
    assert result.error.type is ErrorType.NOT_FOUND


def test_tool_result_rejects_failure_with_result():
    with pytest.raises(ValidationError, match="failed tool results cannot include result"):
        ToolResult(
            ok=False,
            result={"ticket_id": "t_001"},
            error={
                "type": "not_found",
                "message": "Ticket was not found.",
                "retryable": False,
            },
        )


def test_tool_error_rejects_unknown_error_type():
    with pytest.raises(ValidationError, match="type"):
        ToolError(type="network_bad", message="Unknown error type.")


def test_observation_wraps_tool_result_with_summary():
    observation = Observation(
        tool_name="fetch_ticket",
        tool_result={
            "ok": True,
            "result": {"ticket_id": "t_001"},
            "metadata": {"source": "mock_support_backend"},
        },
        summary="Fetched ticket t_001.",
        facts={"ticket_id": "t_001"},
    )

    assert observation.tool_result.ok is True
