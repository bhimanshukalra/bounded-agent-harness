from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from bounded_agent.config import Settings, load_settings
from bounded_agent.domain import (
    AgentState,
    BudgetUsage,
    Scenario,
    Task,
    TerminalResult,
    TerminalState,
)
from bounded_agent.evals import load_scenario
from bounded_agent.loop.actions import ActionDecision, TerminalStateAction
from bounded_agent.state import ResetResult, reset_scenario_environment
from bounded_agent.tools import Observation, ToolRegistry, ToolSpec, build_default_registry


class DecisionSource(Protocol):
    def decide(self, context: "RunnerContext") -> ActionDecision:
        """Choose the next structured action for the current loop step."""


@dataclass(frozen=True)
class RunnerConfig:
    max_steps: int = 12
    max_retries_per_error_type: int = 2
    trace_path: Path = Path("data/runs/trace.jsonl")

    def __post_init__(self) -> None:
        if self.max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        if self.max_retries_per_error_type < 0:
            raise ValueError("max_retries_per_error_type cannot be negative")


@dataclass(frozen=True)
class RunnerRequest:
    run_id: str
    task: Task
    ticket_id: str
    scenario_id: str | None = None
    initial_state: AgentState | None = None

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id cannot be blank")
        if not self.ticket_id.strip():
            raise ValueError("ticket_id cannot be blank")


@dataclass(frozen=True)
class RunnerContext:
    request: RunnerRequest
    state: AgentState
    step: int
    observations: Sequence[Observation]
    available_tools: Sequence[ToolSpec]
    budget_usage: BudgetUsage
    scenario: Scenario | None = None
    db_path: Path | None = None


@dataclass(frozen=True)
class RunnerResult:
    terminal_result: TerminalResult
    state: AgentState
    observations: Sequence[Observation] = field(default_factory=tuple)
    scenario: Scenario | None = None
    db_path: Path | None = None


class AgentRunner:
    def __init__(
        self,
        decision_source: DecisionSource,
        *,
        registry: ToolRegistry | None = None,
        config: RunnerConfig | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.decision_source = decision_source
        self.registry = registry or build_default_registry()
        self.config = config or RunnerConfig()
        self.settings = settings or load_settings()

    def run_scenario(self, scenario_id: str, run_id: str) -> RunnerResult:
        scenario = load_scenario(scenario_id, self.settings)
        reset_result = reset_scenario_environment(scenario.id, run_id, self.settings)
        request = RunnerRequest(
            run_id=run_id,
            task=Task(task_id=scenario.id, goal=scenario.task),
            scenario_id=scenario.id,
            ticket_id=scenario_ticket_id(scenario),
        )
        return self.run(request, scenario=scenario, reset_result=reset_result)

    def run(
        self,
        request: RunnerRequest,
        *,
        scenario: Scenario | None = None,
        reset_result: ResetResult | None = None,
    ) -> RunnerResult:
        state = request.initial_state or AgentState(
            task_id=request.task.task_id,
            goal=request.task.goal,
            scenario_id=request.scenario_id,
            budget_usage=BudgetUsage(max_steps=self.config.max_steps),
        )
        observations: tuple[Observation, ...] = ()

        context = RunnerContext(
            request=request,
            state=state,
            step=state.budget_usage.steps,
            observations=observations,
            available_tools=tuple(self.registry.list_specs()),
            budget_usage=state.budget_usage,
            scenario=scenario,
            db_path=reset_result.db_path if reset_result is not None else None,
        )
        decision = self.decision_source.decide(context)

        if isinstance(decision.action, TerminalStateAction):
            terminal_result = self._terminal_result_from_action(request, state, decision.action)
        else:
            terminal_result = self._unsupported_action_result(request, state, decision)

        terminal_state = state.model_copy(update={"terminal_state": terminal_result.terminal_state})
        return RunnerResult(
            terminal_result=terminal_result,
            state=terminal_state,
            observations=observations,
            scenario=scenario,
            db_path=reset_result.db_path if reset_result is not None else None,
        )

    def _terminal_result_from_action(
        self,
        request: RunnerRequest,
        state: AgentState,
        action: TerminalStateAction,
    ) -> TerminalResult:
        return TerminalResult(
            run_id=request.run_id,
            scenario_id=request.scenario_id,
            ticket_id=request.ticket_id,
            terminal_state=action.terminal_state,
            summary=action.summary,
            actions_taken=state.completed_actions,
            budget_usage=state.budget_usage,
            trace_path=self.config.trace_path,
            **action.fields,
        )

    def _unsupported_action_result(
        self,
        request: RunnerRequest,
        state: AgentState,
        decision: ActionDecision,
    ) -> TerminalResult:
        return TerminalResult(
            run_id=request.run_id,
            scenario_id=request.scenario_id,
            ticket_id=request.ticket_id,
            terminal_state=TerminalState.FAILED_UNRECOVERABLE,
            summary="Runner control flow for this action is not implemented yet.",
            actions_taken=state.completed_actions,
            budget_usage=state.budget_usage,
            trace_path=self.config.trace_path,
            error_summary=f"Unsupported runner action for Milestone 5.1: {decision.action.type}",
            last_successful_step=state.budget_usage.steps,
            trace_event_id=f"trace_{uuid4().hex}",
        )


def scenario_ticket_id(scenario: Scenario) -> str:
    ticket_id = scenario.initial_state.get("ticket_id")
    if not isinstance(ticket_id, str) or not ticket_id.strip():
        raise ValueError(f"scenario does not define initial_state.ticket_id: {scenario.id}")
    return ticket_id
