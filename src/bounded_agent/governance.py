from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ProposalStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DEFERRED = "deferred"
    REJECTED = "rejected"


class CapabilityProposal(BaseModel):
    """Minimum evidence required before extending the bounded harness."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    status: ProposalStatus = ProposalStatus.PROPOSED
    problem_statement: str = Field(min_length=1)
    scope: list[str] = Field(min_length=1)
    non_goals: list[str] = Field(min_length=1)
    risk_level: RiskLevel
    trust_boundary_impact: str = Field(min_length=1)
    untrusted_content_impact: str = Field(min_length=1)
    approval_and_idempotency_impact: str = Field(min_length=1)
    scenario_ids: list[str] = Field(min_length=1)
    baseline_threshold: str = Field(min_length=1)
    verifier_coverage: str = Field(min_length=1)
    rollback_plan: str = Field(min_length=1)
    containment_flag: str | None = None

    @model_validator(mode="after")
    def high_risk_changes_require_containment(self) -> "CapabilityProposal":
        if self.risk_level is RiskLevel.HIGH and self.containment_flag is None:
            raise ValueError("high-risk proposals require a containment_flag")
        return self


class DecisionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str = Field(min_length=1)
    status: ProposalStatus
    decision_owner: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    accepted_risks: list[str] = Field(default_factory=list)
    release_gate: str = Field(min_length=1)
    rollback_trigger: str = Field(min_length=1)
    review_date: str = Field(min_length=1)
