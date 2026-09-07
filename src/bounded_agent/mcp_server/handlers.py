import sqlite3
from pathlib import Path

from bounded_agent.domain import ErrorType
from bounded_agent.mcp_server.schemas import (
    GetPolicyDetailInput,
    GetPolicyDetailOutput,
    KnowledgeBaseMatch,
    McpError,
    McpErrorOutput,
    McpOutputSchema,
    SearchKnowledgeBaseInput,
    SearchKnowledgeBaseOutput,
)
from bounded_agent.state import (
    get_policy,
    initialize_schema,
    load_fixture_file,
    search_policies,
    seed_policy_fixture,
)


class PolicyKnowledgeHandlers:
    """Deterministic in-process handlers backed by the configured policy fixture."""

    def __init__(self, policy_fixture_path: Path) -> None:
        self.policy_fixture_path = policy_fixture_path
        self._connection: sqlite3.Connection | None = None

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def search_knowledge_base(self, tool_input: SearchKnowledgeBaseInput) -> SearchKnowledgeBaseOutput:
        policies = search_policies(self.connection, tool_input.query)
        matches = [policy_match(policy) for policy in policies]
        return SearchKnowledgeBaseOutput(
            query=tool_input.query,
            matches=matches[: tool_input.limit],
            total_matches=len(matches),
        )

    def get_policy_detail(
        self,
        tool_input: GetPolicyDetailInput,
    ) -> GetPolicyDetailOutput | McpErrorOutput:
        policy = get_policy(self.connection, tool_input.policy_id)
        if policy is None:
            return McpErrorOutput(
                error=McpError(
                    type=ErrorType.NOT_FOUND,
                    message="Policy was not found.",
                    details={"policy_id": tool_input.policy_id},
                )
            )
        return GetPolicyDetailOutput(policy=policy_match(policy))

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(":memory:")
            self._connection.row_factory = sqlite3.Row
            initialize_schema(self._connection)
            seed_policy_fixture(
                self._connection,
                load_fixture_file(self.policy_fixture_path),
            )
        return self._connection


def policy_match(policy: dict[str, object]) -> KnowledgeBaseMatch:
    return KnowledgeBaseMatch.model_validate(
        {
            "policy_id": policy["policy_id"],
            "category": policy["category"],
            "title": policy["title"],
            "version": policy["version"],
            "body": policy["body"],
            "eligibility_hints": policy["eligibility_hints"],
        }
    )


def call_search_knowledge_base(
    handlers: PolicyKnowledgeHandlers,
    tool_input: SearchKnowledgeBaseInput,
) -> McpOutputSchema:
    return handlers.search_knowledge_base(tool_input)


def call_get_policy_detail(
    handlers: PolicyKnowledgeHandlers,
    tool_input: GetPolicyDetailInput,
) -> McpOutputSchema:
    return handlers.get_policy_detail(tool_input)
