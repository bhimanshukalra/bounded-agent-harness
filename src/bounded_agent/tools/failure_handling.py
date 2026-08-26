from typing import Any

from bounded_agent.domain import ErrorType
from bounded_agent.tools.execution import error_result
from bounded_agent.tools.models import ToolResult


def injected_failure_result(failure: dict[str, Any]) -> ToolResult:
    injected_failure_type = failure["failure_type"]
    failure_type = (
        ErrorType.TRANSIENT_ERROR
        if injected_failure_type == "transient_error_after_side_effect"
        else ErrorType(injected_failure_type)
    )
    retryable = failure_type in {
        ErrorType.TIMEOUT,
        ErrorType.TRANSIENT_ERROR,
    }
    return error_result(
        failure_type,
        failure["payload"].get("message", f"Injected {failure_type.value} failure."),
        retryable=retryable,
        details={
            "failure_id": failure["failure_id"],
            "failure_type": injected_failure_type,
            "tool_name": failure["tool_name"],
            "remaining_count": failure["remaining_count"],
            "target": failure["target"],
        },
        metadata={"source": "injected_failure"},
    )
