from bounded_agent.config import Settings
from bounded_agent.domain import ErrorType
from bounded_agent.mcp_server import (
    McpErrorOutput,
    SearchKnowledgeBaseOutput,
    build_local_mcp_server,
)


def test_local_mcp_server_smoke_call_returns_typed_success_and_cleans_up():
    server = build_local_mcp_server(Settings(_env_file=None))

    assert server.health().status == "stopped"
    server.start()
    result = server.call_tool(
        "search_knowledge_base",
        {"query": "approval required", "limit": 1},
    )
    server.close()

    assert isinstance(result, SearchKnowledgeBaseOutput)
    assert result.total_matches == 2
    assert [match.policy_id for match in result.matches] == ["policy_approval_required_v1"]
    assert server.health().status == "stopped"


def test_local_mcp_server_smoke_call_returns_structured_errors():
    server = build_local_mcp_server(Settings(_env_file=None)).start()
    try:
        missing = server.call_tool("get_policy_detail", {"policy_id": "policy_missing_v1"})
        invalid = server.call_tool("search_knowledge_base", {"limit": 1})
    finally:
        server.close()

    assert isinstance(missing, McpErrorOutput)
    assert missing.error.type is ErrorType.NOT_FOUND
    assert missing.error.details == {"policy_id": "policy_missing_v1"}
    assert isinstance(invalid, McpErrorOutput)
    assert invalid.error.type is ErrorType.VALIDATION_ERROR
    assert invalid.error.details == {"fields": ["query"]}
