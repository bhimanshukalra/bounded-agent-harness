from typing import Protocol

from bounded_agent.mcp_server import (
    GetPolicyDetailInput,
    GetPolicyDetailOutput,
    LocalMcpServer,
    McpErrorOutput,
    SearchKnowledgeBaseInput,
    SearchKnowledgeBaseOutput,
)
from bounded_agent.tools.execution import error_result, success_result
from bounded_agent.tools.models import ToolResult
from bounded_agent.tools.schemas import SearchPolicyInput


class McpPolicyClient(Protocol):
    """Narrow policy/knowledge client contract used by the tool layer."""

    def search_knowledge_base(
        self,
        tool_input: SearchKnowledgeBaseInput,
    ) -> SearchKnowledgeBaseOutput | McpErrorOutput: ...

    def get_policy_detail(
        self,
        tool_input: GetPolicyDetailInput,
    ) -> GetPolicyDetailOutput | McpErrorOutput: ...


class LocalMcpPolicyClient:
    """In-process MCP client for the deterministic local MCP server."""

    def __init__(self, server: LocalMcpServer) -> None:
        self.server = server

    def search_knowledge_base(
        self,
        tool_input: SearchKnowledgeBaseInput,
    ) -> SearchKnowledgeBaseOutput | McpErrorOutput:
        response = self.server.call_tool("search_knowledge_base", tool_input.model_dump())
        if isinstance(response, SearchKnowledgeBaseOutput | McpErrorOutput):
            return response
        raise TypeError("search_knowledge_base returned an unexpected MCP response")

    def get_policy_detail(
        self,
        tool_input: GetPolicyDetailInput,
    ) -> GetPolicyDetailOutput | McpErrorOutput:
        response = self.server.call_tool("get_policy_detail", tool_input.model_dump())
        if isinstance(response, GetPolicyDetailOutput | McpErrorOutput):
            return response
        raise TypeError("get_policy_detail returned an unexpected MCP response")


def search_policy_with_mcp(client: McpPolicyClient, tool_input: SearchPolicyInput) -> ToolResult:
    response = client.search_knowledge_base(
        SearchKnowledgeBaseInput(query=tool_input.query, limit=50)
    )
    if isinstance(response, McpErrorOutput):
        return mcp_error_result(response)

    return success_result(
        {"policies": [match.model_dump() for match in response.matches]},
        metadata={
            "source": "local_mcp",
            "mcp_tool": "search_knowledge_base",
            "total_matches": response.total_matches,
        },
    )


def get_policy_detail_with_mcp(client: McpPolicyClient, policy_id: str) -> ToolResult:
    response = client.get_policy_detail(GetPolicyDetailInput(policy_id=policy_id))
    if isinstance(response, McpErrorOutput):
        return mcp_error_result(response)

    return success_result(
        {"policy": response.policy.model_dump()},
        metadata={"source": "local_mcp", "mcp_tool": "get_policy_detail"},
    )


def mcp_error_result(response: McpErrorOutput) -> ToolResult:
    return error_result(
        response.error.type,
        response.error.message,
        retryable=response.error.retryable,
        details=response.error.details,
        metadata={"source": "local_mcp"},
    )
