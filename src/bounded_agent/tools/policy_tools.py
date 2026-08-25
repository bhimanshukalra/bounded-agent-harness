from datetime import UTC, datetime

from bounded_agent.domain import ErrorType
from bounded_agent.state import get_charges_for_order, get_customer, get_order, get_ticket
from bounded_agent.tools.execution import (
    ToolExecutionContext,
    error_result,
    success_result,
    tool_connection,
)
from bounded_agent.tools.models import ToolResult
from bounded_agent.tools.schemas import CheckRefundPolicyInput, StrictToolSchema

POLICY_REFERENCE_DATE = datetime(2026, 8, 25, tzinfo=UTC)
REFUND_WINDOW_DAYS = 30


def check_refund_policy(context: ToolExecutionContext, tool_input: StrictToolSchema) -> ToolResult:
    typed_input = expect_check_refund_policy_input(tool_input)
    with tool_connection(context) as connection:
        ticket = get_ticket(connection, typed_input.ticket_id)
        if ticket is None:
            return not_found_result("Ticket was not found.", "ticket_id", typed_input.ticket_id)

        order = get_order(connection, typed_input.order_id)
        if order is None:
            return not_found_result("Order was not found.", "order_id", typed_input.order_id)

        customer = get_customer(connection, order["customer_id"])
        if customer is None:
            return not_found_result("Customer was not found.", "customer_id", order["customer_id"])

        charges = get_charges_for_order(connection, typed_input.order_id)

    if is_bundled_promotion(ticket, charges):
        return manual_review_result()

    if has_duplicate_successful_charge(charges):
        return duplicate_charge_eligible_result()

    if is_outside_refund_window(order):
        return refund_window_ineligible_result()

    return missing_information_result()


def duplicate_charge_eligible_result() -> ToolResult:
    return success_result(
        {
            "eligible": True,
            "decision": "eligible",
            "approval_required": True,
            "policy_references": [
                "policy_duplicate_charge_refund_v1",
                "policy_approval_required_v1",
            ],
            "rationale": "The order has multiple successful charges with the same amount and currency.",
            "required_evidence": [
                "same order",
                "same amount",
                "same currency",
                "two successful charges",
            ],
            "recommended_next_action": "request_approval",
        },
        metadata={"source": "deterministic_policy_engine"},
    )


def refund_window_ineligible_result() -> ToolResult:
    return success_result(
        {
            "eligible": False,
            "decision": "ineligible",
            "approval_required": False,
            "policy_references": ["policy_refund_window_v1"],
            "rationale": "The order is outside the standard refund window and no exception applies.",
            "required_evidence": ["order placed date", "refund window policy"],
            "recommended_next_action": "draft_customer_response",
        },
        metadata={"source": "deterministic_policy_engine"},
    )


def manual_review_result() -> ToolResult:
    return success_result(
        {
            "eligible": False,
            "decision": "manual_review",
            "approval_required": False,
            "policy_references": ["policy_bundle_partial_refund_v1"],
            "rationale": "Promotional bundle partial refunds require manual policy review.",
            "required_evidence": ["bundle terms", "item-level pricing"],
            "recommended_next_action": "escalate",
        },
        metadata={"source": "deterministic_policy_engine"},
    )


def missing_information_result() -> ToolResult:
    return success_result(
        {
            "eligible": False,
            "decision": "missing_information",
            "approval_required": False,
            "policy_references": ["policy_duplicate_charge_refund_v1"],
            "rationale": "The available order and charge records do not establish refund eligibility.",
            "required_evidence": ["eligible refund condition", "supporting charge evidence"],
            "recommended_next_action": "gather_more_evidence",
        },
        metadata={"source": "deterministic_policy_engine"},
    )


def has_duplicate_successful_charge(charges: list[dict]) -> bool:
    seen: set[tuple[float, str]] = set()
    for charge in charges:
        if charge["status"] != "succeeded":
            continue
        charge_key = (charge["amount"], charge["currency"])
        if charge_key in seen:
            return True
        seen.add(charge_key)
    return False


def is_outside_refund_window(order: dict) -> bool:
    placed_at = order.get("placed_at")
    if placed_at is None:
        return False
    placed_at_datetime = datetime.fromisoformat(placed_at)
    return (POLICY_REFERENCE_DATE - placed_at_datetime).days > REFUND_WINDOW_DAYS


def is_bundled_promotion(ticket: dict, charges: list[dict]) -> bool:
    if ticket["category"] == "ambiguous_policy":
        return True
    return any("bundle" in charge["charge_id"] for charge in charges)


def not_found_result(message: str, field_name: str, field_value: str) -> ToolResult:
    return error_result(
        ErrorType.NOT_FOUND,
        message,
        details={field_name: field_value},
        metadata={"source": "deterministic_policy_engine"},
    )


def expect_check_refund_policy_input(tool_input: StrictToolSchema) -> CheckRefundPolicyInput:
    if not isinstance(tool_input, CheckRefundPolicyInput):
        raise TypeError(f"expected CheckRefundPolicyInput, got {type(tool_input).__name__}")
    return tool_input
