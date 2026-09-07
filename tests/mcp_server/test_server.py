from pathlib import Path

import pytest

from bounded_agent.config import Settings
from bounded_agent.mcp_server import (
    DEFAULT_MCP_TOOL_REGISTRATIONS,
    LocalMcpServer,
    McpToolRegistration,
    build_local_mcp_server,
)


def test_build_local_mcp_server_uses_project_settings():
    settings = Settings(_env_file=None)

    server = build_local_mcp_server(settings)
    assert server.health().status == "stopped"
    health = server.start().health()

    assert health.status == "ready"
    assert health.server_name == "bounded-agent-local-mcp"
    assert health.policy_fixture_path == settings.fixtures_dir / "policies.json"
    assert health.support_fixture_path == settings.fixtures_dir / "support_seed.json"
    server.close()


def test_local_mcp_server_exposes_initial_tool_capabilities():
    server = build_local_mcp_server(Settings(_env_file=None))

    capabilities = server.capabilities()

    assert capabilities.server_name == "bounded-agent-local-mcp"
    assert [tool.name for tool in capabilities.tools] == [
        "search_knowledge_base",
        "get_policy_detail",
    ]
    assert capabilities.tools[0].input_schema == "SearchKnowledgeBaseInput"
    assert capabilities.tools[1].output_schema == "GetPolicyDetailOutput"


def test_local_mcp_server_can_be_constructed_with_custom_fixture_paths(tmp_path):
    settings = Settings(
        _env_file=None,
        fixtures_dir=tmp_path / "fixtures",
        runs_dir=tmp_path / "runs",
    )

    server = build_local_mcp_server(settings)

    assert server.policy_fixture_path == tmp_path / "fixtures" / "policies.json"
    assert server.support_fixture_path == tmp_path / "fixtures" / "support_seed.json"


def test_local_mcp_server_can_be_constructed_in_process_with_custom_tools(tmp_path):
    settings = Settings(_env_file=None, fixtures_dir=tmp_path / "fixtures")
    tool = McpToolRegistration(
        name="test_tool",
        description="Test-only tool.",
        input_schema="TestInput",
        output_schema="TestOutput",
    )

    server = LocalMcpServer(settings=settings, tools=[tool], server_name="test-mcp")

    assert server.health().server_name == "test-mcp"
    assert server.health().tools == ["test_tool"]
    assert server.capabilities().tools == [tool]


def test_local_mcp_server_rejects_blank_name_and_empty_tools():
    settings = Settings(_env_file=None)

    with pytest.raises(ValueError, match="server_name cannot be blank"):
        LocalMcpServer(settings=settings, server_name="")

    with pytest.raises(ValueError, match="at least one tool"):
        LocalMcpServer(settings=settings, tools=[])


def test_default_mcp_tool_registrations_are_immutable():
    assert isinstance(DEFAULT_MCP_TOOL_REGISTRATIONS, tuple)


def test_health_paths_are_path_instances():
    server = build_local_mcp_server(Settings(_env_file=None))

    assert isinstance(server.health().policy_fixture_path, Path)
    assert isinstance(server.health().support_fixture_path, Path)
