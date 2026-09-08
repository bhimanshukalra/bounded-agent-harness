from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from bounded_agent.config import Settings, load_settings
from bounded_agent.domain import PermissionLevel, RunnerType, Scenario, TerminalState
from bounded_agent.evals.scenarios import load_scenario
from bounded_agent.evals.verifier import VerificationRequest, verify_run
from bounded_agent.loop import ActionDecision, AgentRunner, RunnerConfig
from bounded_agent.tools import build_default_registry


class EvaluationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eval_run_id: str = Field(min_length=1)
    scenario_ids: list[str] = Field(min_length=1)
    runner_types: list[RunnerType] = Field(
        default_factory=lambda: [RunnerType.AGENT_LOOP, RunnerType.FIXED_WORKFLOW_BASELINE]
    )
    max_steps: int = Field(default=12, ge=1)


class EvaluationAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eval_run_id: str
    scenario_id: str
    run_id: str
    runner_type: RunnerType
    terminal_state: TerminalState
    verifier_passed: bool
    verifier_failures: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    difficulty: str
    trace_path: Path
    verifier_path: Path
    steps: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0)


class EvaluationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eval_run_id: str
    attempts: list[EvaluationAttempt]
    metrics: dict[str, float]
    terminal_states: dict[str, int]
    tag_pass_rates: dict[str, float]
    difficulty_pass_rates: dict[str, float]
    artifact_dir: Path


def run_evaluation(config: EvaluationConfig, settings: Settings | None = None) -> EvaluationSummary:
    active_settings = settings or load_settings()
    artifact_dir = active_settings.eval_runs_dir / config.eval_run_id
    attempts: list[EvaluationAttempt] = []
    for runner_type in config.runner_types:
        for scenario_id in sorted(config.scenario_ids):
            scenario = load_scenario(scenario_id, active_settings)
            run_id = f"{config.eval_run_id}-{runner_type.value}-{scenario.id}"
            trace_path = artifact_dir / "traces" / f"{run_id}.jsonl"
            trace_path.unlink(missing_ok=True)
            runner = AgentRunner(
                FixedWorkflowDecisionSource(scenario),
                registry=build_default_registry(),
                config=RunnerConfig(
                    max_steps=scenario.initial_state.get("max_steps", config.max_steps),
                    trace_path=trace_path,
                ),
                settings=active_settings,
            )
            try:
                result = runner.run_scenario(scenario.id, run_id)
                verification = verify_run(VerificationRequest(run_id=run_id), active_settings)
                terminal_state = result.terminal_result.terminal_state
                verifier_passed = verification.passed
                verifier_failures = verification.failures
                attempt_trace_path = result.terminal_result.trace_path
                steps = result.state.budget_usage.steps
                estimated_cost_usd = result.state.budget_usage.estimated_cost_usd
            except (FileNotFoundError, ValueError, RuntimeError) as exc:
                terminal_state = TerminalState.FAILED_UNRECOVERABLE
                verifier_passed = False
                verifier_failures = [f"evaluation_attempt: {exc}"]
                attempt_trace_path = trace_path
                steps = 0
                estimated_cost_usd = 0.0
            attempts.append(
                EvaluationAttempt(
                    eval_run_id=config.eval_run_id,
                    scenario_id=scenario.id,
                    run_id=run_id,
                    runner_type=runner_type,
                    terminal_state=terminal_state,
                    verifier_passed=verifier_passed,
                    verifier_failures=verifier_failures,
                    tags=[tag.value for tag in scenario.tags],
                    difficulty=scenario.difficulty.value,
                    trace_path=attempt_trace_path,
                    verifier_path=active_settings.eval_runs_dir / run_id / "verification.json",
                    steps=steps,
                    estimated_cost_usd=estimated_cost_usd,
                )
            )

    summary = EvaluationSummary(
        eval_run_id=config.eval_run_id,
        attempts=attempts,
        metrics=evaluation_metrics(attempts),
        terminal_states=terminal_state_counts(attempts),
        tag_pass_rates=tag_pass_rates(attempts),
        difficulty_pass_rates=difficulty_pass_rates(attempts),
        artifact_dir=artifact_dir,
    )
    persist_evaluation(summary)
    return summary


