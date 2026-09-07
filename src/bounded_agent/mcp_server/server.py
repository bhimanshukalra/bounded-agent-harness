from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import Field

from bounded_agent.config import Settings, load_settings
from bounded_agent.mcp_server.schemas import StrictMcpSchema


class McpToolRegistration(StrictMcpSchema):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    input_schema: str = Field(min_length=1)
    output_schema: str = Field(min_length=1)


class McpServerCapabilities(StrictMcpSchema):
    server_name: str = Field(min_length=1)
    tools: list[McpToolRegistration] = Field(min_length=1)


class McpServerHealth(StrictMcpSchema):
    status: Literal["ready"]
    server_name: str = Field(min_length=1)
    tools: list[str] = Field(min_length=1)
    policy_fixture_path: Path
    support_fixture_path: Path


DEFAULT_MCP_TOOL_REGISTRATIONS: tuple[McpToolRegistration, ...] = (
    McpToolRegistration(
        name="search_knowledge_base",
        description="Search local policy and knowledge-base records.",
        input_schema="SearchKnowledgeBaseInput",
        output_schema="SearchKnowledgeBaseOutput",
    ),
    McpToolRegistration(
        name="get_policy_detail",
        description="Return one local policy record by policy_id.",
        input_schema="GetPolicyDetailInput",
        output_schema="GetPolicyDetailOutput",
    ),
)


class LocalMcpServer:
    def __init__(
        self,
        settings: Settings,
        tools: Sequence[McpToolRegistration] = DEFAULT_MCP_TOOL_REGISTRATIONS,
        server_name: str = "bounded-agent-local-mcp",
    ) -> None:
        if not server_name:
            raise ValueError("server_name cannot be blank")
        if not tools:
            raise ValueError("local MCP server requires at least one tool")

        self.settings = settings
        self.server_name = server_name
        self._tools = tuple(tools)

    @property
    def tools(self) -> tuple[McpToolRegistration, ...]:
        return self._tools

    @property
    def policy_fixture_path(self) -> Path:
        return self.settings.fixtures_dir / "policies.json"

    @property
    def support_fixture_path(self) -> Path:
        return self.settings.fixtures_dir / "support_seed.json"

    def capabilities(self) -> McpServerCapabilities:
        return McpServerCapabilities(
            server_name=self.server_name,
            tools=list(self._tools),
        )

    def health(self) -> McpServerHealth:
        return McpServerHealth(
            status="ready",
            server_name=self.server_name,
            tools=[tool.name for tool in self._tools],
            policy_fixture_path=self.policy_fixture_path,
            support_fixture_path=self.support_fixture_path,
        )


def build_local_mcp_server(settings: Settings | None = None) -> LocalMcpServer:
    return LocalMcpServer(settings=settings or load_settings())
