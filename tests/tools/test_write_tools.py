import sqlite3

from bounded_agent.config import Settings
from bounded_agent.domain import ErrorType
from bounded_agent.state import (
    connect_database,
    get_audit_events,
    get_idempotency_record,
    reset_scenario_environment,
)
from bounded_agent.tools import ToolCall, ToolExecutionContext, build_default_registry


def reset_connection(tmp_path) -> sqlite3.Connection:
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    result = reset_scenario_environment("support_001", "support_001_run", settings)
    return connect_database(result.db_path)


def count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    return connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def test_draft_customer_response_returns_draft_without_mutating_environment(tmp_path):
    connection = reset_connection(tmp_path)
    registry = build_default_registry()
    context = ToolExecutionContext(run_id="run_001", connection=connection)
    before_counts = {
        table_name: count_rows(connection, table_name)
        for table_name in ["audit_log", "ticket_comments", "idempotency_keys"]
    }

    result = registry.execute(
        ToolCall(
            tool_name="draft_customer_response",
            arguments={
                "ticket_id": "t_001",
                "response_body": "We found a duplicate charge and will request approval.",
                "rationale": "Duplicate charges are eligible for approval review.",
            },
        ),
        context,
    )
    after_counts = {
        table_name: count_rows(connection, table_name)
        for table_name in ["audit_log", "ticket_comments", "idempotency_keys"]
    }

    assert result.ok is True
    assert result.result == {
        "ticket_id": "t_001",
        "draft_body": "We found a duplicate charge and will request approval.",
        "rationale": "Duplicate charges are eligible for approval review.",
        "sent": False,
    }
    assert result.metadata == {"source": "draft_only_tool"}
    assert after_counts == before_counts


def test_draft_customer_response_returns_not_found_for_missing_ticket(tmp_path):
    connection = reset_connection(tmp_path)
    registry = build_default_registry()
    context = ToolExecutionContext(run_id="run_001", connection=connection)

    result = registry.execute(
        ToolCall(
            tool_name="draft_customer_response",
            arguments={
                "ticket_id": "t_missing",
                "response_body": "Draft.",
                "rationale": "Missing ticket test.",
            },
        ),
        context,
    )

    assert result.ok is False
    assert result.error.type is ErrorType.NOT_FOUND
    assert result.error.details == {"ticket_id": "t_missing"}


def test_add_ticket_comment_requires_idempotency_key(tmp_path):
    connection = reset_connection(tmp_path)
    registry = build_default_registry()
    context = ToolExecutionContext(run_id="run_001", connection=connection)

    result = registry.execute(
        ToolCall(
            tool_name="add_ticket_comment",
            arguments={"ticket_id": "t_001", "body": "Verified duplicate charges."},
        ),
        context,
    )

    assert result.ok is False
    assert result.error.type is ErrorType.VALIDATION_ERROR
    assert result.error.details == {"tool_name": "add_ticket_comment"}


def test_add_ticket_comment_writes_comment_audit_and_idempotency_record(tmp_path):
    connection = reset_connection(tmp_path)
    registry = build_default_registry()
    context = ToolExecutionContext(
        run_id="run_001",
        scenario_id="support_001",
        connection=connection,
        actor="agent",
        idempotency_key="comment:key:001",
    )

    result = registry.execute(
        ToolCall(
            tool_name="add_ticket_comment",
            arguments={"ticket_id": "t_001", "body": "Verified duplicate charges."},
        ),
        context,
    )
    saved_comment = connection.execute(
        """
        SELECT comment_id, ticket_id, body, visibility, idempotency_key
        FROM ticket_comments
        """
    ).fetchone()
    audit_events = get_audit_events(connection, "t_001")
    idempotency_record = get_idempotency_record(connection, "comment:key:001")

    assert result.ok is True
    assert result.result["comment_id"] == saved_comment["comment_id"]
    assert result.result["visibility"] == "internal"
    assert dict(saved_comment) == {
        "comment_id": result.result["comment_id"],
        "ticket_id": "t_001",
        "body": "Verified duplicate charges.",
        "visibility": "internal",
        "idempotency_key": "comment:key:001",
    }
    assert audit_events[0]["action"] == "create_ticket_comment"
    assert audit_events[0]["idempotency_key"] == "comment:key:001"
    assert idempotency_record["result"] == result.result


def test_add_ticket_comment_replays_matching_retry_without_duplicate_side_effects(tmp_path):
    connection = reset_connection(tmp_path)
    registry = build_default_registry()
    context = ToolExecutionContext(
        run_id="run_001",
        connection=connection,
        idempotency_key="comment:key:001",
    )
    call = ToolCall(
        tool_name="add_ticket_comment",
        arguments={"ticket_id": "t_001", "body": "Verified duplicate charges."},
    )

    first = registry.execute(call, context)
    second = registry.execute(call, context)

    assert first.ok is True
    assert second.ok is True
    assert second.result == first.result
    assert second.metadata == {"source": "idempotency_replay"}
    assert count_rows(connection, "ticket_comments") == 1
    assert count_rows(connection, "audit_log") == 1
    assert count_rows(connection, "idempotency_keys") == 1


def test_add_ticket_comment_conflicts_when_key_is_reused_with_different_arguments(tmp_path):
    connection = reset_connection(tmp_path)
    registry = build_default_registry()
    context = ToolExecutionContext(
        run_id="run_001",
        connection=connection,
        idempotency_key="comment:key:001",
    )
    registry.execute(
        ToolCall(
            tool_name="add_ticket_comment",
            arguments={"ticket_id": "t_001", "body": "Verified duplicate charges."},
        ),
        context,
    )

    conflict = registry.execute(
        ToolCall(
            tool_name="add_ticket_comment",
            arguments={"ticket_id": "t_001", "body": "Changed comment body."},
        ),
        context,
    )

    assert conflict.ok is False
    assert conflict.error.type is ErrorType.CONFLICT
    assert conflict.error.details["idempotency_key"] == "comment:key:001"
    assert count_rows(connection, "ticket_comments") == 1
    assert count_rows(connection, "audit_log") == 1
    assert count_rows(connection, "idempotency_keys") == 1
