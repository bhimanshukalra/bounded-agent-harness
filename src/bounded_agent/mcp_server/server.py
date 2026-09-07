from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError

from bounded_agent.config import Settings, load_settings
from bounded_agent.domain import ErrorType
from bounded_agent.mcp_server.handlers import (
    PolicyKnowledgeHandlers,
    call_get_policy_detail,
    call_search_knowledge_base,
)
from bounded_agent.mcp_server.schemas import (
    GetPolicyDetailInput,
    McpError,
    McpErrorOutput,
    McpOutputSchema,
    SearchKnowledgeBaseInput,
    StrictMcpSchema,
    mcp_validation_error_details,
    validate_mcp_schema,
)


class McpToolRegistration(StrictMcpSchema):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    input_schema: str = Field(min_length=1)
    output_schema: str = Field(min_length=1)


class McpServerCapabilities(StrictMcpSchema):
    server_name: str = Field(min_length=1)
    tools: list[McpToolRegistration] = Field(min_length=1)


class McpServerHealth(StrictMcpSchema):
    status: Literal["ready", "stopped"]
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
        self.handlers = PolicyKnowledgeHandlers(self.policy_fixture_path)
        self._started = False

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
            status="ready" if self._started else "stopped",
            server_name=self.server_name,
            tools=[tool.name for tool in self._tools],
            policy_fixture_path=self.policy_fixture_path,
            support_fixture_path=self.support_fixture_path,
        )

    def start(self) -> "LocalMcpServer":
        self._started = True
        return self

    def call_tool(self, tool_name: str, payload: dict[str, Any]) -> McpOutputSchema:
        if not self._started:
            return mcp_error(
                ErrorType.UNRECOVERABLE,
                "Local MCP server is not started.",
                details={"tool_name": tool_name},
            )

        if tool_name == "search_knowledge_base":
            validated_input = validate_mcp_input(SearchKnowledgeBaseInput, payload)
            if isinstance(validated_input, McpErrorOutput):
                return validated_input
            return call_search_knowledge_base(self.handlers, validated_input)

        if tool_name == "get_policy_detail":
            validated_input = validate_mcp_input(GetPolicyDetailInput, payload)
            if isinstance(validated_input, McpErrorOutput):
                return validated_input
            return call_get_policy_detail(self.handlers, validated_input)

        return mcp_error(
            ErrorType.VALIDATION_ERROR,
            "Unknown MCP tool.",
            details={"tool_name": tool_name},
        )

    def close(self) -> None:
        self.handlers.close()
        self._started = False


def build_local_mcp_server(settings: Settings | None = None) -> LocalMcpServer:
    return LocalMcpServer(settings=settings or load_settings())


def validate_mcp_input[SchemaT: StrictMcpSchema](
    schema_type: type[SchemaT],
    payload: dict[str, Any],
) -> SchemaT | McpErrorOutput:
    try:
        return validate_mcp_schema(schema_type, payload)
    except ValidationError as error:
        return mcp_error(
            ErrorType.VALIDATION_ERROR,
            "MCP tool input failed validation.",
            details={"fields": mcp_validation_error_details(error)},
        )


def mcp_error(
    error_type: ErrorType,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> McpErrorOutput:
    return McpErrorOutput(
        error=McpError(type=error_type, message=message, details=details or {})
    )
