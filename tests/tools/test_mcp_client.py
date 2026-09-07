from bounded_agent.config import Settings
from bounded_agent.domain import ErrorType
from bounded_agent.mcp_server import (
    GetPolicyDetailInput,
    McpError,
    McpErrorOutput,
    SearchKnowledgeBaseInput,
    SearchKnowledgeBaseOutput,
    build_local_mcp_server,
)
from bounded_agent.tools import (
    LocalMcpPolicyClient,
    get_policy_detail_with_mcp,
    search_policy_with_mcp,
)
from bounded_agent.tools.schemas import SearchPolicyInput


class NotFoundMcpClient:
    def search_knowledge_base(self, tool_input: SearchKnowledgeBaseInput) -> McpErrorOutput:
        return McpErrorOutput(
            error=McpError(
                type=ErrorType.NOT_FOUND,
                message="Knowledge record was not found.",
                details={"query": tool_input.query},
            )
        )

    def get_policy_detail(self, tool_input: GetPolicyDetailInput) -> McpErrorOutput:
        return McpErrorOutput(
            error=McpError(
                type=ErrorType.NOT_FOUND,
                message="Policy was not found.",
                details={"policy_id": tool_input.policy_id},
            )
        )


class EmptyMcpClient:
    def search_knowledge_base(self, tool_input: SearchKnowledgeBaseInput) -> SearchKnowledgeBaseOutput:
        return SearchKnowledgeBaseOutput(query=tool_input.query, total_matches=0)

    def get_policy_detail(self, tool_input: GetPolicyDetailInput) -> McpErrorOutput:
        return NotFoundMcpClient().get_policy_detail(tool_input)


def test_local_client_translates_search_response_to_stable_tool_result():
    server = build_local_mcp_server(Settings(_env_file=None))
    try:
        server.start()
        result = search_policy_with_mcp(
            LocalMcpPolicyClient(server),
            SearchPolicyInput(query="approval required"),
        )
    finally:
        server.close()

    assert result.ok is True
    assert [policy["policy_id"] for policy in result.result["policies"]] == [
        "policy_approval_required_v1",
        "policy_duplicate_charge_refund_v1",
    ]
    assert result.metadata == {
        "source": "local_mcp",
        "mcp_tool": "search_knowledge_base",
        "total_matches": 2,
    }


def test_client_allows_empty_search_results():
    result = search_policy_with_mcp(EmptyMcpClient(), SearchPolicyInput(query="not present"))

    assert result.ok is True
    assert result.result == {"policies": []}
    assert result.metadata["total_matches"] == 0


def test_client_translates_mcp_errors_to_structured_tool_errors():
    result = search_policy_with_mcp(NotFoundMcpClient(), SearchPolicyInput(query="missing"))

    assert result.ok is False
    assert result.error.type is ErrorType.NOT_FOUND
    assert result.error.details == {"query": "missing"}
    assert result.metadata == {"source": "local_mcp"}


def test_client_translates_policy_detail_response_and_error():
    server = build_local_mcp_server(Settings(_env_file=None))
    try:
        server.start()
        success = get_policy_detail_with_mcp(
            LocalMcpPolicyClient(server),
            "policy_duplicate_charge_refund_v1",
        )
    finally:
        server.close()
    error = get_policy_detail_with_mcp(NotFoundMcpClient(), "policy_missing_v1")

    assert success.ok is True
    assert success.result["policy"]["policy_id"] == "policy_duplicate_charge_refund_v1"
    assert success.metadata["mcp_tool"] == "get_policy_detail"
    assert error.ok is False
    assert error.error.type is ErrorType.NOT_FOUND
    assert error.error.details == {"policy_id": "policy_missing_v1"}
