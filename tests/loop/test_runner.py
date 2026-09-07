from pathlib import Path

import pytest

from bounded_agent.config import Settings
from bounded_agent.domain import AgentState, BudgetUsage, ErrorType, Task, TerminalState
from bounded_agent.evals import load_scenario
from bounded_agent.loop import (
    ActionDecision,
    AgentRunner,
    DecisionParseError,
    DeterministicDecisionSource,
    ModelBackedDecisionSource,
    RunnerConfig,
    RunnerRequest,
    build_bounded_context,
    parse_action_decision,
    scenario_ticket_id,
    validate_action_decision,
)
from bounded_agent.state import connect_database
from bounded_agent.tools import ToolResult, build_default_registry


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
    assert context.bounded_context.task_id == "task_001"
    assert context.bounded_context.ticket_id == "t_001"
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


def test_runner_stops_with_invalid_tool_call_for_failed_action_validation():
    decision = ActionDecision(
        thought_summary="Fetch the ticket.",
        action={
            "type": "tool_call",
            "tool_name": "fetch_ticket",
            "arguments": {},
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

    assert result.terminal_result.terminal_state is TerminalState.FAILED_INVALID_TOOL_CALL
    assert result.terminal_result.tool_name == "fetch_ticket"
    assert result.terminal_result.retry_count == 0
    assert result.terminal_result.validation_errors == ["Tool input failed validation.: ticket_id"]


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


def test_bounded_context_payload_contains_decision_inputs_without_raw_db_path():
    scenario = load_scenario("support_001")
    observation = successful_observation()
    request = runner_request()
    state = AgentState(
        task_id=request.task.task_id,
        goal=request.task.goal,
        scenario_id=request.scenario_id,
        known_facts={"ticket_id": "t_001"},
        completed_actions=["fetch_ticket"],
        pending_approval_ids=["approval_001"],
        retries_by_failure_type={ErrorType.TIMEOUT: 1},
        budget_usage=BudgetUsage(
            steps=1,
            max_steps=5,
            estimated_tokens=120,
            token_budget=500,
            estimated_cost_usd=0.02,
            cost_budget_usd=1.0,
        ),
    )

    context = build_bounded_context(
        request=request,
        state=state,
        observations=[observation],
        available_tools=build_default_registry().list_specs(),
        scenario=scenario,
    )
    payload = context.to_decision_payload()

    assert payload["task"] == {
        "task_id": "task_001",
        "goal": "Resolve duplicate charge ticket.",
        "ticket_id": "t_001",
        "scenario_id": "support_001",
    }
    assert payload["state"]["known_facts"] == {"ticket_id": "t_001"}
    assert payload["state"]["completed_actions"] == ["fetch_ticket"]
    assert payload["state"]["pending_approval_ids"] == ["approval_001"]
    assert payload["state"]["retry_counts"] == {"timeout": 1}
    assert payload["budget"]["steps"] == 1
    assert payload["budget"]["max_steps"] == 5
    assert "Use only registered tools supplied in this context." in payload["safety_constraints"]
    assert "db_path" not in payload
    assert "fetch_ticket" in {tool["name"] for tool in payload["available_tools"]}
    fetch_ticket = next(tool for tool in payload["available_tools"] if tool["name"] == "fetch_ticket")
    assert fetch_ticket["permission_level"] == "read_only"
    assert fetch_ticket["mutates_state"] is False
    assert payload["observations"] == [
        {
            "tool_name": "fetch_ticket",
            "summary": "Fetched ticket t_001.",
            "facts": {"ticket_id": "t_001"},
            "ok": True,
            "error_type": None,
        }
    ]
    assert payload["scenario"]["id"] == "support_001"
    assert payload["scenario"]["initial_state"]["ticket_id"] == "t_001"


def test_parse_action_decision_accepts_dict_payload():
    decision = parse_action_decision(resolved_decision_payload())

    assert decision.action.terminal_state is TerminalState.RESOLVED
    assert decision.stop_reason == "done"


def test_parse_action_decision_accepts_json_payload():
    raw_json = ActionDecision.model_validate(resolved_decision_payload()).model_dump_json()

    decision = parse_action_decision(raw_json)

    assert decision.action.terminal_state is TerminalState.RESOLVED


def test_parse_action_decision_rejects_malformed_payload():
    with pytest.raises(DecisionParseError, match="invalid action decision"):
        parse_action_decision(
            {
                "thought_summary": "Missing safety and action fields.",
                "action": {"type": "send_email"},
            }
        )


def test_deterministic_decision_source_returns_parsed_decisions_in_order():
    source = DeterministicDecisionSource(
        [
            {
                "thought_summary": "Inspect the ticket first.",
                "action": {
                    "type": "tool_call",
                    "tool_name": "fetch_ticket",
                    "arguments": {"ticket_id": "t_001"},
                },
                "safety_check": {
                    "permission_level": "read_only",
                    "approval_required": False,
                },
            },
            resolved_decision_payload(),
        ]
    )
    context = runner_context()

    first = source.decide(context)
    second = source.decide(context)

    assert first.action.tool_name == "fetch_ticket"
    assert second.action.terminal_state is TerminalState.RESOLVED


def test_deterministic_decision_source_rejects_empty_sequence():
    with pytest.raises(ValueError, match="at least one decision"):
        DeterministicDecisionSource([])


def test_deterministic_decision_source_rejects_exhausted_sequence():
    source = DeterministicDecisionSource([resolved_decision_payload()])
    context = runner_context()

    source.decide(context)

    with pytest.raises(DecisionParseError, match="no remaining decisions"):
        source.decide(context)


def test_model_backed_decision_source_passes_bounded_payload_to_client():
    client = RecordingModelDecisionClient(resolved_decision_payload())
    source = ModelBackedDecisionSource(client)
    context = runner_context()

    decision = source.decide(context)

    assert decision.action.terminal_state is TerminalState.RESOLVED
    assert client.seen_payloads == [context.bounded_context.to_decision_payload()]


def test_validate_action_decision_accepts_valid_tool_call():
    decision = ActionDecision(
        thought_summary="Fetch the ticket.",
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

    validation = validate_action_decision(decision, build_default_registry())

    assert validation.valid is True
    assert validation.tool_name == "fetch_ticket"
    assert validation.errors == ()


def test_validate_action_decision_rejects_unknown_tool_call():
    decision = ActionDecision(
        thought_summary="Try an unknown tool.",
        action={
            "type": "tool_call",
            "tool_name": "run_shell",
            "arguments": {},
        },
        safety_check={
            "permission_level": "read_only",
            "approval_required": False,
        },
    )

    validation = validate_action_decision(decision, build_default_registry())

    assert validation.valid is False
    assert validation.tool_name == "run_shell"
    assert validation.errors == ("Unknown tool.",)


def test_validate_action_decision_rejects_invalid_tool_arguments():
    decision = ActionDecision(
        thought_summary="Fetch without required input.",
        action={
            "type": "tool_call",
            "tool_name": "fetch_ticket",
            "arguments": {},
        },
        safety_check={
            "permission_level": "read_only",
            "approval_required": False,
        },
    )

    validation = validate_action_decision(decision, build_default_registry())

    assert validation.valid is False
    assert validation.tool_name == "fetch_ticket"
    assert validation.errors == ("Tool input failed validation.: ticket_id",)


def test_validate_action_decision_accepts_approval_request_for_approval_required_tool():
    decision = ActionDecision(
        thought_summary="Need approval before refund.",
        action={
            "type": "request_approval",
            "action_type": "apply_refund",
            "target": {"ticket_id": "t_001"},
            "proposed_arguments": {"charge_id": "ch_001_b"},
            "evidence_summary": ["Duplicate successful charge confirmed."],
            "risk_summary": "Refund mutates billing state.",
        },
        safety_check={
            "permission_level": "approval_required",
            "approval_required": True,
        },
    )

    validation = validate_action_decision(decision, build_default_registry())

    assert validation.valid is True
    assert validation.tool_name == "apply_refund"


def test_validate_action_decision_rejects_approval_request_for_non_approval_tool():
    decision = ActionDecision(
        thought_summary="Ask approval for a read.",
        action={
            "type": "request_approval",
            "action_type": "fetch_ticket",
            "target": {"ticket_id": "t_001"},
            "proposed_arguments": {"ticket_id": "t_001"},
            "evidence_summary": ["Need ticket details."],
            "risk_summary": "Read-only operation.",
        },
        safety_check={
            "permission_level": "read_only",
            "approval_required": False,
        },
    )

    validation = validate_action_decision(decision, build_default_registry())

    assert validation.valid is False
    assert validation.tool_name == "fetch_ticket"
    assert validation.errors == ("action does not require approval: fetch_ticket",)


def test_validate_action_decision_rejects_terminal_action_missing_state_fields():
    decision = ActionDecision(
        thought_summary="Stop too early.",
        action={
            "type": "set_terminal_state",
            "terminal_state": "resolved",
            "summary": "Resolved.",
            "fields": {},
        },
        safety_check={
            "permission_level": "low_risk_write",
            "approval_required": False,
        },
    )

    validation = validate_action_decision(decision, build_default_registry())

    assert validation.valid is False
    assert validation.tool_name == "set_terminal_state"
    assert validation.errors == (
        (
            "Value error, resolved requires fields: resolution_summary, "
            "final_ticket_status, environment_changes"
        ),
    )


def test_validate_action_decision_rejects_retry_for_unknown_tool():
    decision = ActionDecision(
        thought_summary="Retry a missing tool.",
        action={
            "type": "retry",
            "failed_tool": "missing_tool",
            "error_type": "timeout",
        },
        safety_check={
            "permission_level": "read_only",
            "approval_required": False,
        },
    )

    validation = validate_action_decision(decision, build_default_registry())

    assert validation.valid is False
    assert validation.tool_name == "missing_tool"
    assert validation.errors == ("unknown retry tool: missing_tool",)


def runner_request() -> RunnerRequest:
    return RunnerRequest(
        run_id="run_001",
        task=Task(task_id="task_001", goal="Resolve duplicate charge ticket."),
        scenario_id="support_001",
        ticket_id="t_001",
    )


def resolved_decision() -> ActionDecision:
    return ActionDecision.model_validate(resolved_decision_payload())


def resolved_decision_payload():
    return {
        "thought_summary": "All required work is complete.",
        "action": {
            "type": "set_terminal_state",
            "terminal_state": "resolved",
            "summary": "Duplicate charge was resolved.",
            "fields": {
                "resolution_summary": "Refund and customer draft completed.",
                "final_ticket_status": "resolved",
                "environment_changes": [{"type": "refund", "charge_id": "ch_001_b"}],
            },
        },
        "safety_check": {
            "permission_level": "low_risk_write",
            "approval_required": False,
        },
        "stop_reason": "done",
    }


def runner_context():
    from bounded_agent.loop import RunnerContext

    request = runner_request()
    state = AgentState(
        task_id=request.task.task_id,
        goal=request.task.goal,
        scenario_id=request.scenario_id,
        budget_usage=BudgetUsage(max_steps=5),
    )
    available_tools = tuple(build_default_registry().list_specs())
    bounded_context = build_bounded_context(
        request=request,
        state=state,
        observations=[],
        available_tools=available_tools,
    )
    return RunnerContext(
        request=request,
        state=state,
        step=0,
        observations=(),
        available_tools=available_tools,
        budget_usage=state.budget_usage,
        bounded_context=bounded_context,
    )


class RecordingModelDecisionClient:
    def __init__(self, decision):
        self.decision = decision
        self.seen_payloads = []

    def complete(self, payload):
        self.seen_payloads.append(payload)
        return self.decision


def successful_observation():
    from bounded_agent.tools import Observation

    return Observation(
        tool_name="fetch_ticket",
        tool_result=ToolResult(
            ok=True,
            result={"ticket": {"ticket_id": "t_001"}},
            metadata={"source": "test"},
        ),
        summary="Fetched ticket t_001.",
        facts={"ticket_id": "t_001"},
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
