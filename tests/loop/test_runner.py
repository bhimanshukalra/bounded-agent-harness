import json

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
from bounded_agent.tools import Observation, ToolResult, build_default_registry


class StaticDecisionSource:
    def __init__(self, decision: ActionDecision) -> None:
        self.decision = decision
        self.seen_contexts = []

    def decide(self, context):
        self.seen_contexts.append(context)
        return self.decision


def test_runner_builds_initial_context_for_decision_source(tmp_path):
    decision_source = StaticDecisionSource(resolved_decision())
    runner = AgentRunner(
        decision_source,
        config=runner_config(tmp_path),
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


def test_runner_converts_terminal_action_to_terminal_result(tmp_path):
    config = runner_config(tmp_path)
    runner = AgentRunner(
        StaticDecisionSource(resolved_decision()),
        config=config,
    )

    result = runner.run(runner_request())

    assert result.terminal_result.run_id == "run_001"
    assert result.terminal_result.ticket_id == "t_001"
    assert result.terminal_result.summary == "Duplicate charge was resolved."
    assert result.terminal_result.resolution_summary == "Refund and customer draft completed."
    assert result.terminal_result.final_ticket_status == "resolved"
    assert result.terminal_result.environment_changes == [{"type": "refund", "charge_id": "ch_001_b"}]
    assert result.terminal_result.trace_path == config.trace_path


def test_runner_fails_closed_for_non_terminal_actions_until_execution_is_implemented(tmp_path):
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
        config=runner_config(tmp_path),
    )

    result = runner.run(runner_request())

    assert result.terminal_result.terminal_state is TerminalState.FAILED_UNRECOVERABLE
    assert result.state.terminal_state is TerminalState.FAILED_UNRECOVERABLE
    assert "tool_call" in result.terminal_result.error_summary
    assert result.terminal_result.last_successful_step == 0
    assert result.terminal_result.trace_event_id.startswith("trace_")


def test_runner_stops_with_invalid_tool_call_for_failed_action_validation(tmp_path):
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
        config=runner_config(tmp_path),
    )

    result = runner.run(runner_request())

    assert result.terminal_result.terminal_state is TerminalState.FAILED_INVALID_TOOL_CALL
    assert result.terminal_result.tool_name == "fetch_ticket"
    assert result.terminal_result.retry_count == 0
    assert result.terminal_result.validation_errors == ["Tool input failed validation.: ticket_id"]


