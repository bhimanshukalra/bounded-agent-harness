from collections.abc import Callable, Iterable
from dataclasses import dataclass

from pydantic import ValidationError

from bounded_agent.domain import ErrorType, PermissionLevel
from bounded_agent.tools.execution import ToolExecutionContext, error_result
from bounded_agent.tools.models import ToolCall, ToolResult, ToolSpec
from bounded_agent.tools.read_tools import fetch_customer, fetch_order, fetch_ticket, search_policy
from bounded_agent.tools.schemas import (
    AddTicketCommentInput,
    AddTicketCommentOutput,
    ApplyRefundInput,
    ApplyRefundOutput,
    CheckRefundPolicyInput,
    CheckRefundPolicyOutput,
    DraftCustomerResponseInput,
    DraftCustomerResponseOutput,
    FetchCustomerInput,
    FetchCustomerOutput,
    FetchOrderInput,
    FetchOrderOutput,
    FetchTicketInput,
    FetchTicketOutput,
    RequestApprovalInput,
    RequestApprovalOutput,
    SearchPolicyInput,
    SearchPolicyOutput,
    StrictToolSchema,
    UpdateTicketStatusInput,
    UpdateTicketStatusOutput,
    validate_tool_schema,
    validation_error_details,
)

ToolExecutor = Callable[[ToolExecutionContext, StrictToolSchema], ToolResult]


@dataclass(frozen=True)
class RegisteredTool:
    spec: ToolSpec
    input_schema: type[StrictToolSchema]
    output_schema: type[StrictToolSchema]
    executor: ToolExecutor | None = None


