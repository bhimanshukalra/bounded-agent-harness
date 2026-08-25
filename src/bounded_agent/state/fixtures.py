import json
import sqlite3
from pathlib import Path
from typing import Any


def load_fixture_file(path: Path | str) -> dict[str, Any]:
    fixture_path = Path(path)
    if not fixture_path.exists():
        raise FileNotFoundError(f"fixture file not found: {fixture_path}")
    return json.loads(fixture_path.read_text())


def require_sections(fixture: dict[str, Any], sections: set[str]) -> None:
    missing = sorted(section for section in sections if section not in fixture)
    if missing:
        raise ValueError(f"fixture is missing required sections: {', '.join(missing)}")


def json_dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def seed_support_fixture(connection: sqlite3.Connection, fixture: dict[str, Any]) -> None:
    require_sections(fixture, {"customers", "orders", "charges", "tickets"})

    with connection:
        for customer in fixture["customers"]:
            connection.execute(
                """
                INSERT INTO customers (
                    customer_id,
                    account_status,
                    support_tier,
                    risk_flags_json,
                    masked_email,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    customer["customer_id"],
                    customer["account_status"],
                    customer["support_tier"],
                    json_dump(customer.get("risk_flags", [])),
                    customer.get("masked_email"),
                    json_dump(customer.get("metadata", {})),
                ),
            )

        for order in fixture["orders"]:
            connection.execute(
                """
                INSERT INTO orders (
                    order_id,
                    customer_id,
                    status,
                    placed_at,
                    refund_status,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    order["order_id"],
                    order["customer_id"],
                    order["status"],
                    order.get("placed_at"),
                    order.get("refund_status", "none"),
                    json_dump(order.get("metadata", {})),
                ),
            )

        for ticket in fixture["tickets"]:
            connection.execute(
                """
                INSERT INTO tickets (
                    ticket_id,
                    customer_id,
                    order_id,
                    category,
                    status,
                    subject,
                    body,
                    untrusted_content,
                    created_at,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket["ticket_id"],
                    ticket.get("customer_id"),
                    ticket.get("order_id"),
                    ticket["category"],
                    ticket["status"],
                    ticket["subject"],
                    ticket["body"],
                    int(ticket.get("untrusted_content", True)),
                    ticket.get("created_at"),
                    json_dump(ticket.get("metadata", {})),
                ),
            )

        for charge in fixture["charges"]:
            connection.execute(
                """
                INSERT INTO charges (
                    charge_id,
                    order_id,
                    amount,
                    currency,
                    status,
                    charged_at,
                    refunded_amount,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    charge["charge_id"],
                    charge["order_id"],
                    charge["amount"],
                    charge["currency"],
                    charge["status"],
                    charge.get("charged_at"),
                    charge.get("refunded_amount", 0),
                    json_dump(charge.get("metadata", {})),
                ),
            )


def seed_policy_fixture(connection: sqlite3.Connection, fixture: dict[str, Any]) -> None:
    require_sections(fixture, {"policies"})

    with connection:
        for policy in fixture["policies"]:
            connection.execute(
                """
                INSERT INTO policies (
                    policy_id,
                    category,
                    title,
                    body,
                    version,
                    eligibility_hints_json,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    policy["policy_id"],
                    policy["category"],
                    policy["title"],
                    policy["body"],
                    policy["version"],
                    json_dump(policy.get("eligibility_hints", [])),
                    json_dump(policy.get("metadata", {})),
                ),
            )


def seed_base_fixtures(
    connection: sqlite3.Connection,
    support_fixture_path: Path | str,
    policy_fixture_path: Path | str,
) -> None:
    seed_support_fixture(connection, load_fixture_file(support_fixture_path))
    seed_policy_fixture(connection, load_fixture_file(policy_fixture_path))