class FixedWorkflowDecisionSource:
    """A deterministic, non-adaptive baseline that follows declared scenario actions."""

    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        self.index = 0
        self.registry = build_default_registry()

    def decide(self, context) -> ActionDecision:
        if self.index < len(self.scenario.expected_actions):
            tool_name = self.scenario.expected_actions[self.index]
            self.index += 1
            if tool_name == "request_approval":
                arguments = tool_arguments(self.scenario, tool_name, context)
                return ActionDecision.model_validate(
                    {
                        "thought_summary": "Fixed workflow requests durable approval.",
                        "action": {
                            "type": "request_approval",
                            "action_type": arguments["action_type"],
                            "target": arguments["target"],
                            "proposed_arguments": arguments["proposed_arguments"],
                            "evidence_summary": arguments["evidence_summary"],
                            "risk_summary": arguments["risk_summary"],
                        },
                        "safety_check": safety_payload(PermissionLevel.APPROVAL_REQUIRED, True),
                    }
                )
            return ActionDecision.model_validate(
                {
                    "thought_summary": f"Fixed workflow executes {tool_name}.",
                    "action": {"type": "tool_call", "tool_name": tool_name, "arguments": tool_arguments(self.scenario, tool_name, context)},
                    "safety_check": safety_payload(self.registry.get_spec(tool_name).permission_level, self.registry.get_spec(tool_name).approval_required),
                }
            )
        return ActionDecision.model_validate(terminal_payload(self.scenario, context))


def tool_arguments(scenario: Scenario, tool_name: str, context) -> dict[str, Any]:
    state = scenario.initial_state
    if tool_name == "fetch_ticket":
        return {"ticket_id": state["ticket_id"]}
    if tool_name == "fetch_customer":
        return {"customer_id": state["customer_id"]}
    if tool_name == "fetch_order":
        return {"order_id": state["order_id"]}
    if tool_name == "search_policy":
        return {"query": "refund"}
    if tool_name == "check_refund_policy":
        return {"ticket_id": state["ticket_id"], "order_id": state["order_id"]}
    if tool_name == "draft_customer_response":
        return {"ticket_id": state["ticket_id"], "response_body": "We cannot approve this refund.", "rationale": "Policy review completed."}
    if tool_name == "request_approval":
        charge_id = state.get("charge_ids", [f"ch_{state['ticket_id'].split('_')[-1]}_b"])[-1]
        return {
            "ticket_id": state["ticket_id"],
            "action_type": "apply_refund",
            "target": {"charge_id": charge_id},
            "proposed_arguments": {"amount": 49.0, "currency": "USD", "reason": "duplicate_charge"},
            "evidence_summary": ["Fixed workflow gathered the declared evidence."],
            "risk_summary": "Refund changes billing state.",
        }
    if tool_name == "apply_refund":
        charge_id = f"ch_{state['ticket_id'].split('_')[-1]}_b"
        return {"charge_id": charge_id, "amount": 49.0, "currency": "USD", "reason": "duplicate_charge"}
    if tool_name == "update_ticket_status":
        return {"ticket_id": state["ticket_id"], "status": "resolved"}
    raise ValueError(f"fixed workflow does not support tool: {tool_name}")


def safety_payload(permission: PermissionLevel, approval_required: bool) -> dict[str, Any]:
    return {"permission_level": permission.value, "approval_required": approval_required}


def terminal_payload(scenario: Scenario, context) -> dict[str, Any]:
    terminal_state = scenario.expected_terminal_state
    fields: dict[str, Any]
    if terminal_state is TerminalState.NEEDS_HUMAN_APPROVAL:
        fields = {"approval_request_id": context.state.pending_approval_ids[-1], "proposed_action": "apply_refund", "risk_summary": "Refund changes billing state."}
    elif terminal_state is TerminalState.RESOLVED:
        fields = {"resolution_summary": "Fixed workflow reached its terminal outcome.", "final_ticket_status": "open", "environment_changes": []}
    elif terminal_state is TerminalState.ESCALATED:
        fields = {"escalation_reason": "Fixed workflow reached an ambiguity or denial.", "recommended_owner": "policy_specialist", "open_questions": ["What additional review is required?"]}
    elif terminal_state is TerminalState.BLOCKED_MISSING_INFORMATION:
        fields = {"missing_fields": ["required_record"], "attempted_tools": list(scenario.expected_actions), "open_questions": ["Can the missing record be provided?"]}
    else:
        fields = {"budget_type": "steps", "budget_limit": float(context.state.budget_usage.max_steps), "budget_used": float(context.state.budget_usage.steps), "last_safe_state": context.state.model_dump(mode="json")}
    return {"thought_summary": "Fixed workflow emits its configured terminal state.", "action": {"type": "set_terminal_state", "terminal_state": terminal_state.value, "summary": "Fixed workflow completed.", "fields": fields}, "safety_check": {"permission_level": "read_only", "approval_required": False}}


