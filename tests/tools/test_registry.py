import sqlite3

import pytest

from bounded_agent.domain import ErrorType, PermissionLevel
from bounded_agent.tools import (
    DEFAULT_TOOL_SPECS,
    FetchTicketInput,
    FetchTicketOutput,
    RegisteredTool,
    ToolCall,
    ToolExecutionContext,
    ToolRegistry,
    ToolSpec,
    build_default_registry,
    registered_tool,
    success_result,
)


def test_default_registry_registers_all_planned_tools():
    registry = build_default_registry()

    assert registry.allowed_tool_names() == {
        "add_ticket_comment",
        "apply_refund",
        "check_refund_policy",
        "draft_customer_response",
        "fetch_customer",
        "fetch_order",
        "fetch_ticket",
        "request_approval",
        "search_policy",
        "update_ticket_status",
    }


def test_default_registry_fetches_tool_specs_by_name():
    registry = build_default_registry()

    spec = registry.get_spec("fetch_ticket")

    assert spec.name == "fetch_ticket"
    assert spec.input_schema == "FetchTicketInput"
    assert spec.output_schema == "FetchTicketOutput"
    assert spec.permission_level is PermissionLevel.READ_ONLY


def test_registry_lists_specs_by_permission():
    registry = build_default_registry()

    read_only_specs = registry.list_specs_by_permission(PermissionLevel.READ_ONLY)

    assert [spec.name for spec in read_only_specs] == [
        "check_refund_policy",
        "fetch_customer",
        "fetch_order",
        "fetch_ticket",
        "search_policy",
    ]


def test_registry_rejects_unknown_tool_names_before_execution():
    registry = build_default_registry()
    call = ToolCall(tool_name="run_shell", arguments={})
    context = ToolExecutionContext(run_id="run_001", connection=sqlite3.connect(":memory:"))

    result = registry.execute(call, context)

    assert result.ok is False
    assert result.error.type is ErrorType.VALIDATION_ERROR
    assert result.error.details == {"tool_name": "run_shell"}


def test_registry_validates_input_arguments_before_execution():
    registry = build_default_registry()
    call = ToolCall(tool_name="fetch_ticket", arguments={})

    parsed = registry.validate_call(call)

    assert parsed.ok is False
    assert parsed.error.type is ErrorType.VALIDATION_ERROR
    assert parsed.error.details == {"fields": ["ticket_id"]}


def test_default_registry_returns_error_for_registered_tool_without_executor():
    registry = build_default_registry()
    call = ToolCall(tool_name="fetch_ticket", arguments={"ticket_id": "t_001"})
    context = ToolExecutionContext(run_id="run_001", connection=sqlite3.connect(":memory:"))

    result = registry.execute(call, context)

    assert result.ok is False
    assert result.error.type is ErrorType.UNRECOVERABLE
    assert result.error.details == {"tool_name": "fetch_ticket"}


def test_registry_can_execute_registered_tool_with_valid_input_and_output():
    def fake_fetch_ticket(context, tool_input):
        assert context.run_id == "run_001"
        assert isinstance(tool_input, FetchTicketInput)
        return success_result(
            {"ticket": {"ticket_id": tool_input.ticket_id, "status": "open"}},
            metadata={"executor": "fake"},
        )

    registry = ToolRegistry(
        [
            registered_tool(
                DEFAULT_TOOL_SPECS["fetch_ticket"],
                FetchTicketInput,
                FetchTicketOutput,
                executor=fake_fetch_ticket,
            )
        ]
    )
    call = ToolCall(tool_name="fetch_ticket", arguments={"ticket_id": "t_001"})
    context = ToolExecutionContext(run_id="run_001", connection=sqlite3.connect(":memory:"))

    result = registry.execute(call, context)

    assert result.ok is True
    assert result.result == {"ticket": {"ticket_id": "t_001", "status": "open"}}
    assert result.metadata == {"executor": "fake"}


def test_registry_validates_executor_output():
    def fake_bad_fetch_ticket(_context, _tool_input):
        return success_result({"wrong": {"ticket_id": "t_001"}})

    registry = ToolRegistry(
        [
            registered_tool(
                DEFAULT_TOOL_SPECS["fetch_ticket"],
                FetchTicketInput,
                FetchTicketOutput,
                executor=fake_bad_fetch_ticket,
            )
        ]
    )
    call = ToolCall(tool_name="fetch_ticket", arguments={"ticket_id": "t_001"})
    context = ToolExecutionContext(run_id="run_001", connection=sqlite3.connect(":memory:"))

    result = registry.execute(call, context)

    assert result.ok is False
    assert result.error.type is ErrorType.VALIDATION_ERROR
    assert result.error.details == {"fields": ["ticket", "wrong"]}


def test_registry_rejects_call_context_run_id_mismatch():
    registry = build_default_registry()
    call = ToolCall(tool_name="fetch_ticket", arguments={"ticket_id": "t_001"}, run_id="run_other")
    context = ToolExecutionContext(run_id="run_001", connection=sqlite3.connect(":memory:"))

    result = registry.execute(call, context)

    assert result.ok is False
    assert result.error.type is ErrorType.VALIDATION_ERROR
    assert result.error.details == {
        "tool_call_run_id": "run_other",
        "context_run_id": "run_001",
    }


def test_registry_rejects_duplicate_registrations():
    tool = RegisteredTool(
        spec=DEFAULT_TOOL_SPECS["fetch_ticket"],
        input_schema=FetchTicketInput,
        output_schema=FetchTicketOutput,
    )

    with pytest.raises(ValueError, match="duplicate tool registration"):
        ToolRegistry([tool, tool])


def test_registered_tool_rejects_schema_name_mismatch():
    bad_spec = ToolSpec(
        name="fetch_ticket",
        description="Fetch ticket.",
        input_schema="WrongInput",
        output_schema="FetchTicketOutput",
        permission_level=PermissionLevel.READ_ONLY,
        mutates_state=False,
        approval_required=False,
        idempotency_required=False,
        error_types=[ErrorType.VALIDATION_ERROR],
    )

    with pytest.raises(ValueError, match="input schema mismatch"):
        registered_tool(bad_spec, FetchTicketInput, FetchTicketOutput)
