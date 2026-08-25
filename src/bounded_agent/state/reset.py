import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bounded_agent.config import Settings, load_settings
from bounded_agent.domain import ApprovalStatus, Scenario
from bounded_agent.evals import load_scenario
from bounded_agent.state.fixtures import json_dump, seed_base_fixtures
from bounded_agent.state.schema import connect_database, initialize_schema

FIXED_RESET_TIMESTAMP = "2026-08-25T00:00:00Z"


@dataclass(frozen=True)
class ResetResult:
    scenario_id: str
    run_id: str
    db_path: Path


def run_database_path(run_id: str, settings: Settings | None = None) -> Path:
    active_settings = settings or load_settings()
    return active_settings.runs_dir / run_id / "state.db"


def reset_scenario_environment(
    scenario_id: str,
    run_id: str,
    settings: Settings | None = None,
) -> ResetResult:
    active_settings = settings or load_settings()
    scenario = load_scenario(scenario_id, active_settings)
    db_path = run_database_path(run_id, active_settings)

    if db_path.exists():
        db_path.unlink()

    connection = connect_database(db_path)
    try:
        initialize_schema(connection)
        seed_base_fixtures(
            connection,
            active_settings.fixtures_dir / "support_seed.json",
            active_settings.fixtures_dir / "policies.json",
        )
        configure_injected_failures(connection, scenario)
        preload_approval_fixture(connection, scenario, run_id)
    finally:
        connection.close()

    return ResetResult(scenario_id=scenario_id, run_id=run_id, db_path=db_path)


def configure_injected_failures(connection: sqlite3.Connection, scenario: Scenario) -> None:
    with connection:
        for index, failure in enumerate(scenario.injected_failures, start=1):
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
                    f"{scenario.id}:failure:{index}",
                    scenario.id,
                    failure["tool"],
                    failure["type"],
                    failure.get("count", 1),
                    json_dump(failure.get("target", {})),
                    json_dump(failure.get("payload", {})),
                ),
            )


def preload_approval_fixture(
    connection: sqlite3.Connection,
    scenario: Scenario,
    run_id: str,
) -> None:
    approval_fixture = scenario.initial_state.get("approval_fixture")
    if approval_fixture not in {"approved", "denied"}:
        return

    order_id = scenario.initial_state["order_id"]
    ticket_id = scenario.initial_state["ticket_id"]
    charge = duplicate_refund_charge(connection, order_id)
    approval_id = f"{scenario.id}:approval:refund"

    with connection:
        connection.execute(
            """
            INSERT INTO approvals (
                approval_id,
                run_id,
                scenario_id,
                ticket_id,
                action_type,
                target_json,
                proposed_arguments_json,
                evidence_summary_json,
                risk_summary,
                status,
                decision,
                created_at,
                resolved_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id,
                run_id,
                scenario.id,
                ticket_id,
                "apply_refund",
                json_dump({"order_id": order_id, "charge_id": charge["charge_id"]}),
                json_dump(
                    {
                        "amount": charge["amount"],
                        "currency": charge["currency"],
                        "reason": "duplicate_charge",
                    }
                ),
                json_dump(
                    [
                        "Scenario fixture preloads approval decision.",
                        "Order has duplicate successful charges.",
                    ]
                ),
                "Refund changes mock billing state and must be idempotent.",
                ApprovalStatus.APPROVED
                if approval_fixture == "approved"
                else ApprovalStatus.DENIED,
                approval_fixture,
                FIXED_RESET_TIMESTAMP,
                FIXED_RESET_TIMESTAMP,
            ),
        )


def duplicate_refund_charge(connection: sqlite3.Connection, order_id: str) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT charge_id, amount, currency
        FROM charges
        WHERE order_id = ?
        ORDER BY charged_at, charge_id
        """,
        (order_id,),
    ).fetchall()
    if len(rows) < 2:
        raise ValueError(f"order does not have a duplicate charge fixture: {order_id}")
    return dict(rows[-1])
