import pytest
from pydantic import ValidationError

from bounded_agent.domain import ActionType, ErrorType, PermissionLevel, TerminalState
from bounded_agent.loop import (
    ActionDecision,
    ApprovalRequestAction,
    ReplanAction,
    RetryAction,
    SafetyCheck,
    TerminalStateAction,
    ToolCallAction,
)


def test_action_decision_accepts_tool_call_action():
    decision = ActionDecision(
        thought_summary="Need to inspect the ticket before deciding next step.",
        action={
            "type": "tool_call",
            "tool_name": "fetch_ticket",
            "arguments": {"ticket_id": "t_001"},
        },
        safety_check={
            "permission_level": "read_only",
            "approval_required": False,
        },
    )

    assert isinstance(decision.action, ToolCallAction)
    assert decision.action.type is ActionType.TOOL_CALL
    assert decision.safety_check.permission_level is PermissionLevel.READ_ONLY


def test_action_decision_rejects_unknown_action_type():
    with pytest.raises(ValidationError, match="union_tag_invalid"):
        ActionDecision(
            thought_summary="Try an unsupported action.",
            action={"type": "send_email", "arguments": {}},
            safety_check={
                "permission_level": "read_only",
                "approval_required": False,
            },
        )


def test_action_decision_rejects_unknown_permission_level():
    with pytest.raises(ValidationError, match="permission_level"):
        ActionDecision(
            thought_summary="Need to inspect the ticket.",
            action={
                "type": "tool_call",
                "tool_name": "fetch_ticket",
                "arguments": {"ticket_id": "t_001"},
            },
            safety_check={
                "permission_level": "admin",
                "approval_required": False,
            },
        )


def test_approval_request_action_requires_evidence():
    with pytest.raises(ValidationError, match="evidence_summary"):
        ApprovalRequestAction(
            action_type="apply_refund",
            target={"charge_id": "ch_001"},
            proposed_arguments={"amount": 49.0},
            evidence_summary=[],
            risk_summary="Refund mutates billing state.",
        )


def test_terminal_state_action_parses_terminal_state():
    action = TerminalStateAction(
        terminal_state="needs_human_approval",
        summary="Approval is required before refund.",
        fields={"approval_request_id": "appr_001"},
    )

    assert action.terminal_state is TerminalState.NEEDS_HUMAN_APPROVAL


def test_retry_action_parses_error_type():
    action = RetryAction(
        failed_tool="fetch_order",
        error_type="timeout",
        retry_reason="Transient timeout, retry within budget.",
    )

    assert action.error_type is ErrorType.TIMEOUT


def test_replan_action_requires_next_goal():
    with pytest.raises(ValidationError, match="next_goal"):
        ReplanAction(reason="Need another path.", known_facts={})


def test_safety_check_rejects_extra_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        SafetyCheck(
            permission_level="read_only",
            approval_required=False,
            untrusted_content_used=False,
            hidden_override=True,
        )
