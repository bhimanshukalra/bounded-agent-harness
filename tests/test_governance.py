import pytest
from pydantic import ValidationError

from bounded_agent.governance import CapabilityProposal, DecisionRecord, ProposalStatus, RiskLevel


def proposal(**overrides):
    values = {
        "proposal_id": "proposal_001",
        "title": "Experimental model mode",
        "owner": "agent-platform",
        "problem_statement": "Evaluate a bounded model-backed decision source.",
        "scope": ["Decision-source adapter only."],
        "non_goals": ["No new tool authority."],
        "risk_level": RiskLevel.HIGH,
        "trust_boundary_impact": "Registry authority remains unchanged.",
        "untrusted_content_impact": "Existing sanitization remains required.",
        "approval_and_idempotency_impact": "Existing gates remain required.",
        "scenario_ids": ["support_008"],
        "baseline_threshold": "No safety regression.",
        "verifier_coverage": "Safety and terminal checks must pass.",
        "rollback_plan": "Disable the experiment flag.",
        "containment_flag": "ENABLE_LIVE_MODEL",
    }
    values.update(overrides)
    return CapabilityProposal(**values)


def test_high_risk_proposals_require_a_containment_flag():
    with pytest.raises(ValidationError, match="containment_flag"):
        proposal(containment_flag=None)


def test_governance_records_capture_release_and_rollback_decisions():
    capability = proposal()
    record = DecisionRecord(
        proposal_id=capability.proposal_id,
        status=ProposalStatus.ACCEPTED,
        decision_owner="safety-reviewer",
        rationale="Containment preserves the existing authority boundary.",
        release_gate="Capstone and verifier checks pass.",
        rollback_trigger="Any safety regression.",
        review_date="2026-12-07",
    )

    assert capability.containment_flag == "ENABLE_LIVE_MODEL"
    assert record.status is ProposalStatus.ACCEPTED
