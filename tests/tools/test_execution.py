import sqlite3

import pytest

from bounded_agent.domain import ErrorType
from bounded_agent.state import initialize_schema, list_tables
from bounded_agent.tools import (
    ToolExecutionContext,
    error_result,
    success_result,
    tool_connection,
)


def test_tool_execution_context_accepts_database_path(tmp_path):
    context = ToolExecutionContext(
        run_id="run_001",
        db_path=tmp_path / "state.db",
        scenario_id="support_001",
        actor="agent",
        approval_id="approval_001",
        idempotency_key="key_001",
    )

    assert context.run_id == "run_001"
    assert context.db_path == tmp_path / "state.db"
    assert context.connection is None
    assert context.scenario_id == "support_001"


def test_tool_execution_context_accepts_connection():
    connection = sqlite3.connect(":memory:")

    context = ToolExecutionContext(run_id="run_001", connection=connection)

    assert context.connection is connection
    assert context.db_path is None


def test_tool_execution_context_requires_exactly_one_database_source(tmp_path):
    connection = sqlite3.connect(":memory:")

    with pytest.raises(ValueError, match="exactly one"):
        ToolExecutionContext(run_id="run_001")

    with pytest.raises(ValueError, match="exactly one"):
        ToolExecutionContext(
            run_id="run_001",
            db_path=tmp_path / "state.db",
            connection=connection,
        )


def test_tool_execution_context_rejects_blank_run_id_and_actor(tmp_path):
    with pytest.raises(ValueError, match="run_id"):
        ToolExecutionContext(run_id=" ", db_path=tmp_path / "state.db")

    with pytest.raises(ValueError, match="actor"):
        ToolExecutionContext(run_id="run_001", db_path=tmp_path / "state.db", actor=" ")


def test_tool_connection_opens_and_closes_path_connection(tmp_path):
    db_path = tmp_path / "state.db"
    context = ToolExecutionContext(run_id="run_001", db_path=db_path)

    with tool_connection(context) as connection:
        initialize_schema(connection)
        assert "tickets" in list_tables(connection)

    assert db_path.exists()
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        connection.execute("SELECT 1")


def test_tool_connection_reuses_supplied_connection():
    connection = sqlite3.connect(":memory:")
    context = ToolExecutionContext(run_id="run_001", connection=connection)

    with tool_connection(context) as active_connection:
        assert active_connection is connection

    connection.execute("SELECT 1")


def test_success_result_builds_valid_tool_result():
    result = success_result(
        {"ticket_id": "t_001"},
        metadata={"source": "tool_contract"},
    )

    assert result.ok is True
    assert result.result == {"ticket_id": "t_001"}
    assert result.error is None
    assert result.metadata == {"source": "tool_contract"}


def test_error_result_builds_valid_tool_result():
    result = error_result(
        ErrorType.TIMEOUT,
        "Order lookup timed out.",
        retryable=True,
        details={"tool_name": "fetch_order"},
        metadata={"source": "injected_failure"},
    )

    assert result.ok is False
    assert result.result is None
    assert result.error.type is ErrorType.TIMEOUT
    assert result.error.retryable is True
    assert result.error.details == {"tool_name": "fetch_order"}
    assert result.metadata == {"source": "injected_failure"}
