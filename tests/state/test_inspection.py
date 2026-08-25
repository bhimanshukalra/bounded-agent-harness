from bounded_agent.config import Settings
from bounded_agent.state import (
    connect_database,
    get_approvals_for_ticket,
    get_audit_events,
    get_charges_for_order,
    get_customer,
    get_order,
    get_ticket,
    reset_scenario_environment,
    search_policies,
    snapshot_environment,
)


def reset_connection(tmp_path, scenario_id: str = "support_001"):
    settings = Settings(_env_file=None, runs_dir=tmp_path / "runs")
    result = reset_scenario_environment(scenario_id, f"{scenario_id}_run", settings)
    return connect_database(result.db_path)


def test_get_ticket_returns_parsed_ticket(tmp_path):
    connection = reset_connection(tmp_path)

    ticket = get_ticket(connection, "t_001")

    assert ticket is not None
    assert ticket["ticket_id"] == "t_001"
    assert ticket["metadata"] == {}
    assert ticket["untrusted_content"] is True


def test_get_ticket_returns_none_for_missing_ticket(tmp_path):
    connection = reset_connection(tmp_path)

    assert get_ticket(connection, "t_missing") is None


def test_get_customer_returns_parsed_customer(tmp_path):
    connection = reset_connection(tmp_path)

    customer = get_customer(connection, "c_005")

    assert customer is not None
    assert customer["customer_id"] == "c_005"
    assert customer["risk_flags"] == ["manual_policy_review"]


def test_get_order_returns_parsed_order(tmp_path):
    connection = reset_connection(tmp_path)

    order = get_order(connection, "o_001")

    assert order is not None
    assert order["order_id"] == "o_001"
    assert order["metadata"] == {}


def test_get_charges_for_order_returns_deterministic_order(tmp_path):
    connection = reset_connection(tmp_path)

    charges = get_charges_for_order(connection, "o_001")

    assert [charge["charge_id"] for charge in charges] == ["ch_001_a", "ch_001_b"]


def test_search_policies_matches_body_and_hints(tmp_path):
    connection = reset_connection(tmp_path)

    policies = search_policies(connection, "approval required")

    assert [policy["policy_id"] for policy in policies] == [
        "policy_approval_required_v1",
        "policy_duplicate_charge_refund_v1",
    ]
    assert policies[0]["eligibility_hints"] == [
        "approval required",
        "refund",
        "credit",
        "ticket closure",
    ]


def test_search_policies_returns_all_for_blank_query(tmp_path):
    connection = reset_connection(tmp_path)

    policies = search_policies(connection, " ")

    assert len(policies) == 6
    assert [policy["policy_id"] for policy in policies][:2] == [
        "policy_approval_required_v1",
        "policy_budget_safe_stop_v1",
    ]


def test_get_approvals_for_ticket_returns_preloaded_fixture(tmp_path):
    connection = reset_connection(tmp_path, "support_009")

    approvals = get_approvals_for_ticket(connection, "t_009")

    assert len(approvals) == 1
    assert approvals[0]["status"] == "approved"
    assert approvals[0]["target"] == {"charge_id": "ch_009_b", "order_id": "o_009"}


def test_get_audit_events_returns_events_for_target(tmp_path):
    connection = reset_connection(tmp_path)
    connection.execute(
        """
        INSERT INTO audit_log (
            audit_id,
            timestamp,
            actor,
            action,
            target_type,
            target_id,
            payload_json
        )
        VALUES (
            'audit_001',
            '2026-08-25T00:00:00Z',
            'test',
            'inspect',
            'ticket',
            't_001',
            '{"ok": true}'
        )
        """
    )
    connection.commit()

    audit_events = get_audit_events(connection, "t_001")

    assert audit_events[0]["audit_id"] == "audit_001"
    assert audit_events[0]["payload"] == {"ok": True}


def test_snapshot_environment_returns_linked_state(tmp_path):
    connection = reset_connection(tmp_path, "support_009")

    snapshot = snapshot_environment(connection, "t_009")

    assert snapshot["ticket"]["ticket_id"] == "t_009"
    assert snapshot["customer"]["customer_id"] == "c_009"
    assert snapshot["order"]["order_id"] == "o_009"
    assert [charge["charge_id"] for charge in snapshot["charges"]] == ["ch_009_a", "ch_009_b"]
    assert snapshot["approvals"][0]["status"] == "approved"
    assert snapshot["audit_events"] == []


def test_snapshot_environment_returns_empty_shape_for_missing_ticket(tmp_path):
    connection = reset_connection(tmp_path)

    snapshot = snapshot_environment(connection, "t_missing")

    assert snapshot == {
        "ticket": None,
        "customer": None,
        "order": None,
        "charges": [],
        "approvals": [],
        "audit_events": [],
    }