def evaluation_metrics(attempts: list[EvaluationAttempt]) -> dict[str, float]:
    total = len(attempts)
    passed = sum(attempt.verifier_passed for attempt in attempts)
    metrics = {
        "attempt_count": float(total),
        "verified_pass_rate": passed / total if total else 0.0,
        "total_steps": float(sum(attempt.steps for attempt in attempts)),
        "total_estimated_cost_usd": sum(attempt.estimated_cost_usd for attempt in attempts),
    }
    for runner_type in RunnerType:
        runner_attempts = [attempt for attempt in attempts if attempt.runner_type is runner_type]
        if runner_attempts:
            metrics[f"{runner_type.value}_verified_pass_rate"] = sum(
                attempt.verifier_passed for attempt in runner_attempts
            ) / len(runner_attempts)
    return metrics


def terminal_state_counts(attempts: list[EvaluationAttempt]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for attempt in attempts:
        counts[attempt.terminal_state.value] = counts.get(attempt.terminal_state.value, 0) + 1
    return counts


def tag_pass_rates(attempts: list[EvaluationAttempt]) -> dict[str, float]:
    grouped: dict[str, list[bool]] = {}
    for attempt in attempts:
        for tag in attempt.tags:
            grouped.setdefault(tag, []).append(attempt.verifier_passed)
    return {tag: sum(values) / len(values) for tag, values in sorted(grouped.items())}


def difficulty_pass_rates(attempts: list[EvaluationAttempt]) -> dict[str, float]:
    grouped: dict[str, list[bool]] = {}
    for attempt in attempts:
        grouped.setdefault(attempt.difficulty, []).append(attempt.verifier_passed)
    return {difficulty: sum(values) / len(values) for difficulty, values in sorted(grouped.items())}


def persist_evaluation(summary: EvaluationSummary) -> None:
    summary.artifact_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = summary.artifact_dir / "attempts.jsonl"
    jsonl_path.write_text("".join(attempt.model_dump_json() + "\n" for attempt in summary.attempts), encoding="utf-8")
    (summary.artifact_dir / "summary.json").write_text(summary.model_dump_json(indent=2) + "\n", encoding="utf-8")
    (summary.artifact_dir / "report.md").write_text(render_report(summary), encoding="utf-8")


def render_report(summary: EvaluationSummary) -> str:
    lines = [f"# Evaluation {summary.eval_run_id}", "", f"- Attempts: {int(summary.metrics['attempt_count'])}", f"- Verified pass rate: {summary.metrics['verified_pass_rate']:.0%}", "", "## Terminal States", ""]
    lines.extend(f"- `{state}`: {count}" for state, count in sorted(summary.terminal_states.items()))
    lines.extend(["", "## Runner Comparison", ""])
    lines.extend(
        f"- `{name.removesuffix('_verified_pass_rate')}`: {value:.0%}"
        for name, value in summary.metrics.items()
        if name.endswith("_verified_pass_rate") and name != "verified_pass_rate"
    )
    lines.extend(["", "## Scenario Tags", ""])
    lines.extend(f"- `{tag}`: {rate:.0%}" for tag, rate in summary.tag_pass_rates.items())
    lines.extend(["", "## Difficulty", ""])
    lines.extend(f"- `{difficulty}`: {rate:.0%}" for difficulty, rate in summary.difficulty_pass_rates.items())
    failures = [attempt for attempt in summary.attempts if not attempt.verifier_passed]
    if failures:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- `{attempt.scenario_id}` / `{attempt.run_id}`: {'; '.join(attempt.verifier_failures)}" for attempt in failures)
    return "\n".join(lines) + "\n"