def test_runner_executes_tool_call_through_registry_and_records_observation(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    source = DeterministicDecisionSource(
        [
            {
                "thought_summary": "Inspect the ticket.",
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
    runner = AgentRunner(
        source,
        config=runner_config(tmp_path),
        settings=settings,
    )

    result = runner.run_scenario("support_001", "run_001")

    assert result.terminal_result.terminal_state is TerminalState.RESOLVED
    assert result.state.budget_usage.steps == 1
    assert len(result.observations) == 1
    observation = result.observations[0]
    assert observation.tool_name == "fetch_ticket"
    assert observation.tool_result.ok is True
    assert observation.tool_result.result["ticket"]["ticket_id"] == "t_001"
    assert observation.summary == "Executed fetch_ticket."
    assert observation.facts["ticket"]["ticket_id"] == "t_001"


def test_runner_records_structured_tool_error_observation(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    source = DeterministicDecisionSource(
        [
            {
                "thought_summary": "Fetch a missing order.",
                "action": {
                    "type": "tool_call",
                    "tool_name": "fetch_order",
                    "arguments": {"order_id": "o_missing"},
                },
                "safety_check": {
                    "permission_level": "read_only",
                    "approval_required": False,
                },
            },
            blocked_tool_error_decision_payload(),
        ]
    )
    runner = AgentRunner(
        source,
        config=runner_config(tmp_path),
        settings=settings,
    )

    result = runner.run_scenario("support_001", "run_001")

    assert result.terminal_result.terminal_state is TerminalState.BLOCKED_TOOL_ERROR
    assert len(result.observations) == 1
    observation = result.observations[0]
    assert observation.tool_name == "fetch_order"
    assert observation.tool_result.ok is False
    assert observation.tool_result.error.type is ErrorType.NOT_FOUND
    assert observation.summary == "fetch_order failed: Order was not found."
    assert observation.facts == {
        "error_type": "not_found",
        "retryable": False,
        "details": {"order_id": "o_missing"},
    }


def test_runner_preserves_mutating_tool_idempotency(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    add_comment_decision = {
        "thought_summary": "Add the verified duplicate charge note.",
        "action": {
            "type": "tool_call",
            "tool_name": "add_ticket_comment",
            "arguments": {"ticket_id": "t_001", "body": "Verified duplicate charges."},
        },
        "safety_check": {
            "permission_level": "low_risk_write",
            "approval_required": False,
        },
    }
    source = DeterministicDecisionSource(
        [add_comment_decision, add_comment_decision, resolved_decision_payload()]
    )
    runner = AgentRunner(
        source,
        config=runner_config(tmp_path),
        settings=settings,
    )

    result = runner.run_scenario("support_001", "run_001")

    assert result.terminal_result.terminal_state is TerminalState.RESOLVED
    assert result.state.budget_usage.steps == 2
    assert len(result.observations) == 2
    assert result.observations[0].tool_result.result == result.observations[1].tool_result.result
    assert result.observations[1].tool_result.metadata == {"source": "idempotency_replay"}

    connection = connect_database(result.db_path)
    try:
        assert connection.execute("SELECT COUNT(*) FROM ticket_comments").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM idempotency_keys").fetchone()[0] == 1
    finally:
        connection.close()


def test_runner_updates_state_after_tool_calls_and_errors(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    source = DeterministicDecisionSource(
        [
            {
                "thought_summary": "Fetch a missing order.",
                "action": {
                    "type": "tool_call",
                    "tool_name": "fetch_order",
                    "arguments": {"order_id": "o_missing"},
                },
                "safety_check": {
                    "permission_level": "read_only",
                    "approval_required": False,
                },
            },
            blocked_tool_error_decision_payload(),
        ]
    )
    runner = AgentRunner(source, config=runner_config(tmp_path), settings=settings)

    result = runner.run_scenario("support_001", "run_001")

    assert result.state.completed_actions == ["fetch_order"]
    assert result.state.tool_call_history == [
        {
            "tool_name": "fetch_order",
            "arguments": {"order_id": "o_missing"},
            "ok": False,
        }
    ]
    assert result.state.retries_by_failure_type == {}
    assert result.state.current_status == "observed:fetch_order"


def test_runner_tracks_pending_approval_requests(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    source = ApprovalThenStopDecisionSource()
    runner = AgentRunner(source, config=runner_config(tmp_path), settings=settings)

    result = runner.run_scenario("support_001", "run_001")

    assert len(result.state.pending_approval_ids) == 1
    approval_id = result.state.pending_approval_ids[0]
    assert approval_id.startswith("approval_")
    assert result.state.completed_actions == ["request_approval"]
    assert result.state.budget_usage.steps == 1
    assert result.state.current_status == "approval_requested"
    assert result.terminal_result.terminal_state is TerminalState.NEEDS_HUMAN_APPROVAL
    assert result.terminal_result.approval_request_id == approval_id
    connection = connect_database(result.db_path)
    approval = connection.execute(
        "SELECT status, action_type FROM approvals WHERE approval_id = ?", (approval_id,)
    ).fetchone()
    connection.close()
    assert dict(approval) == {"status": "pending", "action_type": "apply_refund"}


def test_runner_writes_trace_events_for_decisions_tools_observations_and_terminal(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    source = DeterministicDecisionSource(
        [
            {
                "thought_summary": "Inspect the ticket.",
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
    config = runner_config(tmp_path)
    runner = AgentRunner(source, config=config, settings=settings)

    runner.run_scenario("support_001", "run_001")

    events = read_trace_events(config.trace_path)
    assert [event["event_type"] for event in events] == [
        "decision",
        "tool_call",
        "observation",
        "decision",
        "terminal_state",
    ]
    assert events[0]["payload"]["action"]["tool_name"] == "fetch_ticket"
    assert events[1]["payload"] == {
        "arguments": {"ticket_id": "t_001"},
        "metadata": {"source": "mock_support_environment"},
        "ok": True,
        "tool_name": "fetch_ticket",
    }
    assert events[2]["payload"]["ok"] is True
    assert events[-1]["payload"]["terminal_state"] == "resolved"


def test_runner_records_mcp_backed_policy_lookup_for_mcp_dependent_scenario(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    source = DeterministicDecisionSource(
        [
            {
                "thought_summary": "Search MCP-backed policy knowledge for bundle rules.",
                "action": {
                    "type": "tool_call",
                    "tool_name": "search_policy",
                    "arguments": {"query": "bundle"},
                },
                "safety_check": {
                    "permission_level": "read_only",
                    "approval_required": False,
                },
            },
            {
                "thought_summary": "Policy ambiguity requires a specialist review.",
                "action": {
                    "type": "set_terminal_state",
                    "terminal_state": "escalated",
                    "summary": "Bundled promotional refund needs policy review.",
                    "fields": {
                        "escalation_reason": "Bundle terms do not establish separable pricing.",
                        "recommended_owner": "policy_specialist",
                        "open_questions": ["Are item-level prices separable under the promotion?"],
                    },
                },
                "safety_check": {
                    "permission_level": "read_only",
                    "approval_required": False,
                },
                "stop_reason": "policy_ambiguity",
            },
        ]
    )
    config = runner_config(tmp_path)
    runner = AgentRunner(source, config=config, settings=settings)

    result = runner.run_scenario("support_005", "run_005")

    assert result.terminal_result.terminal_state is TerminalState.ESCALATED
    assert result.state.completed_actions == ["search_policy"]
    assert result.observations[0].tool_result.metadata["source"] == "local_mcp"
    events = read_trace_events(config.trace_path)
    assert events[1]["payload"]["tool_name"] == "search_policy"
    assert events[1]["payload"]["metadata"]["mcp_tool"] == "search_knowledge_base"
    persisted = json.loads(result.result_path.read_text())
    assert persisted["terminal_state"] == "escalated"
    assert persisted["scenario_id"] == "support_005"


def test_runner_resumes_interrupted_mcp_scenario_from_durable_state(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    initial_runner = AgentRunner(
        InterruptAfterFirstDecisionSource(search_policy_decision_payload()),
        config=runner_config(tmp_path),
        settings=settings,
    )

    with pytest.raises(RuntimeError, match="simulated interruption"):
        initial_runner.run_scenario("support_005", "run_005")

    resumed_runner = AgentRunner(
        DeterministicDecisionSource([escalated_bundle_decision_payload()]),
        config=runner_config(tmp_path),
        settings=settings,
    )
    result = resumed_runner.resume_scenario("run_005")

    assert result.terminal_result.terminal_state is TerminalState.ESCALATED
    assert result.state.completed_actions == ["search_policy"]
    assert len(result.observations) == 1
    assert result.observations[0].tool_result.metadata["source"] == "local_mcp"
    assert (tmp_path / "runs" / "run_005" / "memory" / "facts.md").exists()
    events = read_trace_events(tmp_path / "trace.jsonl")
    assert [event["event_type"] for event in events].count("tool_call") == 1


def test_runner_compacts_bounded_context_to_configured_observation_limit(tmp_path):
    runner = AgentRunner(
        StaticDecisionSource(resolved_decision()),
        config=RunnerConfig(
            trace_path=tmp_path / "trace.jsonl",
            max_context_observations=1,
        ),
    )
    request = runner_request()
    state = AgentState(task_id=request.task.task_id, goal=request.task.goal)
    observations = (
        successful_observation(),
        Observation(
            tool_name="search_policy",
            tool_result=ToolResult(ok=True, result={"policies": []}),
            summary="Executed search_policy.",
            facts={"policies": []},
        ),
    )

    context = runner._build_runner_context(
        request=request,
        state=state,
        observations=observations,
        scenario=None,
        db_path=None,
    )

    assert [observation["tool_name"] for observation in context.bounded_context.observations] == [
        "search_policy"
    ]


def test_runner_persists_terminal_result_to_default_run_output_path(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    runner = AgentRunner(
        DeterministicDecisionSource([resolved_decision_payload()]),
        config=runner_config(tmp_path),
        settings=settings,
    )

    result = runner.run_scenario("support_001", "run_001")

    assert result.result_path == tmp_path / "runs" / "run_001" / "result.json"
    persisted = json.loads(result.result_path.read_text())
    assert persisted["run_id"] == "run_001"
    assert persisted["scenario_id"] == "support_001"
    assert persisted["ticket_id"] == "t_001"
    assert persisted["terminal_state"] == "resolved"
    assert persisted["trace_path"] == str(result.terminal_result.trace_path)
    assert persisted["resolution_summary"] == "Refund and customer draft completed."
    assert persisted["final_ticket_status"] == "resolved"
    assert persisted["environment_changes"] == [{"type": "refund", "charge_id": "ch_001_b"}]


def test_runner_refuses_to_resume_terminal_run(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    runner = AgentRunner(
        DeterministicDecisionSource([resolved_decision_payload()]),
        config=runner_config(tmp_path),
        settings=settings,
    )
    runner.run_scenario("support_001", "run_001")

    with pytest.raises(ValueError, match="terminal runs cannot be resumed"):
        runner.resume_scenario("run_001")


def test_runner_persists_terminal_result_to_custom_result_path(tmp_path):
    result_path = tmp_path / "custom" / "terminal.json"
    runner = AgentRunner(
        StaticDecisionSource(resolved_decision()),
        config=RunnerConfig(trace_path=tmp_path / "trace.jsonl", result_path=result_path),
    )

    result = runner.run(runner_request())

    assert result.result_path == result_path
    assert result_path.exists()
    assert json.loads(result_path.read_text())["terminal_state"] == "resolved"


def test_runner_stops_before_decision_when_step_budget_is_exhausted(tmp_path):
    initial_state = AgentState(
        task_id="task_001",
        goal="Resolve duplicate charge ticket.",
        scenario_id="support_001",
        budget_usage=BudgetUsage(steps=1, max_steps=1),
        completed_actions=["fetch_ticket"],
    )
    source = StaticDecisionSource(resolved_decision())
    runner = AgentRunner(source, config=runner_config(tmp_path, max_steps=1))

    result = runner.run(runner_request(initial_state=initial_state))

    assert source.seen_contexts == []
    assert result.terminal_result.terminal_state is TerminalState.FAILED_BUDGET_EXCEEDED
    assert result.terminal_result.budget_type == "steps"
    assert result.terminal_result.budget_limit == 1.0
    assert result.terminal_result.budget_used == 1.0
    assert result.terminal_result.last_safe_state["budget_usage"]["steps"] == 1


def test_runner_emits_budget_terminal_after_tool_action_exhausts_steps(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    source = DeterministicDecisionSource(
        [
            {
                "thought_summary": "Inspect the ticket.",
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
    config = runner_config(tmp_path, max_steps=1)
    runner = AgentRunner(source, config=config, settings=settings)

    result = runner.run_scenario("support_001", "run_001")

    assert result.terminal_result.terminal_state is TerminalState.FAILED_BUDGET_EXCEEDED
    assert result.state.budget_usage.steps == 1
    assert len(result.observations) == 1
    assert [event["event_type"] for event in read_trace_events(config.trace_path)] == [
        "decision",
        "tool_call",
        "observation",
        "terminal_state",
    ]


def test_runner_does_not_retry_non_retryable_tool_errors(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    source = DeterministicDecisionSource(
        [
            {
                "thought_summary": "Fetch a missing order.",
                "action": {
                    "type": "tool_call",
                    "tool_name": "fetch_order",
                    "arguments": {"order_id": "o_missing"},
                },
                "safety_check": {
                    "permission_level": "read_only",
                    "approval_required": False,
                },
            },
            resolved_decision_payload(),
        ]
    )
    runner = AgentRunner(
        source,
        config=runner_config(tmp_path, max_retries_per_error_type=0),
        settings=settings,
    )

    result = runner.run_scenario("support_001", "run_001")

    assert result.terminal_result.terminal_state is TerminalState.RESOLVED
    assert result.state.retries_by_failure_type == {}


def test_runner_replans_once_after_an_invalid_action(tmp_path):
    source = DeterministicDecisionSource(
        [
            {
                "thought_summary": "Call an unknown tool.",
                "action": {"type": "tool_call", "tool_name": "unknown_tool", "arguments": {}},
                "safety_check": {"permission_level": "read_only", "approval_required": False},
            },
            resolved_decision_payload(),
        ]
    )
    runner = AgentRunner(
        source,
        config=RunnerConfig(
            trace_path=tmp_path / "trace.jsonl",
            max_invalid_actions=1,
        ),
    )

    result = runner.run(runner_request())

    assert result.terminal_result.terminal_state is TerminalState.RESOLVED
    assert result.state.invalid_action_count == 1
    assert result.state.safety_events == [
        {
            "event": "invalid_action",
            "tool_name": "unknown_tool",
            "errors": ["Unknown tool."],
            "invalid_action_count": 1,
        }
    ]


def test_runner_sanitizes_untrusted_ticket_content_in_later_context(tmp_path):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    source = ContextSequenceDecisionSource(
        [
            {
                "thought_summary": "Inspect the ticket as untrusted data.",
                "action": {
                    "type": "tool_call",
                    "tool_name": "fetch_ticket",
                    "arguments": {"ticket_id": "t_008"},
                },
                "safety_check": {"permission_level": "read_only", "approval_required": False},
            },
            escalated_bundle_decision_payload(),
        ]
    )
    runner = AgentRunner(source, config=runner_config(tmp_path), settings=settings)

    result = runner.run_scenario("support_008", "run_008")

    context = source.seen_contexts[1].bounded_context.to_decision_payload()
    ticket = context["observations"][0]["facts"]["ticket"]
    assert context["observations"][0]["content_trust"] == "untrusted_data"
    assert ticket["body"] == "[untrusted content omitted; see tool history]"
    assert result.state.safety_events
    assert result.state.safety_events[0]["event"] == "untrusted_instruction_marker"
    assert "ignore all previous" in result.observations[0].facts["ticket"]["body"].lower()


def test_runner_emits_unrecoverable_when_retry_budget_exhausts_without_tool_error(tmp_path):
    initial_state = AgentState(
        task_id="task_001",
        goal="Resolve duplicate charge ticket.",
        scenario_id="support_001",
        budget_usage=BudgetUsage(steps=1, max_steps=12),
        retries_by_failure_type={ErrorType.TIMEOUT: 1},
    )
    source = StaticDecisionSource(resolved_decision())
    runner = AgentRunner(source, config=runner_config(tmp_path, max_retries_per_error_type=0))

    result = runner.run(runner_request(initial_state=initial_state))

    assert source.seen_contexts == []
    assert result.terminal_result.terminal_state is TerminalState.FAILED_UNRECOVERABLE
    assert result.terminal_result.error_summary == "Retry budget exceeded for timeout."
    assert result.terminal_result.last_successful_step == 1


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
        config=runner_config(tmp_path, max_steps=7),
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
                "content_trust": "untrusted_data",
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


def test_validate_action_decision_rejects_non_retryable_error_type():
    decision = ActionDecision(
        thought_summary="Retry a permanent missing-record error.",
        action={
            "type": "retry",
            "failed_tool": "fetch_order",
            "error_type": "not_found",
        },
        safety_check={"permission_level": "read_only", "approval_required": False},
    )

    validation = validate_action_decision(decision, build_default_registry())

    assert validation.valid is False
    assert validation.errors == ("error type is not retryable: not_found",)


def test_runner_records_replan_as_a_bounded_transition(tmp_path):
    source = DeterministicDecisionSource(
        [
            {
                "thought_summary": "Replan using the validated ticket ID.",
                "action": {
                    "type": "replan",
                    "reason": "The prior action had invalid arguments.",
                    "known_facts": {"ticket_id": "t_001"},
                    "next_goal": "Fetch the ticket with its required ID.",
                },
                "safety_check": {"permission_level": "read_only", "approval_required": False},
            },
            resolved_decision_payload(),
        ]
    )
    runner = AgentRunner(source, config=runner_config(tmp_path))

    result = runner.run(runner_request())

    assert result.terminal_result.terminal_state is TerminalState.RESOLVED
    assert result.state.completed_actions == ["replan"]
    assert result.state.known_facts["ticket_id"] == "t_001"
    assert result.state.budget_usage.steps == 1


def runner_request(initial_state=None) -> RunnerRequest:
    return RunnerRequest(
        run_id="run_001",
        task=Task(task_id="task_001", goal="Resolve duplicate charge ticket."),
        scenario_id="support_001",
        ticket_id="t_001",
        initial_state=initial_state,
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


def search_policy_decision_payload():
    return {
        "thought_summary": "Search MCP-backed policy knowledge for bundle rules.",
        "action": {
            "type": "tool_call",
            "tool_name": "search_policy",
            "arguments": {"query": "bundle"},
        },
        "safety_check": {"permission_level": "read_only", "approval_required": False},
    }


def escalated_bundle_decision_payload():
    return {
        "thought_summary": "Policy ambiguity requires a specialist review.",
        "action": {
            "type": "set_terminal_state",
            "terminal_state": "escalated",
            "summary": "Bundled promotional refund needs policy review.",
            "fields": {
                "escalation_reason": "Bundle terms do not establish separable pricing.",
                "recommended_owner": "policy_specialist",
                "open_questions": ["Are item-level prices separable under the promotion?"],
            },
        },
        "safety_check": {"permission_level": "read_only", "approval_required": False},
        "stop_reason": "policy_ambiguity",
    }


def blocked_tool_error_decision_payload():
    return {
        "thought_summary": "The order lookup failed with a structured not-found error.",
        "action": {
            "type": "set_terminal_state",
            "terminal_state": "blocked_tool_error",
            "summary": "Order lookup failed.",
            "fields": {
                "failed_tool": "fetch_order",
                "error_type": "not_found",
                "retry_count": 0,
                "last_error": {
                    "type": "not_found",
                    "message": "Order was not found.",
                    "retryable": False,
                    "details": {"order_id": "o_missing"},
                },
            },
        },
        "safety_check": {
            "permission_level": "read_only",
            "approval_required": False,
        },
        "stop_reason": "tool_error",
    }


def approval_request_decision_payload():
    return {
        "thought_summary": "Request approval before applying a refund.",
        "action": {
            "type": "request_approval",
            "action_type": "apply_refund",
            "target": {"ticket_id": "t_001", "charge_id": "ch_001_b"},
            "proposed_arguments": {
                "charge_id": "ch_001_b",
                "amount": 49.0,
                "currency": "USD",
                "reason": "duplicate_charge",
            },
            "evidence_summary": ["Duplicate successful charge confirmed."],
            "risk_summary": "Refund mutates billing state.",
        },
        "safety_check": {
            "permission_level": "approval_required",
            "approval_required": True,
        },
    }


def needs_human_approval_decision_payload():
    return {
        "thought_summary": "Approval has been requested and the run should stop.",
        "action": {
            "type": "set_terminal_state",
            "terminal_state": "needs_human_approval",
            "summary": "Refund approval is pending.",
            "fields": {
                "approval_request_id": "run_001:approval:apply_refund:1",
                "proposed_action": "apply_refund",
                "risk_summary": "Refund mutates billing state.",
            },
        },
        "safety_check": {
            "permission_level": "approval_required",
            "approval_required": True,
        },
        "stop_reason": "approval_required",
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


class InterruptAfterFirstDecisionSource:
    def __init__(self, first_decision):
        self.first_decision = first_decision
        self.called = False

    def decide(self, _context):
        if self.called:
            raise RuntimeError("simulated interruption")
        self.called = True
        return ActionDecision.model_validate(self.first_decision)


class ApprovalThenStopDecisionSource:
    def decide(self, context):
        if not context.state.pending_approval_ids:
            return ActionDecision.model_validate(approval_request_decision_payload())
        payload = needs_human_approval_decision_payload()
        payload["action"]["fields"]["approval_request_id"] = context.state.pending_approval_ids[-1]
        return ActionDecision.model_validate(payload)


class ContextSequenceDecisionSource:
    def __init__(self, decisions):
        self.decisions = iter(decisions)
        self.seen_contexts = []

    def decide(self, context):
        self.seen_contexts.append(context)
        return ActionDecision.model_validate(next(self.decisions))


def runner_config(
    tmp_path,
    max_steps: int = 12,
    max_retries_per_error_type: int = 2,
) -> RunnerConfig:
    return RunnerConfig(
        max_steps=max_steps,
        max_retries_per_error_type=max_retries_per_error_type,
        trace_path=tmp_path / "trace.jsonl",
    )


def read_trace_events(trace_path):
    return [json.loads(line) for line in trace_path.read_text().splitlines()]


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
