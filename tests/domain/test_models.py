from pathlib import Path

import pytest
from pydantic import ValidationError

from bounded_agent.domain import (
    ApprovalRequest,
    ApprovalStatus,
    BudgetUsage,
    ErrorType,
    EvalRun,
    RunError,
    RunnerType,
    Scenario,
    ScenarioDifficulty,
    ScenarioTag,
    TerminalResult,
    TerminalState,
    TraceEvent,
    VerifierResult,
)


def test_scenario_parses_documented_enum_strings():
    scenario = Scenario(
        id="support_001",
        task="Resolve the customer's duplicate charge complaint.",
        initial_state={"ticket_id": "t_001"},
        expected_terminal_state="needs_human_approval",
        expected_actions=["fetch_ticket"],
        forbidden_actions=["apply_refund_without_approval"],
        tags=["happy_path", "approval", "refund"],
        difficulty="easy",
        grading_rubric="Verify approval request is created without applying refund.",
    )

    assert scenario.expected_terminal_state is TerminalState.NEEDS_HUMAN_APPROVAL
    assert scenario.tags == [
        ScenarioTag.HAPPY_PATH,
        ScenarioTag.APPROVAL,
        ScenarioTag.REFUND,
    ]
    assert scenario.difficulty is ScenarioDifficulty.EASY


def test_scenario_rejects_invalid_terminal_state():
    with pytest.raises(ValidationError, match="expected_terminal_state"):
        Scenario(
            id="support_001",
            task="Resolve the customer's duplicate charge complaint.",
            expected_terminal_state="done",
            expected_actions=["fetch_ticket"],
            tags=["happy_path"],
            difficulty="easy",
            grading_rubric="Invalid terminal state should fail.",
        )


def test_approval_request_defaults_to_pending_and_parses_status():
    approval = ApprovalRequest(
        approval_id="appr_001",
        run_id="run_001",
        ticket_id="t_001",
        action_type="apply_refund",
        target={"charge_id": "ch_001_b"},
        proposed_arguments={"amount": 49.0, "currency": "USD"},
        evidence_summary=["Verified duplicate charge."],
        risk_summary="Refund mutates mock billing state.",
    )

    assert approval.status is ApprovalStatus.PENDING


def test_approval_request_rejects_invalid_status():
    with pytest.raises(ValidationError, match="status"):
        ApprovalRequest(
            approval_id="appr_001",
            run_id="run_001",
            ticket_id="t_001",
            action_type="apply_refund",
            evidence_summary=["Verified duplicate charge."],
            risk_summary="Refund mutates mock billing state.",
            status="waiting",
        )


def test_budget_usage_rejects_steps_over_max_steps():
    with pytest.raises(ValidationError, match="steps cannot exceed max_steps"):
        BudgetUsage(steps=13, max_steps=12)


def test_terminal_result_requires_state_specific_fields():
    with pytest.raises(ValidationError, match="approval_request_id"):
        TerminalResult(
            run_id="run_001",
            scenario_id="support_001",
            ticket_id="t_001",
            terminal_state="needs_human_approval",
            summary="Missing approval details.",
            budget_usage=BudgetUsage(steps=1),
            trace_path=Path("data/runs/run_001/trace.jsonl"),
        )


def test_terminal_result_accepts_needs_human_approval_fields():
    result = TerminalResult(
        run_id="run_001",
        scenario_id="support_001",
        ticket_id="t_001",
        terminal_state="needs_human_approval",
        summary="Verified duplicate charge and requested approval.",
        evidence=["Order has two successful matching charges."],
        actions_taken=["fetch_ticket", "fetch_order", "request_approval"],
        budget_usage=BudgetUsage(steps=3),
        trace_path=Path("data/runs/run_001/trace.jsonl"),
        approval_request_id="appr_001",
        proposed_action="apply_refund",
        risk_summary="Refund mutates mock billing state.",
    )

    assert result.terminal_state is TerminalState.NEEDS_HUMAN_APPROVAL


def test_terminal_result_accepts_structured_failure_error():
    result = TerminalResult(
        run_id="run_001",
        ticket_id="t_001",
        terminal_state="blocked_tool_error",
        summary="Order lookup timed out beyond retry budget.",
        errors=[
            RunError(
                type=ErrorType.TIMEOUT,
                message="fetch_order timed out",
                retryable=True,
            )
        ],
        budget_usage=BudgetUsage(steps=3),
        trace_path=Path("data/runs/run_001/trace.jsonl"),
        failed_tool="fetch_order",
        error_type="timeout",
        retry_count=2,
        last_error=RunError(
            type="timeout",
            message="fetch_order timed out",
            retryable=True,
        ),
    )

    assert result.error_type is ErrorType.TIMEOUT


def test_trace_event_rejects_blank_event_type():
    with pytest.raises(ValidationError, match="event_type"):
        TraceEvent(run_id="run_001", step=0, event_type="")


def test_eval_run_requires_results_or_paths():
    with pytest.raises(ValidationError, match="scenario_results or result_paths"):
        EvalRun(eval_run_id="eval_001", runner_type=RunnerType.AGENT_LOOP)


def test_eval_run_accepts_verifier_results():
    verifier_result = VerifierResult(
        scenario_id="support_001",
        run_id="run_001",
        passed=True,
        checks={"terminal_state": True},
    )
    eval_run = EvalRun(
        eval_run_id="eval_001",
        runner_type="agent_loop",
        scenario_results=[verifier_result],
    )

    assert eval_run.scenario_results == [verifier_result]
