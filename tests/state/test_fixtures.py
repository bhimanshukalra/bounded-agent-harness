import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "data" / "fixtures"
SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "data" / "scenarios"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def test_fixture_files_exist_and_parse():
    support_seed = load_json(FIXTURES_DIR / "support_seed.json")
    policies = load_json(FIXTURES_DIR / "policies.json")

    assert support_seed["customers"]
    assert support_seed["orders"]
    assert support_seed["charges"]
    assert support_seed["tickets"]
    assert policies["policies"]


def test_support_seed_covers_existing_scenario_tickets():
    support_seed = load_json(FIXTURES_DIR / "support_seed.json")
    ticket_ids = {ticket["ticket_id"] for ticket in support_seed["tickets"]}
    scenario_ticket_ids = {
        load_json(path)["initial_state"]["ticket_id"]
        for path in sorted(SCENARIOS_DIR.glob("support_*.json"))
    }

    assert scenario_ticket_ids.issubset(ticket_ids)


def test_support_seed_intentionally_omits_missing_records():
    support_seed = load_json(FIXTURES_DIR / "support_seed.json")
    customer_ids = {customer["customer_id"] for customer in support_seed["customers"]}
    order_ids = {order["order_id"] for order in support_seed["orders"]}

    assert "c_missing" not in customer_ids
    assert "o_missing" not in order_ids


def test_duplicate_charge_scenarios_have_matching_successful_charges():
    support_seed = load_json(FIXTURES_DIR / "support_seed.json")
    charges_by_order: dict[str, list[dict]] = {}
    for charge in support_seed["charges"]:
        charges_by_order.setdefault(charge["order_id"], []).append(charge)

    for order_id in ["o_001", "o_006", "o_007", "o_008", "o_009"]:
        charges = charges_by_order[order_id]
        amounts = {(charge["amount"], charge["currency"], charge["status"]) for charge in charges}

        assert len(charges) == 2
        assert amounts == {(49.0, "USD", "succeeded")}


def test_fixture_hooks_cover_failure_and_approval_scenarios():
    support_seed = load_json(FIXTURES_DIR / "support_seed.json")
    hooks = support_seed["scenario_hooks"]

    assert hooks["support_006"]["injected_failure"]["type"] == "timeout"
    assert hooks["support_007"]["approval_fixture"] == "denied"
    assert hooks["support_008"]["ticket_contains_prompt_injection"] is True
    assert hooks["support_009"]["approval_fixture"] == "approved"
    assert hooks["support_009"]["injected_failure"]["type"] == "transient_error_after_side_effect"
    assert hooks["support_010"]["max_steps"] == 3


def test_policy_fixture_covers_required_categories():
    policies = load_json(FIXTURES_DIR / "policies.json")
    categories = {policy["category"] for policy in policies["policies"]}

    assert {
        "duplicate_charge",
        "refund_window",
        "bundled_promotions",
        "approval_required_actions",
        "safety",
        "budget",
    }.issubset(categories)
