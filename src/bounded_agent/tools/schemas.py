from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class StrictToolSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FetchTicketInput(StrictToolSchema):
    ticket_id: str = Field(min_length=1)


class FetchTicketOutput(StrictToolSchema):
    ticket: dict[str, Any]


class FetchCustomerInput(StrictToolSchema):
    customer_id: str = Field(min_length=1)


class FetchCustomerOutput(StrictToolSchema):
    customer: dict[str, Any]


class FetchOrderInput(StrictToolSchema):
    order_id: str = Field(min_length=1)


class FetchOrderOutput(StrictToolSchema):
    order: dict[str, Any]
    charges: list[dict[str, Any]] = Field(default_factory=list)


class SearchPolicyInput(StrictToolSchema):
    query: str = Field(min_length=1)


class SearchPolicyOutput(StrictToolSchema):
    policies: list[dict[str, Any]]


class CheckRefundPolicyInput(StrictToolSchema):
    ticket_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)


class CheckRefundPolicyOutput(StrictToolSchema):
    eligible: bool
    decision: Literal["eligible", "ineligible", "manual_review", "missing_information"]
    approval_required: bool
    policy_references: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    required_evidence: list[str] = Field(default_factory=list)
    recommended_next_action: str = Field(min_length=1)

    @model_validator(mode="after")
    def keep_approval_consistent_with_decision(self) -> "CheckRefundPolicyOutput":
        if self.decision != "eligible" and self.approval_required:
            raise ValueError("approval_required can only be true for eligible refund decisions")
        return self


class DraftCustomerResponseInput(StrictToolSchema):
    ticket_id: str = Field(min_length=1)
    response_body: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class DraftCustomerResponseOutput(StrictToolSchema):
    ticket_id: str = Field(min_length=1)
    draft_body: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    sent: Literal[False] = False


class RequestApprovalInput(StrictToolSchema):
    ticket_id: str = Field(min_length=1)
    action_type: str = Field(min_length=1)
    target: dict[str, Any] = Field(default_factory=dict)
    proposed_arguments: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: list[str] = Field(min_length=1)
    risk_summary: str = Field(min_length=1)


class RequestApprovalOutput(StrictToolSchema):
    approval_id: str = Field(min_length=1)
    status: Literal["pending"]
    ticket_id: str = Field(min_length=1)
    action_type: str = Field(min_length=1)


class ApplyRefundInput(StrictToolSchema):
    charge_id: str = Field(min_length=1)
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    reason: str = Field(min_length=1)


class ApplyRefundOutput(StrictToolSchema):
    charge_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    status: Literal["refunded", "partially_refunded"]
    idempotency_key: str = Field(min_length=1)


class AddTicketCommentInput(StrictToolSchema):
    ticket_id: str = Field(min_length=1)
    body: str = Field(min_length=1)


class AddTicketCommentOutput(StrictToolSchema):
    comment_id: str = Field(min_length=1)
    ticket_id: str = Field(min_length=1)
    visibility: Literal["internal"]
    created_at: str = Field(min_length=1)


class UpdateTicketStatusInput(StrictToolSchema):
    ticket_id: str = Field(min_length=1)
    status: Literal["open", "pending", "resolved", "escalated"]


class UpdateTicketStatusOutput(StrictToolSchema):
    ticket_id: str = Field(min_length=1)
    status: Literal["open", "pending", "resolved", "escalated"]
    updated_at: str = Field(min_length=1)


ToolInputSchema = (
    FetchTicketInput
    | FetchCustomerInput
    | FetchOrderInput
    | SearchPolicyInput
    | CheckRefundPolicyInput
    | DraftCustomerResponseInput
    | RequestApprovalInput
    | ApplyRefundInput
    | AddTicketCommentInput
    | UpdateTicketStatusInput
)

ToolOutputSchema = (
    FetchTicketOutput
    | FetchCustomerOutput
    | FetchOrderOutput
    | SearchPolicyOutput
    | CheckRefundPolicyOutput
    | DraftCustomerResponseOutput
    | RequestApprovalOutput
    | ApplyRefundOutput
    | AddTicketCommentOutput
    | UpdateTicketStatusOutput
)

def validate_tool_schema[SchemaT: StrictToolSchema](
    schema_type: type[SchemaT],
    payload: dict[str, Any],
) -> SchemaT:
    return schema_type.model_validate(payload)


def validation_error_details(error: ValidationError) -> list[str]:
    return [".".join(str(part) for part in issue["loc"]) for issue in error.errors()]
