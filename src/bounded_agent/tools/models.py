from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bounded_agent.domain.enums import ErrorType, PermissionLevel


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolSpec(StrictBaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    input_schema: str = Field(min_length=1)
    output_schema: str = Field(min_length=1)
    permission_level: PermissionLevel
    mutates_state: bool
    approval_required: bool
    idempotency_required: bool
    idempotency_key_rule: str | None = None
    error_types: list[ErrorType] = Field(min_length=1)
    examples: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_permission_contract(self) -> "ToolSpec":
        if self.permission_level is PermissionLevel.APPROVAL_REQUIRED and not self.approval_required:
            raise ValueError("approval_required permission must set approval_required=true")
        if self.permission_level is PermissionLevel.FORBIDDEN:
            raise ValueError("forbidden tools must not be registered")
        if self.mutates_state and not self.idempotency_key_rule:
            raise ValueError("mutating tools must define idempotency_key_rule")
        if self.idempotency_key_rule and not self.idempotency_required:
            raise ValueError("idempotency_key_rule requires idempotency_required=true")
        return self


class ToolCall(StrictBaseModel):
    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    run_id: str | None = None
    approval_id: str | None = None
    idempotency_key: str | None = None


class ToolError(StrictBaseModel):
    type: ErrorType
    message: str = Field(min_length=1)
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ToolResult(StrictBaseModel):
    ok: bool
    result: dict[str, Any] | None = None
    error: ToolError | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def enforce_success_error_exclusivity(self) -> "ToolResult":
        if self.ok and self.error is not None:
            raise ValueError("successful tool results cannot include error")
        if self.ok and self.result is None:
            raise ValueError("successful tool results must include result")
        if not self.ok and self.error is None:
            raise ValueError("failed tool results must include error")
        if not self.ok and self.result is not None:
            raise ValueError("failed tool results cannot include result")
        return self


class Observation(StrictBaseModel):
    tool_name: str = Field(min_length=1)
    tool_result: ToolResult
    summary: str = Field(min_length=1)
    facts: dict[str, Any] = Field(default_factory=dict)
    raw_result_ref: str | None = None
