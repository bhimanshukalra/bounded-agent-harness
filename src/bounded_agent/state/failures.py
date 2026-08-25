import sqlite3
from typing import Any

from bounded_agent.state.fixtures import json_dump
from bounded_agent.state.inspection import normalize_row

SUPPORTED_FAILURE_TYPES = {
    "timeout",
    "transient_error",
    "transient_error_after_side_effect",
    "not_found",
    "permission_denied",
    "conflict",
}


def list_injected_failures(
    connection: sqlite3.Connection,
    *,
    scenario_id: str,
    tool_name: str | None = None,
) -> list[dict[str, Any]]:
    if tool_name is None:
        rows = connection.execute(
            """
            SELECT *
            FROM injected_failures
            WHERE scenario_id = ?
            ORDER BY failure_id
            """,
            (scenario_id,),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT *
            FROM injected_failures
            WHERE scenario_id = ? AND tool_name = ?
            ORDER BY failure_id
            """,
            (scenario_id, tool_name),
        ).fetchall()
    return [normalize_failure(row) for row in rows]


def consume_injected_failure(
    connection: sqlite3.Connection,
    *,
    scenario_id: str,
    tool_name: str,
    target: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    failure = next_matching_failure(
        connection,
        scenario_id=scenario_id,
        tool_name=tool_name,
        target=target,
    )
    if failure is None:
        return None

    with connection:
        connection.execute(
            """
            UPDATE injected_failures
            SET remaining_count = remaining_count - 1
            WHERE failure_id = ? AND remaining_count > 0
            """,
            (failure["failure_id"],),
        )

    failure["remaining_count"] -= 1
    return failure


def next_matching_failure(
    connection: sqlite3.Connection,
    *,
    scenario_id: str,
    tool_name: str,
    target: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    rows = connection.execute(
        """
        SELECT *
        FROM injected_failures
        WHERE scenario_id = ?
            AND tool_name = ?
            AND remaining_count > 0
        ORDER BY failure_id
        """,
        (scenario_id, tool_name),
    ).fetchall()

    for row in rows:
        failure = normalize_failure(row)
        if failure_matches_target(failure["target"], target):
            return failure
    return None


def failure_matches_target(
    configured_target: dict[str, Any],
    requested_target: dict[str, Any] | None,
) -> bool:
    if not configured_target:
        return True
    if requested_target is None:
        return False
    return configured_target == requested_target


def normalize_failure(row: sqlite3.Row) -> dict[str, Any]:
    failure = normalize_row(row)
    if failure["failure_type"] not in SUPPORTED_FAILURE_TYPES:
        raise ValueError(f"unsupported injected failure type: {failure['failure_type']}")
    return failure


def insert_injected_failure(
    connection: sqlite3.Connection,
    *,
    failure_id: str,
    scenario_id: str,
    tool_name: str,
    failure_type: str,
    remaining_count: int = 1,
    target: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if failure_type not in SUPPORTED_FAILURE_TYPES:
        raise ValueError(f"unsupported injected failure type: {failure_type}")
    if remaining_count < 0:
        raise ValueError("remaining_count cannot be negative")

    with connection:
        connection.execute(
            """
            INSERT INTO injected_failures (
                failure_id,
                scenario_id,
                tool_name,
                failure_type,
                remaining_count,
                target_json,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                failure_id,
                scenario_id,
                tool_name,
                failure_type,
                remaining_count,
                json_dump(target or {}),
                json_dump(payload or {}),
            ),
        )

    return {
        "failure_id": failure_id,
        "scenario_id": scenario_id,
        "tool_name": tool_name,
        "failure_type": failure_type,
        "remaining_count": remaining_count,
        "target": target or {},
        "payload": payload or {},
    }
