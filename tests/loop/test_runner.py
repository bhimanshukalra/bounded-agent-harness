from pathlib import Path

import pytest

from bounded_agent.config import Settings
from bounded_agent.domain import Task, TerminalState
from bounded_agent.loop import (
    ActionDecision,
    AgentRunner,
    RunnerConfig,
    RunnerRequest,
    scenario_ticket_id,
)
from bounded_agent.state import connect_database


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


def test_runner_loads_scenario_and_resets_environment(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    decision_source = StaticDecisionSource(resolved_decision())
    runner = AgentRunner(
        decision_source,
        config=RunnerConfig(max_steps=7, trace_path=Path("data/runs/run_001/trace.jsonl")),
        settings=settings,
    )

    result = runner.run_scenario("support_001", "run_001")

    assert result.scenario is not None
    assert result.scenario.id == "support_001"
    assert result.db_path == tmp_path / "runs" / "run_001" / "state.db"
    assert result.db_path.exists()
    assert result.state.task_id == "support_001"
    assert result.state.goal == "Resolve the customer's duplicate charge complaint."
    assert result.state.scenario_id == "support_001"
    assert result.state.budget_usage.max_steps == 7

    context = decision_source.seen_contexts[0]
    assert context.scenario is result.scenario
    assert context.db_path == result.db_path
    assert context.request.ticket_id == "t_001"

    connection = connect_database(result.db_path)
    try:
        assert connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 10
    finally:
        connection.close()


def test_scenario_ticket_id_rejects_missing_ticket_id():
    scenario = object_without_ticket_id()

    with pytest.raises(ValueError, match="initial_state.ticket_id"):
        scenario_ticket_id(scenario)


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


def object_without_ticket_id():
    from bounded_agent.domain import Scenario

    return Scenario(
        id="support_missing_ticket",
        task="Resolve a ticket with malformed scenario state.",
        expected_terminal_state="blocked_missing_information",
        expected_actions=["fetch_ticket"],
        tags=["missing_info"],
        difficulty="easy",
        grading_rubric="Scenario is invalid for runner loading.",
    )
