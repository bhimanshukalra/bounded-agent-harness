from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from bounded_agent.domain.enums import ActionType, ErrorType, PermissionLevel, TerminalState


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SafetyCheck(StrictBaseModel):
    permission_level: PermissionLevel
    approval_required: bool
    untrusted_content_used: bool = False


class ToolCallAction(StrictBaseModel):
    type: Literal[ActionType.TOOL_CALL] = ActionType.TOOL_CALL
    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequestAction(StrictBaseModel):
    type: Literal[ActionType.REQUEST_APPROVAL] = ActionType.REQUEST_APPROVAL
    action_type: str = Field(min_length=1)
    target: dict[str, Any] = Field(default_factory=dict)
    proposed_arguments: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: list[str] = Field(min_length=1)
    risk_summary: str = Field(min_length=1)


class TerminalStateAction(StrictBaseModel):
    type: Literal[ActionType.SET_TERMINAL_STATE] = ActionType.SET_TERMINAL_STATE
    terminal_state: TerminalState
    summary: str = Field(min_length=1)
    fields: dict[str, Any] = Field(default_factory=dict)


class RetryAction(StrictBaseModel):
    type: Literal[ActionType.RETRY] = ActionType.RETRY
    failed_tool: str = Field(min_length=1)
    error_type: ErrorType
    corrected_arguments: dict[str, Any] | None = None
    retry_reason: str | None = None


class ReplanAction(StrictBaseModel):
    type: Literal[ActionType.REPLAN] = ActionType.REPLAN
    reason: str = Field(min_length=1)
    known_facts: dict[str, Any] = Field(default_factory=dict)
    next_goal: str = Field(min_length=1)


AgentAction = Annotated[
    ToolCallAction | ApprovalRequestAction | TerminalStateAction | RetryAction | ReplanAction,
    Field(discriminator="type"),
]


class ActionDecision(StrictBaseModel):
    thought_summary: str = Field(min_length=1, max_length=500)
    action: AgentAction
    safety_check: SafetyCheck
    stop_reason: str | None = None
