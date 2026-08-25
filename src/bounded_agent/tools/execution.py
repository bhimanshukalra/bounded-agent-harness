import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bounded_agent.domain import ErrorType
from bounded_agent.state import connect_database
from bounded_agent.tools.models import ToolError, ToolResult


@dataclass(frozen=True)
class ToolExecutionContext:
    run_id: str
    db_path: Path | None = None
    connection: sqlite3.Connection | None = None
    scenario_id: str | None = None
    actor: str = "agent"
    approval_id: str | None = None
    idempotency_key: str | None = None

    # Validate that each tool call has one clear database access path.
    def __post_init__(self) -> None:
        has_db_path = self.db_path is not None
        has_connection = self.connection is not None
        if has_db_path == has_connection:
            raise ValueError("tool execution context requires exactly one of db_path or connection")
        if not self.run_id.strip():
            raise ValueError("run_id cannot be blank")
        if not self.actor.strip():
            raise ValueError("actor cannot be blank")


# Provide a SQLite connection while respecting caller-owned connections.
@contextmanager
def tool_connection(context: ToolExecutionContext) -> Iterator[sqlite3.Connection]:
    if context.connection is not None:
        yield context.connection
        return

    connection = connect_database(context.db_path)
    try:
        yield connection
    finally:
        connection.close()


# Build the standard successful tool result shape.
def success_result(
    result: dict[str, Any],
    *,
    metadata: dict[str, Any] | None = None,
) -> ToolResult:
    return ToolResult(ok=True, result=result, metadata=metadata or {})


# Build the standard expected-error tool result shape.
def error_result(
    error_type: ErrorType,
    message: str,
    *,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ToolResult:
    return ToolResult(
        ok=False,
        error=ToolError(
            type=error_type,
            message=message,
            retryable=retryable,
            details=details or {},
        ),
        metadata=metadata or {},
    )
