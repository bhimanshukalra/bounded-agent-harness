from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from bounded_agent.domain import ErrorType


class StrictMcpSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KnowledgeBaseMatch(StrictMcpSchema):
    policy_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    title: str = Field(min_length=1)
    version: str = Field(min_length=1)
    body: str = Field(min_length=1)
    eligibility_hints: list[str] = Field(default_factory=list)


class SearchKnowledgeBaseInput(StrictMcpSchema):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=50)


class SearchKnowledgeBaseOutput(StrictMcpSchema):
    query: str = Field(min_length=1)
    matches: list[KnowledgeBaseMatch] = Field(default_factory=list)
    total_matches: int = Field(ge=0)


class GetPolicyDetailInput(StrictMcpSchema):
    policy_id: str = Field(min_length=1)


class GetPolicyDetailOutput(StrictMcpSchema):
    policy: KnowledgeBaseMatch


class McpError(StrictMcpSchema):
    type: ErrorType
    message: str = Field(min_length=1)
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class McpErrorOutput(StrictMcpSchema):
    error: McpError


McpInputSchema = SearchKnowledgeBaseInput | GetPolicyDetailInput
McpOutputSchema = SearchKnowledgeBaseOutput | GetPolicyDetailOutput | McpErrorOutput


def validate_mcp_schema[SchemaT: StrictMcpSchema](
    schema_type: type[SchemaT],
    payload: dict[str, Any],
) -> SchemaT:
    return schema_type.model_validate(payload)


def mcp_validation_error_details(error: ValidationError) -> list[str]:
    return [".".join(str(part) for part in issue["loc"]) for issue in error.errors()]
