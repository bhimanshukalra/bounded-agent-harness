import pytest
from pydantic import ValidationError

from bounded_agent.tools import (
    AddTicketCommentInput,
    AddTicketCommentOutput,
    ApplyRefundInput,
    ApplyRefundOutput,
    CheckRefundPolicyInput,
    CheckRefundPolicyOutput,
    DraftCustomerResponseInput,
    DraftCustomerResponseOutput,
    FetchCustomerInput,
    FetchCustomerOutput,
    FetchOrderInput,
    FetchOrderOutput,
    FetchTicketInput,
    FetchTicketOutput,
    RequestApprovalInput,
    RequestApprovalOutput,
    SearchPolicyInput,
    SearchPolicyOutput,
    UpdateTicketStatusInput,
    UpdateTicketStatusOutput,
    validate_tool_schema,
    validation_error_details,
)


def test_fetch_ticket_schemas_accept_ticket_payload():
    input_schema = FetchTicketInput(ticket_id="t_001")
    output_schema = FetchTicketOutput(ticket={"ticket_id": "t_001", "status": "open"})

    assert input_schema.ticket_id == "t_001"
    assert output_schema.ticket["status"] == "open"


def test_fetch_customer_schemas_accept_customer_payload():
    input_schema = FetchCustomerInput(customer_id="c_001")
    output_schema = FetchCustomerOutput(customer={"customer_id": "c_001", "support_tier": "standard"})

    assert input_schema.customer_id == "c_001"
    assert output_schema.customer["support_tier"] == "standard"


def test_fetch_order_schemas_accept_order_and_charges():
    input_schema = FetchOrderInput(order_id="o_001")
    output_schema = FetchOrderOutput(
        order={"order_id": "o_001"},
        charges=[{"charge_id": "ch_001_a"}, {"charge_id": "ch_001_b"}],
    )

    assert input_schema.order_id == "o_001"
    assert [charge["charge_id"] for charge in output_schema.charges] == ["ch_001_a", "ch_001_b"]


def test_search_policy_schemas_accept_policy_results():
    input_schema = SearchPolicyInput(query="duplicate charge")
    output_schema = SearchPolicyOutput(policies=[{"policy_id": "policy_duplicate_charge_refund_v1"}])

    assert input_schema.query == "duplicate charge"
    assert output_schema.policies[0]["policy_id"] == "policy_duplicate_charge_refund_v1"


def test_check_refund_policy_schemas_accept_eligible_decision():
    input_schema = CheckRefundPolicyInput(ticket_id="t_001", order_id="o_001")
    output_schema = CheckRefundPolicyOutput(
        eligible=True,
        decision="eligible",
        approval_required=True,
        policy_references=["policy_duplicate_charge_refund_v1"],
        rationale="Two matching successful charges were found.",
        required_evidence=["same amount", "same currency"],
        recommended_next_action="request_approval",
    )

    assert input_schema.ticket_id == "t_001"
    assert output_schema.approval_required is True


def test_check_refund_policy_rejects_approval_for_ineligible_decision():
    with pytest.raises(ValidationError, match="approval_required"):
        CheckRefundPolicyOutput(
            eligible=False,
            decision="ineligible",
            approval_required=True,
            policy_references=["policy_refund_window_v1"],
            rationale="Order is outside the refund window.",
            recommended_next_action="draft_customer_response",
        )


def test_draft_customer_response_schema_cannot_mark_sent_true():
    DraftCustomerResponseInput(
        ticket_id="t_002",
        response_body="I can draft a policy-backed response.",
        rationale="Refund is outside the policy window.",
    )

    with pytest.raises(ValidationError, match="sent"):
        DraftCustomerResponseOutput(
            ticket_id="t_002",
            draft_body="Draft only.",
            rationale="Not sent externally.",
            sent=True,
        )


def test_request_approval_schemas_require_evidence_summary():
    with pytest.raises(ValidationError, match="evidence_summary"):
        RequestApprovalInput(
            ticket_id="t_001",
            action_type="apply_refund",
            target={"charge_id": "ch_001_b"},
            proposed_arguments={"amount": 49.0},
            evidence_summary=[],
            risk_summary="Refund changes billing state.",
        )

    output_schema = RequestApprovalOutput(
        approval_id="approval_001",
        status="pending",
        ticket_id="t_001",
        action_type="apply_refund",
    )
    assert output_schema.status == "pending"


def test_apply_refund_schemas_reject_non_positive_amount():
    with pytest.raises(ValidationError, match="greater than 0"):
        ApplyRefundInput(charge_id="ch_001_b", amount=0, currency="USD", reason="duplicate_charge")

    output_schema = ApplyRefundOutput(
        charge_id="ch_001_b",
        order_id="o_001",
        amount=49.0,
        currency="USD",
        status="refunded",
        idempotency_key="refund:key:001",
    )
    assert output_schema.status == "refunded"


def test_add_ticket_comment_schemas_require_internal_visibility():
    input_schema = AddTicketCommentInput(ticket_id="t_001", body="Verified duplicate charges.")

    with pytest.raises(ValidationError, match="visibility"):
        AddTicketCommentOutput(
            comment_id="comment_001",
            ticket_id="t_001",
            visibility="public",
            created_at="2026-08-25T00:00:00Z",
        )

    assert input_schema.body == "Verified duplicate charges."


def test_update_ticket_status_schemas_reject_unknown_status():
    with pytest.raises(ValidationError, match="status"):
        UpdateTicketStatusInput(ticket_id="t_001", status="deleted")

    output_schema = UpdateTicketStatusOutput(
        ticket_id="t_001",
        status="resolved",
        updated_at="2026-08-25T00:00:00Z",
    )
    assert output_schema.status == "resolved"


def test_tool_schemas_forbid_extra_fields():
    with pytest.raises(ValidationError, match="Extra inputs"):
        FetchTicketInput(ticket_id="t_001", customer_id="c_001")


def test_validate_tool_schema_returns_typed_schema():
    schema = validate_tool_schema(
        ApplyRefundInput,
        {"charge_id": "ch_001_b", "amount": 49.0, "currency": "USD", "reason": "duplicate_charge"},
    )

    assert isinstance(schema, ApplyRefundInput)
    assert schema.amount == 49.0


def test_validation_error_details_returns_field_paths():
    with pytest.raises(ValidationError) as error:
        validate_tool_schema(ApplyRefundInput, {"charge_id": "", "amount": 49.0, "currency": "USD"})

    assert validation_error_details(error.value) == ["charge_id", "reason"]
