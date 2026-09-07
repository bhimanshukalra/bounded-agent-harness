import pytest
from pydantic import ValidationError

from bounded_agent.domain import ErrorType
from bounded_agent.mcp_server import (
    GetPolicyDetailInput,
    GetPolicyDetailOutput,
    KnowledgeBaseMatch,
    McpError,
    McpErrorOutput,
    SearchKnowledgeBaseInput,
    SearchKnowledgeBaseOutput,
    mcp_validation_error_details,
    validate_mcp_schema,
)


def policy_match() -> KnowledgeBaseMatch:
    return KnowledgeBaseMatch(
        policy_id="policy_duplicate_charge_refund_v1",
        category="duplicate_charge",
        title="Duplicate Charge Refund Eligibility",
        version="2026-08-01",
        body="A verified duplicate charge is eligible for refund.",
        eligibility_hints=["same order", "same amount", "same currency"],
    )


def test_search_knowledge_base_schemas_accept_typed_matches():
    input_schema = SearchKnowledgeBaseInput(query="duplicate charge", limit=3)
    output_schema = SearchKnowledgeBaseOutput(
        query="duplicate charge",
        matches=[policy_match()],
        total_matches=1,
    )

    assert input_schema.query == "duplicate charge"
    assert input_schema.limit == 3
    assert output_schema.matches[0].policy_id == "policy_duplicate_charge_refund_v1"


def test_search_knowledge_base_input_defaults_and_bounds_limit():
    assert SearchKnowledgeBaseInput(query="refund").limit == 5

    with pytest.raises(ValidationError, match="less than or equal to 50"):
        SearchKnowledgeBaseInput(query="refund", limit=51)

    with pytest.raises(ValidationError, match="greater than or equal to 1"):
        SearchKnowledgeBaseInput(query="refund", limit=0)


def test_get_policy_detail_schemas_accept_policy_payload():
    input_schema = GetPolicyDetailInput(policy_id="policy_duplicate_charge_refund_v1")
    output_schema = GetPolicyDetailOutput(policy=policy_match())

    assert input_schema.policy_id == "policy_duplicate_charge_refund_v1"
    assert output_schema.policy.title == "Duplicate Charge Refund Eligibility"


def test_mcp_error_output_preserves_tool_error_semantics():
    output_schema = McpErrorOutput(
        error=McpError(
            type=ErrorType.NOT_FOUND,
            message="Policy was not found.",
            retryable=False,
            details={"policy_id": "policy_missing"},
        )
    )

    assert output_schema.error.type is ErrorType.NOT_FOUND
    assert output_schema.error.details == {"policy_id": "policy_missing"}


def test_mcp_schemas_forbid_extra_fields():
    with pytest.raises(ValidationError, match="Extra inputs"):
        GetPolicyDetailInput(policy_id="policy_duplicate_charge_refund_v1", unexpected=True)


def test_validate_mcp_schema_returns_typed_schema():
    schema = validate_mcp_schema(
        SearchKnowledgeBaseInput,
        {"query": "approval required", "limit": 2},
    )

    assert isinstance(schema, SearchKnowledgeBaseInput)
    assert schema.limit == 2


def test_mcp_validation_error_details_returns_field_paths():
    with pytest.raises(ValidationError) as error:
        validate_mcp_schema(SearchKnowledgeBaseInput, {"query": "", "limit": 0})

    assert mcp_validation_error_details(error.value) == ["query", "limit"]
