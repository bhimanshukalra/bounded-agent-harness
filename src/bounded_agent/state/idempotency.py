import hashlib
import sqlite3
from typing import Any, Literal

from bounded_agent.state.audit import current_timestamp
from bounded_agent.state.fixtures import json_dump
from bounded_agent.state.inspection import normalize_row

IdempotencyStatus = Literal["created", "replay", "conflict"]


def hash_arguments(arguments: dict[str, Any]) -> str:
    return hashlib.sha256(json_dump(arguments).encode("utf-8")).hexdigest()


def get_idempotency_record(
    connection: sqlite3.Connection,
    idempotency_key: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT *
        FROM idempotency_keys
        WHERE idempotency_key = ?
        """,
        (idempotency_key,),
    ).fetchone()
    if row is None:
        return None
    return normalize_row(row)


def record_or_replay_idempotency(
    connection: sqlite3.Connection,
    *,
    idempotency_key: str,
    run_id: str | None,
    tool_name: str,
    target_type: str,
    target_id: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
    created_at: str | None = None,
) -> dict[str, Any]:
    argument_hash = hash_arguments(arguments)
    existing = get_idempotency_record(connection, idempotency_key)
    if existing is not None:
        if existing["argument_hash"] == argument_hash:
            return {
                "status": "replay",
                "record": existing,
                "result": existing["result"],
            }
        return {
            "status": "conflict",
            "record": existing,
            "result": None,
            "conflict": {
                "idempotency_key": idempotency_key,
                "original_argument_hash": existing["argument_hash"],
                "new_argument_hash": argument_hash,
            },
        }

    timestamp = created_at or current_timestamp()
    record = {
        "idempotency_key": idempotency_key,
        "run_id": run_id,
        "tool_name": tool_name,
        "target_type": target_type,
        "target_id": target_id,
        "argument_hash": argument_hash,
        "result": result,
        "created_at": timestamp,
    }

    with connection:
        connection.execute(
            """
            INSERT INTO idempotency_keys (
                idempotency_key,
                run_id,
                tool_name,
                target_type,
                target_id,
                argument_hash,
                result_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                idempotency_key,
                run_id,
                tool_name,
                target_type,
                target_id,
                argument_hash,
                json_dump(result),
                timestamp,
            ),
        )

    return {
        "status": "created",
        "record": record,
        "result": result,
    }
