import hashlib

from bounded_agent.domain import ErrorType
from bounded_agent.state import (
    create_ticket_comment,
    get_idempotency_record,
    get_ticket,
    hash_arguments,
    record_or_replay_idempotency,
)
from bounded_agent.state.audit import current_timestamp
from bounded_agent.tools.execution import (
    ToolExecutionContext,
    error_result,
    success_result,
    tool_connection,
)
from bounded_agent.tools.models import ToolResult
from bounded_agent.tools.schemas import (
    AddTicketCommentInput,
    DraftCustomerResponseInput,
    StrictToolSchema,
)


def draft_customer_response(context: ToolExecutionContext, tool_input: StrictToolSchema) -> ToolResult:
    typed_input = expect_input(tool_input, DraftCustomerResponseInput)
    with tool_connection(context) as connection:
        ticket = get_ticket(connection, typed_input.ticket_id)
        if ticket is None:
            return not_found_result("Ticket was not found.", "ticket_id", typed_input.ticket_id)

    return success_result(
        {
            "ticket_id": typed_input.ticket_id,
            "draft_body": typed_input.response_body,
            "rationale": typed_input.rationale,
            "sent": False,
        },
        metadata={"source": "draft_only_tool"},
    )


def add_ticket_comment(context: ToolExecutionContext, tool_input: StrictToolSchema) -> ToolResult:
    typed_input = expect_input(tool_input, AddTicketCommentInput)
    if context.idempotency_key is None:
        return error_result(
            ErrorType.VALIDATION_ERROR,
            "Mutating tool requires an idempotency key.",
            details={"tool_name": "add_ticket_comment"},
        )

    arguments = typed_input.model_dump()
    with tool_connection(context) as connection:
        ticket = get_ticket(connection, typed_input.ticket_id)
        if ticket is None:
            return not_found_result("Ticket was not found.", "ticket_id", typed_input.ticket_id)

        existing_record = get_idempotency_record(connection, context.idempotency_key)
        if existing_record is not None:
            if existing_record["argument_hash"] == hash_arguments(arguments):
                return success_result(
                    existing_record["result"],
                    metadata={"source": "idempotency_replay"},
                )
            return error_result(
                ErrorType.CONFLICT,
                "Idempotency key was reused with different arguments.",
                details={
                    "idempotency_key": context.idempotency_key,
                    "original_argument_hash": existing_record["argument_hash"],
                    "new_argument_hash": hash_arguments(arguments),
                },
            )

        created_at = current_timestamp()
        comment_id = stable_id("comment", context.idempotency_key)
        comment = create_ticket_comment(
            connection,
            comment_id=comment_id,
            ticket_id=typed_input.ticket_id,
            run_id=context.run_id,
            scenario_id=context.scenario_id,
            author=context.actor,
            body=typed_input.body,
            created_at=created_at,
            idempotency_key=context.idempotency_key,
            actor=context.actor,
        )
        result = {
            "comment_id": comment["comment_id"],
            "ticket_id": comment["ticket_id"],
            "visibility": comment["visibility"],
            "created_at": comment["created_at"],
        }
        record_or_replay_idempotency(
            connection,
            idempotency_key=context.idempotency_key,
            run_id=context.run_id,
            tool_name="add_ticket_comment",
            target_type="ticket",
            target_id=typed_input.ticket_id,
            arguments=arguments,
            result=result,
            created_at=created_at,
        )

    return success_result(result, metadata={"source": "mock_support_environment"})


def stable_id(prefix: str, idempotency_key: str) -> str:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


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
