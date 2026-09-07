from pathlib import Path

import pytest

from bounded_agent.domain import Task, TerminalState
from bounded_agent.loop import ActionDecision, AgentRunner, RunnerConfig, RunnerRequest


class StaticDecisionSource:
    def __init__(self, decision: ActionDecision) -> None:
        self.decision = decision
        self.seen_contexts = []

    def decide(self, context):
        self.seen_contexts.append(context)
        return self.decision


def test_runner_builds_initial_context_for_decision_source():
    decision_source = StaticDecisionSource(resolved_decision())
    runner = AgentRunner(
        decision_source,
        config=RunnerConfig(trace_path=Path("data/runs/run_001/trace.jsonl")),
    )
    request = runner_request()

    result = runner.run(request)

    assert result.terminal_result.terminal_state is TerminalState.RESOLVED
    assert result.state.terminal_state is TerminalState.RESOLVED
    assert len(decision_source.seen_contexts) == 1
    context = decision_source.seen_contexts[0]
    assert context.request is request
    assert context.state.task_id == "task_001"
    assert context.state.goal == "Resolve duplicate charge ticket."
    assert context.step == 0
    assert context.budget_usage.max_steps == 12
    assert {tool.name for tool in context.available_tools} >= {"fetch_ticket", "request_approval"}


def test_runner_converts_terminal_action_to_terminal_result():
    runner = AgentRunner(
        StaticDecisionSource(resolved_decision()),
        config=RunnerConfig(trace_path=Path("data/runs/run_001/trace.jsonl")),
    )

    result = runner.run(runner_request())

    assert result.terminal_result.run_id == "run_001"
    assert result.terminal_result.ticket_id == "t_001"
    assert result.terminal_result.summary == "Duplicate charge was resolved."
    assert result.terminal_result.resolution_summary == "Refund and customer draft completed."
    assert result.terminal_result.final_ticket_status == "resolved"
    assert result.terminal_result.environment_changes == [{"type": "refund", "charge_id": "ch_001_b"}]
    assert result.terminal_result.trace_path == Path("data/runs/run_001/trace.jsonl")


def test_runner_fails_closed_for_non_terminal_actions_until_execution_is_implemented():
    decision = ActionDecision(
        thought_summary="Need to inspect the ticket.",
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
    runner = AgentRunner(
        StaticDecisionSource(decision),
        config=RunnerConfig(trace_path=Path("data/runs/run_001/trace.jsonl")),
    )

    result = runner.run(runner_request())

    assert result.terminal_result.terminal_state is TerminalState.FAILED_UNRECOVERABLE
    assert result.state.terminal_state is TerminalState.FAILED_UNRECOVERABLE
    assert "tool_call" in result.terminal_result.error_summary
    assert result.terminal_result.last_successful_step == 0
    assert result.terminal_result.trace_event_id.startswith("trace_")


def test_runner_request_rejects_blank_run_id():
    with pytest.raises(ValueError, match="run_id cannot be blank"):
        RunnerRequest(
            run_id=" ",
            task=Task(task_id="task_001", goal="Resolve duplicate charge ticket."),
            scenario_id="support_001",
            ticket_id="t_001",
        )


def test_runner_config_rejects_invalid_step_budget():
    with pytest.raises(ValueError, match="max_steps must be at least 1"):
        RunnerConfig(max_steps=0)


def runner_request() -> RunnerRequest:
    return RunnerRequest(
        run_id="run_001",
        task=Task(task_id="task_001", goal="Resolve duplicate charge ticket."),
        scenario_id="support_001",
        ticket_id="t_001",
    )


def resolved_decision() -> ActionDecision:
    return ActionDecision(
        thought_summary="All required work is complete.",
        action={
            "type": "set_terminal_state",
            "terminal_state": "resolved",
            "summary": "Duplicate charge was resolved.",
            "fields": {
                "resolution_summary": "Refund and customer draft completed.",
                "final_ticket_status": "resolved",
                "environment_changes": [{"type": "refund", "charge_id": "ch_001_b"}],
            },
        },
        safety_check={
            "permission_level": "low_risk_write",
            "approval_required": False,
        },
        stop_reason="done",
    )
