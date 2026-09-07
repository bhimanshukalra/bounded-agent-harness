import pytest

from bounded_agent.config import Settings
from bounded_agent.domain import ErrorType
from bounded_agent.mcp_server import (
    GetPolicyDetailInput,
    McpErrorOutput,
    SearchKnowledgeBaseInput,
    build_local_mcp_server,
)


@pytest.fixture
def server():
    local_server = build_local_mcp_server(Settings(_env_file=None))
    yield local_server
    local_server.close()


def test_search_knowledge_base_matches_case_insensitively_in_stable_order(server):
    result = server.handlers.search_knowledge_base(
        SearchKnowledgeBaseInput(query="  APPROVAL REQUIRED  ")
    )

    assert result.query == "APPROVAL REQUIRED"
    assert result.total_matches == 2
    assert [match.policy_id for match in result.matches] == [
        "policy_approval_required_v1",
        "policy_duplicate_charge_refund_v1",
    ]


def test_search_knowledge_base_applies_limit_without_changing_total(server):
    result = server.handlers.search_knowledge_base(SearchKnowledgeBaseInput(query="refund", limit=1))

    assert len(result.matches) == 1
    assert result.total_matches == 4
    assert result.matches[0].policy_id == "policy_approval_required_v1"


def test_get_policy_detail_returns_typed_policy(server):
    result = server.handlers.get_policy_detail(
        GetPolicyDetailInput(policy_id=" policy_duplicate_charge_refund_v1 ")
    )

    assert result.policy.policy_id == "policy_duplicate_charge_refund_v1"
    assert result.policy.eligibility_hints[-1] == "approval required"


def test_get_policy_detail_returns_structured_not_found_error(server):
    result = server.handlers.get_policy_detail(GetPolicyDetailInput(policy_id="policy_missing_v1"))

    assert isinstance(result, McpErrorOutput)
    assert result.error.type is ErrorType.NOT_FOUND
    assert result.error.retryable is False
    assert result.error.details == {"policy_id": "policy_missing_v1"}


@pytest.mark.parametrize("field", ["query", "policy_id"])
def test_handler_inputs_reject_whitespace_only_identifiers(field):
    schema = SearchKnowledgeBaseInput if field == "query" else GetPolicyDetailInput

    with pytest.raises(ValueError, match=f"{field} cannot be blank"):
        schema(**{field: "   "})
