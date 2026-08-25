from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bounded_agent.domain.enums import (
    ApprovalStatus,
    ErrorType,
    RunnerType,
    ScenarioDifficulty,
    ScenarioTag,
    TerminalState,
)


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Task(StrictBaseModel):
    task_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    ticket_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Scenario(StrictBaseModel):
    id: str = Field(min_length=1)
    task: str = Field(min_length=1)
    initial_state: dict[str, Any] = Field(default_factory=dict)
    expected_terminal_state: TerminalState
    expected_actions: list[str] = Field(min_length=1)
    forbidden_actions: list[str] = Field(default_factory=list)
    injected_failures: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[ScenarioTag] = Field(min_length=1)
    difficulty: ScenarioDifficulty
    grading_rubric: str = Field(min_length=1)


class BudgetUsage(StrictBaseModel):
    steps: int = Field(default=0, ge=0)
    max_steps: int = Field(default=12, ge=1)
    estimated_tokens: int = Field(default=0, ge=0)
    token_budget: int | None = Field(default=None, ge=1)
    estimated_cost_usd: float = Field(default=0.0, ge=0)
    cost_budget_usd: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def steps_must_not_exceed_max_steps(self) -> "BudgetUsage":
        if self.steps > self.max_steps:
            raise ValueError("steps cannot exceed max_steps")
        return self


class RunError(StrictBaseModel):
    type: ErrorType
    message: str = Field(min_length=1)
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequest(StrictBaseModel):
    approval_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    scenario_id: str | None = None
    ticket_id: str = Field(min_length=1)
    action_type: str = Field(min_length=1)
    target: dict[str, Any] = Field(default_factory=dict)
    proposed_arguments: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: list[str] = Field(min_length=1)
    risk_summary: str = Field(min_length=1)
    status: ApprovalStatus = ApprovalStatus.PENDING
    decision: str | None = None


class AgentState(StrictBaseModel):
    task_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    current_status: str = Field(default="created", min_length=1)
    scenario_id: str | None = None
    known_facts: dict[str, Any] = Field(default_factory=dict)
    completed_actions: list[str] = Field(default_factory=list)
    pending_approval_ids: list[str] = Field(default_factory=list)
    tool_call_history: list[dict[str, Any]] = Field(default_factory=list)
    retries_by_failure_type: dict[ErrorType, int] = Field(default_factory=dict)
    budget_usage: BudgetUsage = Field(default_factory=BudgetUsage)
    terminal_state: TerminalState | None = None


class TerminalResult(StrictBaseModel):
    run_id: str = Field(min_length=1)
    scenario_id: str | None = None
    ticket_id: str = Field(min_length=1)
    terminal_state: TerminalState
    summary: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)
    errors: list[RunError] = Field(default_factory=list)
    budget_usage: BudgetUsage
    trace_path: Path

    resolution_summary: str | None = None
    final_ticket_status: str | None = None
    environment_changes: list[dict[str, Any]] | None = None
    approval_request_id: str | None = None
    proposed_action: str | None = None
    risk_summary: str | None = None
    escalation_reason: str | None = None
    recommended_owner: str | None = None
    open_questions: list[str] | None = None
    missing_fields: list[str] | None = None
    attempted_tools: list[str] | None = None
    failed_tool: str | None = None
    error_type: ErrorType | None = None
    retry_count: int | None = Field(default=None, ge=0)
    last_error: RunError | None = None
    budget_type: str | None = None
    budget_limit: float | None = None
    budget_used: float | None = None
    last_safe_state: dict[str, Any] | None = None
    violation_type: str | None = None
    attempted_action: str | None = None
    policy_reference: str | None = None
    trace_event_id: str | None = None
    tool_name: str | None = None
    validation_errors: list[str] | None = None
    error_summary: str | None = None
    last_successful_step: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_state_specific_fields(self) -> "TerminalResult":
        required_fields = {
            TerminalState.RESOLVED: (
                "resolution_summary",
                "final_ticket_status",
                "environment_changes",
            ),
            TerminalState.NEEDS_HUMAN_APPROVAL: (
                "approval_request_id",
                "proposed_action",
                "risk_summary",
            ),
            TerminalState.ESCALATED: (
                "escalation_reason",
                "recommended_owner",
                "open_questions",
            ),
            TerminalState.BLOCKED_MISSING_INFORMATION: (
                "missing_fields",
                "attempted_tools",
                "open_questions",
            ),
            TerminalState.BLOCKED_TOOL_ERROR: (
                "failed_tool",
                "error_type",
                "retry_count",
                "last_error",
            ),
            TerminalState.FAILED_BUDGET_EXCEEDED: (
                "budget_type",
                "budget_limit",
                "budget_used",
                "last_safe_state",
            ),
            TerminalState.FAILED_POLICY_VIOLATION: (
                "violation_type",
                "attempted_action",
                "policy_reference",
                "trace_event_id",
            ),
            TerminalState.FAILED_INVALID_TOOL_CALL: (
                "tool_name",
                "validation_errors",
                "retry_count",
            ),
            TerminalState.FAILED_UNRECOVERABLE: (
                "error_summary",
                "last_successful_step",
                "trace_event_id",
            ),
        }

        missing = [
            field_name
            for field_name in required_fields[self.terminal_state]
            if getattr(self, field_name) is None
        ]
        if missing:
            missing_text = ", ".join(missing)
            raise ValueError(f"{self.terminal_state} requires fields: {missing_text}")
        return self


class TraceEvent(StrictBaseModel):
    run_id: str = Field(min_length=1)
    scenario_id: str | None = None
    step: int = Field(ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    error: RunError | None = None
    latency_ms: float | None = Field(default=None, ge=0)
    token_usage: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)


class VerifierResult(StrictBaseModel):
    scenario_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    passed: bool
    checks: dict[str, bool] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EvalRun(StrictBaseModel):
    eval_run_id: str = Field(min_length=1)
    runner_type: RunnerType
    scenario_results: list[VerifierResult] = Field(default_factory=list)
    result_paths: list[Path] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    model_name: str | None = None
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None

    @model_validator(mode="after")
    def must_reference_results(self) -> "EvalRun":
        if not self.scenario_results and not self.result_paths:
            raise ValueError("EvalRun must include scenario_results or result_paths")
        return self
