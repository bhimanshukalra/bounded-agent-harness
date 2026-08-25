import json
import sqlite3
from typing import Any


def get_ticket(connection: sqlite3.Connection, ticket_id: str) -> dict[str, Any] | None:
    return fetch_one(
        connection,
        """
        SELECT *
        FROM tickets
        WHERE ticket_id = ?
        """,
        (ticket_id,),
    )


def get_customer(connection: sqlite3.Connection, customer_id: str) -> dict[str, Any] | None:
    return fetch_one(
        connection,
        """
        SELECT *
        FROM customers
        WHERE customer_id = ?
        """,
        (customer_id,),
    )


def get_order(connection: sqlite3.Connection, order_id: str) -> dict[str, Any] | None:
    return fetch_one(
        connection,
        """
        SELECT *
        FROM orders
        WHERE order_id = ?
        """,
        (order_id,),
    )


def get_charges_for_order(
    connection: sqlite3.Connection,
    order_id: str,
) -> list[dict[str, Any]]:
    return fetch_all(
        connection,
        """
        SELECT *
        FROM charges
        WHERE order_id = ?
        ORDER BY charged_at, charge_id
        """,
        (order_id,),
    )


def search_policies(connection: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return fetch_all(
            connection,
            """
            SELECT *
            FROM policies
            ORDER BY category, policy_id
            """,
        )

    like_query = f"%{normalized_query}%"
    return fetch_all(
        connection,
        """
        SELECT *
        FROM policies
        WHERE lower(policy_id) LIKE ?
            OR lower(category) LIKE ?
            OR lower(title) LIKE ?
            OR lower(body) LIKE ?
            OR lower(eligibility_hints_json) LIKE ?
        ORDER BY category, policy_id
        """,
        (like_query, like_query, like_query, like_query, like_query),
    )


def get_approvals_for_ticket(
    connection: sqlite3.Connection,
    ticket_id: str,
) -> list[dict[str, Any]]:
    return fetch_all(
        connection,
        """
        SELECT *
        FROM approvals
        WHERE ticket_id = ?
        ORDER BY created_at, approval_id
        """,
        (ticket_id,),
    )


def get_audit_events(
    connection: sqlite3.Connection,
    target_id: str,
) -> list[dict[str, Any]]:
    return fetch_all(
        connection,
        """
        SELECT *
        FROM audit_log
        WHERE target_id = ?
        ORDER BY timestamp, audit_id
        """,
        (target_id,),
    )


def snapshot_environment(
    connection: sqlite3.Connection,
    ticket_id: str,
) -> dict[str, Any]:
    ticket = get_ticket(connection, ticket_id)
    if ticket is None:
        return {
            "ticket": None,
            "customer": None,
            "order": None,
            "charges": [],
            "approvals": [],
            "audit_events": [],
        }

    customer = None
    if ticket["customer_id"] is not None:
        customer = get_customer(connection, ticket["customer_id"])

    order = None
    charges: list[dict[str, Any]] = []
    if ticket["order_id"] is not None:
        order = get_order(connection, ticket["order_id"])
        charges = get_charges_for_order(connection, ticket["order_id"])

    return {
        "ticket": ticket,
        "customer": customer,
        "order": order,
        "charges": charges,
        "approvals": get_approvals_for_ticket(connection, ticket_id),
        "audit_events": get_audit_events(connection, ticket_id),
    }


def fetch_one(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[Any, ...] = (),
) -> dict[str, Any] | None:
    row = connection.execute(sql, parameters).fetchone()
    if row is None:
        return None
    return normalize_row(row)


def fetch_all(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    rows = connection.execute(sql, parameters).fetchall()
    return [normalize_row(row) for row in rows]


def normalize_row(row: sqlite3.Row) -> dict[str, Any]:
    normalized = dict(row)
    for key in list(normalized):
        if key.endswith("_json"):
            normalized[key.removesuffix("_json")] = json.loads(normalized.pop(key))
    if "untrusted_content" in normalized:
        normalized["untrusted_content"] = bool(normalized["untrusted_content"])
    return normalized
