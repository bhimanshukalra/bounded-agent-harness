from bounded_agent.domain import (
    ActionType,
    ApprovalStatus,
    ErrorType,
    PermissionLevel,
    RunnerType,
    ScenarioDifficulty,
    ScenarioTag,
    TerminalState,
)


def enum_values(enum_type: type) -> set[str]:
    return {member.value for member in enum_type}


def test_terminal_state_values_are_stable():
    assert enum_values(TerminalState) == {
        "resolved",
        "needs_human_approval",
        "escalated",
        "blocked_missing_information",
        "blocked_tool_error",
        "failed_budget_exceeded",
        "failed_policy_violation",
        "failed_invalid_tool_call",
        "failed_unrecoverable",
    }


def test_permission_level_values_are_stable():
    assert enum_values(PermissionLevel) == {
        "read_only",
        "draft_only",
        "low_risk_write",
        "approval_required",
        "forbidden",
    }


def test_approval_status_values_are_stable():
    assert enum_values(ApprovalStatus) == {
        "pending",
        "approved",
        "denied",
        "expired",
        "cancelled",
    }


def test_action_type_values_are_stable():
    assert enum_values(ActionType) == {
        "tool_call",
        "request_approval",
        "set_terminal_state",
        "retry",
        "replan",
    }


def test_error_type_values_are_stable():
    assert enum_values(ErrorType) == {
        "not_found",
        "permission_denied",
        "validation_error",
        "timeout",
        "conflict",
        "already_exists",
        "transient_error",
        "policy_violation",
        "budget_exceeded",
        "unrecoverable",
    }


def test_runner_type_values_are_stable():
    assert enum_values(RunnerType) == {
        "agent_loop",
        "fixed_workflow_baseline",
        "single_call_baseline",
    }


def test_scenario_difficulty_values_are_stable():
    assert enum_values(ScenarioDifficulty) == {
        "easy",
        "medium",
        "hard",
    }


def test_scenario_tag_values_cover_phase_zero_drafts():
    assert enum_values(ScenarioTag) == {
        "happy_path",
        "duplicate_charge",
        "approval",
        "refund",
        "policy_denial",
        "resolved",
        "missing_info",
        "order",
        "customer",
        "blocked",
        "ambiguous_policy",
        "escalation",
        "tool_error",
        "retry",
        "approval_denied",
        "prompt_injection",
        "security",
        "idempotency",
        "approved_action",
        "budget",
        "safe_stop",
        "complex_case",
    }


def test_enums_behave_like_strings_for_json_values():
    assert TerminalState.RESOLVED == "resolved"
    assert PermissionLevel.READ_ONLY == "read_only"
    assert ScenarioDifficulty.HARD == "hard"