class ToolRegistry:
    def __init__(self, tools: Iterable[RegisteredTool]) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        for tool in tools:
            name = tool.spec.name
            if name in self._tools:
                raise ValueError(f"duplicate tool registration: {name}")
            self._tools[name] = tool

    def allowed_tool_names(self) -> set[str]:
        return set(self._tools)

    def list_specs(self) -> list[ToolSpec]:
        return [tool.spec for tool in sorted(self._tools.values(), key=lambda item: item.spec.name)]

    def list_specs_by_permission(self, permission_level: PermissionLevel) -> list[ToolSpec]:
        return [spec for spec in self.list_specs() if spec.permission_level is permission_level]

    def get_tool(self, tool_name: str) -> RegisteredTool:
        try:
            return self._tools[tool_name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {tool_name}") from exc

    def get_spec(self, tool_name: str) -> ToolSpec:
        return self.get_tool(tool_name).spec

    def validate_call(self, call: ToolCall) -> StrictToolSchema | ToolResult:
        tool = self._tools.get(call.tool_name)
        if tool is None:
            return unknown_tool_result(call.tool_name)

        try:
            return validate_tool_schema(tool.input_schema, call.arguments)
        except ValidationError as exc:
            return schema_validation_result("Tool input failed validation.", exc)

    def execute(self, call: ToolCall, context: ToolExecutionContext) -> ToolResult:
        tool = self._tools.get(call.tool_name)
        if tool is None:
            return unknown_tool_result(call.tool_name)
        if call.run_id is not None and call.run_id != context.run_id:
            return error_result(
                ErrorType.VALIDATION_ERROR,
                "Tool call run_id does not match execution context.",
                details={"tool_call_run_id": call.run_id, "context_run_id": context.run_id},
            )
        if tool.executor is None:
            return error_result(
                ErrorType.UNRECOVERABLE,
                "Tool is registered but has no executor.",
                details={"tool_name": call.tool_name},
            )

        parsed_input = self.validate_call(call)
        if isinstance(parsed_input, ToolResult):
            return parsed_input

        raw_result = tool.executor(context, parsed_input)
        tool_result = ToolResult.model_validate(raw_result)
        if not tool_result.ok:
            return tool_result

        try:
            validated_output = validate_tool_schema(tool.output_schema, tool_result.result or {})
        except ValidationError as exc:
            return schema_validation_result("Tool output failed validation.", exc)

        return ToolResult(
            ok=True,
            result=validated_output.model_dump(),
            metadata=tool_result.metadata,
        )


def unknown_tool_result(tool_name: str) -> ToolResult:
    return error_result(
        ErrorType.VALIDATION_ERROR,
        "Unknown tool.",
        details={"tool_name": tool_name},
    )


def schema_validation_result(message: str, error: ValidationError) -> ToolResult:
    return error_result(
        ErrorType.VALIDATION_ERROR,
        message,
        details={"fields": validation_error_details(error)},
    )


def build_default_registry() -> ToolRegistry:
    return ToolRegistry(DEFAULT_REGISTERED_TOOLS)


def registered_tool(
    spec: ToolSpec,
    input_schema: type[StrictToolSchema],
    output_schema: type[StrictToolSchema],
    executor: ToolExecutor | None = None,
) -> RegisteredTool:
    if spec.input_schema != input_schema.__name__:
        raise ValueError(f"input schema mismatch for {spec.name}")
    if spec.output_schema != output_schema.__name__:
        raise ValueError(f"output schema mismatch for {spec.name}")
    return RegisteredTool(
        spec=spec,
        input_schema=input_schema,
        output_schema=output_schema,
        executor=executor,
    )


DEFAULT_TOOL_SPECS = {
    "add_ticket_comment": ToolSpec(
        name="add_ticket_comment",
        description="Add an internal note to a support ticket.",
        input_schema="AddTicketCommentInput",
        output_schema="AddTicketCommentOutput",
        permission_level=PermissionLevel.LOW_RISK_WRITE,
        mutates_state=True,
        approval_required=False,
        idempotency_required=True,
        idempotency_key_rule="run:ticket:comment",
        error_types=[ErrorType.NOT_FOUND, ErrorType.VALIDATION_ERROR, ErrorType.CONFLICT],
    ),
    "apply_refund": ToolSpec(
        name="apply_refund",
        description="Apply an approved mock refund to a charge.",
        input_schema="ApplyRefundInput",
        output_schema="ApplyRefundOutput",
        permission_level=PermissionLevel.APPROVAL_REQUIRED,
        mutates_state=True,
        approval_required=True,
        idempotency_required=True,
        idempotency_key_rule="run:approval:charge:refund",
        error_types=[
            ErrorType.NOT_FOUND,
            ErrorType.PERMISSION_DENIED,
            ErrorType.VALIDATION_ERROR,
            ErrorType.CONFLICT,
            ErrorType.TRANSIENT_ERROR,
        ],
    ),
    "check_refund_policy": ToolSpec(
        name="check_refund_policy",
        description="Check refund eligibility against deterministic support policy.",
        input_schema="CheckRefundPolicyInput",
        output_schema="CheckRefundPolicyOutput",
        permission_level=PermissionLevel.READ_ONLY,
        mutates_state=False,
        approval_required=False,
        idempotency_required=False,
        error_types=[ErrorType.NOT_FOUND, ErrorType.VALIDATION_ERROR],
    ),
    "draft_customer_response": ToolSpec(
        name="draft_customer_response",
        description="Create a customer response draft without sending it.",
        input_schema="DraftCustomerResponseInput",
        output_schema="DraftCustomerResponseOutput",
        permission_level=PermissionLevel.DRAFT_ONLY,
        mutates_state=False,
        approval_required=False,
        idempotency_required=False,
        error_types=[ErrorType.VALIDATION_ERROR],
    ),
    "fetch_customer": ToolSpec(
        name="fetch_customer",
        description="Fetch scoped customer account facts.",
        input_schema="FetchCustomerInput",
        output_schema="FetchCustomerOutput",
        permission_level=PermissionLevel.READ_ONLY,
        mutates_state=False,
        approval_required=False,
        idempotency_required=False,
        error_types=[ErrorType.NOT_FOUND, ErrorType.VALIDATION_ERROR, ErrorType.TIMEOUT],
    ),
    "fetch_order": ToolSpec(
        name="fetch_order",
        description="Fetch order facts and linked charge records.",
        input_schema="FetchOrderInput",
        output_schema="FetchOrderOutput",
        permission_level=PermissionLevel.READ_ONLY,
        mutates_state=False,
        approval_required=False,
        idempotency_required=False,
        error_types=[ErrorType.NOT_FOUND, ErrorType.VALIDATION_ERROR, ErrorType.TIMEOUT],
    ),
    "fetch_ticket": ToolSpec(
        name="fetch_ticket",
        description="Fetch scoped ticket metadata, status, and body.",
        input_schema="FetchTicketInput",
        output_schema="FetchTicketOutput",
        permission_level=PermissionLevel.READ_ONLY,
        mutates_state=False,
        approval_required=False,
        idempotency_required=False,
        error_types=[ErrorType.NOT_FOUND, ErrorType.VALIDATION_ERROR, ErrorType.TIMEOUT],
    ),
    "request_approval": ToolSpec(
        name="request_approval",
        description="Create a durable approval request for a consequential action.",
        input_schema="RequestApprovalInput",
        output_schema="RequestApprovalOutput",
        permission_level=PermissionLevel.APPROVAL_REQUIRED,
        mutates_state=True,
        approval_required=True,
        idempotency_required=True,
        idempotency_key_rule="run:ticket:approval:action",
        error_types=[ErrorType.NOT_FOUND, ErrorType.PERMISSION_DENIED, ErrorType.VALIDATION_ERROR],
    ),
    "search_policy": ToolSpec(
        name="search_policy",
        description="Search scoped support policy content.",
        input_schema="SearchPolicyInput",
        output_schema="SearchPolicyOutput",
        permission_level=PermissionLevel.READ_ONLY,
        mutates_state=False,
        approval_required=False,
        idempotency_required=False,
        error_types=[ErrorType.NOT_FOUND, ErrorType.VALIDATION_ERROR, ErrorType.TIMEOUT],
    ),
    "update_ticket_status": ToolSpec(
        name="update_ticket_status",
        description="Update a support ticket status after required approval.",
        input_schema="UpdateTicketStatusInput",
        output_schema="UpdateTicketStatusOutput",
        permission_level=PermissionLevel.APPROVAL_REQUIRED,
        mutates_state=True,
        approval_required=True,
        idempotency_required=True,
        idempotency_key_rule="run:approval:ticket:status",
        error_types=[ErrorType.NOT_FOUND, ErrorType.PERMISSION_DENIED, ErrorType.VALIDATION_ERROR],
    ),
}

DEFAULT_REGISTERED_TOOLS = [
    registered_tool(
        DEFAULT_TOOL_SPECS["add_ticket_comment"],
        AddTicketCommentInput,
        AddTicketCommentOutput,
    ),
    registered_tool(
        DEFAULT_TOOL_SPECS["apply_refund"],
        ApplyRefundInput,
        ApplyRefundOutput,
    ),
    registered_tool(
        DEFAULT_TOOL_SPECS["check_refund_policy"],
        CheckRefundPolicyInput,
        CheckRefundPolicyOutput,
    ),
    registered_tool(
        DEFAULT_TOOL_SPECS["draft_customer_response"],
        DraftCustomerResponseInput,
        DraftCustomerResponseOutput,
    ),
    registered_tool(
        DEFAULT_TOOL_SPECS["fetch_customer"],
        FetchCustomerInput,
        FetchCustomerOutput,
        executor=fetch_customer,
    ),
    registered_tool(
        DEFAULT_TOOL_SPECS["fetch_order"],
        FetchOrderInput,
        FetchOrderOutput,
        executor=fetch_order,
    ),
    registered_tool(
        DEFAULT_TOOL_SPECS["fetch_ticket"],
        FetchTicketInput,
        FetchTicketOutput,
        executor=fetch_ticket,
    ),
    registered_tool(
        DEFAULT_TOOL_SPECS["request_approval"],
        RequestApprovalInput,
        RequestApprovalOutput,
    ),
    registered_tool(
        DEFAULT_TOOL_SPECS["search_policy"],
        SearchPolicyInput,
        SearchPolicyOutput,
        executor=search_policy,
    ),
    registered_tool(
        DEFAULT_TOOL_SPECS["update_ticket_status"],
        UpdateTicketStatusInput,
        UpdateTicketStatusOutput,
    ),
]
