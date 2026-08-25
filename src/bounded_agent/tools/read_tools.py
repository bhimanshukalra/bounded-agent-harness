from typing import Any

from bounded_agent.domain import ErrorType
from bounded_agent.state import (
    consume_injected_failure,
    get_charges_for_order,
    get_customer,
    get_order,
    get_ticket,
    search_policies,
)
from bounded_agent.tools.execution import (
    ToolExecutionContext,
    error_result,
    success_result,
    tool_connection,
)
from bounded_agent.tools.models import ToolResult
from bounded_agent.tools.schemas import (
    FetchCustomerInput,
    FetchOrderInput,
    FetchTicketInput,
    SearchPolicyInput,
    StrictToolSchema,
)


def fetch_ticket(context: ToolExecutionContext, tool_input: StrictToolSchema) -> ToolResult:
    typed_input = expect_input(tool_input, FetchTicketInput)
    with tool_connection(context) as connection:
        failure = consume_read_failure(
            connection,
            context,
            "fetch_ticket",
            {"ticket_id": typed_input.ticket_id},
        )
        if failure is not None:
            return failure

        ticket = get_ticket(connection, typed_input.ticket_id)
        if ticket is None:
            return not_found_result("Ticket was not found.", "ticket_id", typed_input.ticket_id)

    return success_result({"ticket": ticket}, metadata={"source": "mock_support_environment"})


def fetch_customer(context: ToolExecutionContext, tool_input: StrictToolSchema) -> ToolResult:
    typed_input = expect_input(tool_input, FetchCustomerInput)
    with tool_connection(context) as connection:
        failure = consume_read_failure(
            connection,
            context,
            "fetch_customer",
            {"customer_id": typed_input.customer_id},
        )
        if failure is not None:
            return failure

        customer = get_customer(connection, typed_input.customer_id)
        if customer is None:
            return not_found_result("Customer was not found.", "customer_id", typed_input.customer_id)

    return success_result({"customer": customer}, metadata={"source": "mock_support_environment"})


def fetch_order(context: ToolExecutionContext, tool_input: StrictToolSchema) -> ToolResult:
    typed_input = expect_input(tool_input, FetchOrderInput)
    with tool_connection(context) as connection:
        failure = consume_read_failure(
            connection,
            context,
            "fetch_order",
            {"order_id": typed_input.order_id},
        )
        if failure is not None:
            return failure

        order = get_order(connection, typed_input.order_id)
        if order is None:
            return not_found_result("Order was not found.", "order_id", typed_input.order_id)

        charges = get_charges_for_order(connection, typed_input.order_id)

    return success_result(
        {"order": order, "charges": charges},
        metadata={"source": "mock_support_environment"},
    )


def search_policy(context: ToolExecutionContext, tool_input: StrictToolSchema) -> ToolResult:
    typed_input = expect_input(tool_input, SearchPolicyInput)
    with tool_connection(context) as connection:
        failure = consume_read_failure(
            connection,
            context,
            "search_policy",
            {"query": typed_input.query},
        )
        if failure is not None:
            return failure

        policies = search_policies(connection, typed_input.query)

    return success_result(
        {"policies": policies},
        metadata={"source": "mock_support_environment"},
    )


def consume_read_failure(
    connection,
    context: ToolExecutionContext,
    tool_name: str,
    target: dict[str, Any],
) -> ToolResult | None:
    if context.scenario_id is None:
        return None

    failure = consume_injected_failure(
        connection,
        scenario_id=context.scenario_id,
        tool_name=tool_name,
        target=target,
    )
    if failure is None:
        return None

    return injected_failure_result(failure)


def injected_failure_result(failure: dict[str, Any]) -> ToolResult:
    failure_type = ErrorType(failure["failure_type"])
    retryable = failure_type in {ErrorType.TIMEOUT, ErrorType.TRANSIENT_ERROR}
    return error_result(
        failure_type,
        failure["payload"].get("message", f"Injected {failure_type.value} failure."),
        retryable=retryable,
        details={
            "failure_id": failure["failure_id"],
            "tool_name": failure["tool_name"],
            "remaining_count": failure["remaining_count"],
            "target": failure["target"],
        },
        metadata={"source": "injected_failure"},
    )


def not_found_result(message: str, field_name: str, field_value: str) -> ToolResult:
    return error_result(
        ErrorType.NOT_FOUND,
        message,
        details={field_name: field_value},
        metadata={"source": "mock_support_environment"},
    )


def expect_input[SchemaT: StrictToolSchema](
    tool_input: StrictToolSchema,
    schema_type: type[SchemaT],
) -> SchemaT:
    if not isinstance(tool_input, schema_type):
        raise TypeError(f"expected {schema_type.__name__}, got {type(tool_input).__name__}")
    return tool_input
