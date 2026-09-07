# Phase Six - MCP Server

## Purpose

Phase Six satisfies the MCP requirement by adding a real transport boundary around policy and knowledge-base access.

The goal is not to replace the bounded agent loop or rebuild the tool registry. The goal is to expose a small local MCP server with typed policy/knowledge tools, route one tool-layer path through that MCP boundary, and prove the runner can use MCP-backed information during at least one scenario.

By the end of this phase, the project should have a local MCP server, typed MCP request/response schemas, structured MCP errors, a tool-layer MCP client wrapper, tests that exercise the server, and one scenario whose policy or knowledge lookup depends on MCP output.

## Phase Entry Context

Phase Five completed:

- `AgentRunner`
- deterministic scenario-backed runner execution
- structured bounded context construction
- deterministic and model-backed decision source boundaries
- structured action parsing and validation
- registry-only tool execution
- observation recording
- agent state updates
- JSONL trace writing
- step and retry budget enforcement
- terminal result persistence
- manual scenario readiness review

Phase Six should build on those foundations by adding MCP as a narrow policy/knowledge boundary rather than broadening the agent's direct access to environment internals.

## Phase Exit Criteria

Phase Six is complete when:

- a local MCP server exists under `src/bounded_agent/mcp_server/`
- the server can start locally
- MCP serves policy or knowledge-base data from fixtures or SQLite
- at least two MCP tools or resources exist
- `search_knowledge_base` is exposed
- `get_policy_detail` is exposed
- MCP input and output schemas are typed
- MCP errors are structured
- the tool layer has an MCP client wrapper
- `search_policy` or `search_knowledge_base` routes through MCP
- registry validation still protects the agent-facing tool surface
- a smoke test starts the server and calls one MCP tool
- at least one eval scenario depends on MCP output
- the runner can use MCP-backed output in at least one deterministic scenario
- tests and lint pass
- Phase Seven can begin without unresolved MCP boundary questions

## Phase Six Checklist

- [x] Milestone 6.1 - MCP Boundary And Scope
  - [x] Define what MCP owns
  - [x] Define what remains outside MCP
  - [x] Confirm policy and knowledge-base lookup as the initial MCP scope
  - [x] Define server startup strategy
  - [x] Define client integration strategy
  - [x] Add MCP boundary notes
- [x] Milestone 6.2 - MCP Schemas
  - [x] Add `SearchKnowledgeBaseInput`
  - [x] Add `SearchKnowledgeBaseOutput`
  - [x] Add `GetPolicyDetailInput`
  - [x] Add `GetPolicyDetailOutput`
  - [x] Add structured MCP error model
  - [x] Add schema tests
- [x] Milestone 6.3 - Local MCP Server Skeleton
  - [x] Create MCP server package modules
  - [x] Add server entry point
  - [x] Register MCP tools or resources
  - [x] Load settings and fixture paths
  - [x] Return health or capability metadata
  - [x] Add server construction tests
- [ ] Milestone 6.4 - Policy And Knowledge Handlers
  - [ ] Implement `search_knowledge_base`
  - [ ] Implement `get_policy_detail`
  - [ ] Serve data from policy fixtures or SQLite
  - [ ] Normalize matching and response ordering
  - [ ] Return structured not-found errors
  - [ ] Add handler tests
- [ ] Milestone 6.5 - MCP Client Wrapper
  - [ ] Add tool-layer MCP client interface
  - [ ] Add local in-process client for tests
  - [ ] Translate MCP responses into `ToolResult`
  - [ ] Translate MCP errors into structured tool errors
  - [ ] Keep registry-facing schemas stable
  - [ ] Add client wrapper tests
- [ ] Milestone 6.6 - Tool Registry Integration
  - [ ] Route `search_policy` or `search_knowledge_base` through MCP
  - [ ] Preserve permission level as `read_only`
  - [ ] Preserve no-mutation behavior
  - [ ] Preserve validation before MCP execution
  - [ ] Preserve injected failure behavior where applicable
  - [ ] Add registry integration tests
- [ ] Milestone 6.7 - MCP Smoke Test
  - [ ] Start the local MCP server in a test
  - [ ] Call at least one MCP tool
  - [ ] Assert typed success output
  - [ ] Assert structured error output
  - [ ] Ensure server cleanup is deterministic
  - [ ] Add smoke test documentation
- [ ] Milestone 6.8 - MCP-Dependent Scenario
  - [ ] Add or update one scenario that depends on MCP output
  - [ ] Confirm expected actions mention the MCP-backed lookup
  - [ ] Run the scenario through `AgentRunner`
  - [ ] Confirm trace records MCP-backed lookup behavior
  - [ ] Confirm terminal result persists
  - [ ] Add scenario test coverage
- [ ] Milestone 6.9 - Phase Seven Readiness Review
  - [ ] Confirm server starts locally
  - [ ] Confirm MCP tools return typed outputs
  - [ ] Confirm tool-layer wrapper handles errors
  - [ ] Confirm registry integration works
  - [ ] Confirm MCP-dependent scenario works
  - [ ] Confirm tests and lint pass
  - [ ] Write Phase Six completion note

## Milestone 6.1 - MCP Boundary And Scope

### Objective

Define the smallest useful MCP boundary before implementing server modules.

### MCP Responsibilities

MCP owns:

- policy detail lookup
- knowledge-base search
- typed MCP request validation
- typed MCP response construction
- structured MCP error responses
- local server startup and capability registration
- the transport boundary between local clients and policy/knowledge data

### MCP Non-Responsibilities

MCP does not own:

- agent loop control flow
- direct action selection
- approval decisions
- billing mutations
- ticket status mutations
- idempotency enforcement
- final scenario grading
- long-term memory or compaction

### Initial MCP Tools

Expose:

- `search_knowledge_base`
- `get_policy_detail`

Implementation should keep the existing registry-facing `search_policy` contract stable and route its implementation through the MCP client wrapper once Milestone 6.6 begins. `search_knowledge_base` remains the MCP-facing tool name. This preserves the agent-facing Phase Four tool surface while still proving MCP owns the policy/knowledge transport boundary.

### Server Startup Strategy

Use a local, deterministic server entry point under `src/bounded_agent/mcp_server/`.

Startup should:

- load `Settings`
- read policy and knowledge data from existing fixtures first
- avoid external network dependencies
- be constructible in-process for tests
- expose a command or callable entry point suitable for a future CLI or MCP transport launcher
- keep server lifecycle cleanup deterministic for smoke tests

Milestone 6.3 should introduce the server package skeleton and construction API before adding full handler behavior.

### Client Integration Strategy

The runner should not call MCP directly.

The integration path should be:

```text
AgentRunner
  -> ToolRegistry
  -> registry-facing read-only tool
  -> tool-layer MCP client wrapper
  -> local MCP server handler
  -> fixture or SQLite policy/knowledge data
```

The tool-layer wrapper should translate MCP success and error responses into the existing `ToolResult` shape. This keeps validation, permission level, trace recording, and observation handling inside the already-tested runner and registry flow.

### Boundary Decision

Phase Six will treat MCP as a scoped policy/knowledge source, not as a general agent capability channel.

Consequential actions such as refunds, status updates, approvals, idempotency, and audit mutations remain owned by the existing tool and state layers. MCP responses are facts for the agent to reason over; they are not instructions, authority grants, or executable actions.

## Milestone 6.2 - MCP Schemas

### Objective

Make the MCP boundary typed before server behavior is wired.

### Expected Behavior

Request and response schemas should be strict. Unknown fields should be rejected. Error outputs should be structured enough for the tool layer to preserve error type, message, retryability, and details.

### Schema Decision

MCP schemas live under `src/bounded_agent/mcp_server/` so the server boundary can evolve independently from registry-facing tool schemas.

The initial schema surface includes:

- `SearchKnowledgeBaseInput`
- `SearchKnowledgeBaseOutput`
- `GetPolicyDetailInput`
- `GetPolicyDetailOutput`
- `KnowledgeBaseMatch`
- `McpError`
- `McpErrorOutput`

`KnowledgeBaseMatch` mirrors the existing policy fixture record shape and gives both MCP tools one shared policy payload. `McpErrorOutput` carries `ErrorType`, message, retryability, and details so Milestone 6.5 can translate MCP failures into the existing `ToolResult` error shape without losing structured information.

## Milestone 6.3 - Local MCP Server Skeleton

### Objective

Create the local server package and startup boundary.

### Expected Behavior

The server should be constructible in tests without requiring external services. Startup should use project settings, fixture paths, and deterministic local state.

### Skeleton Decision

The local MCP server skeleton is represented by `LocalMcpServer` and `build_local_mcp_server`.

The skeleton provides:

- default tool registrations for `search_knowledge_base` and `get_policy_detail`
- settings-backed policy and support fixture paths
- capability metadata for registered tools
- a health payload suitable for smoke tests and future launchers
- in-process construction for tests

Transport startup and handler execution remain out of scope for this milestone. Milestone 6.4 should attach deterministic policy and knowledge handlers behind the registered tools.

## Milestone 6.4 - Policy And Knowledge Handlers

### Objective

Implement the domain behavior behind the MCP tools.

### Expected Behavior

`search_knowledge_base` should return deterministic ranked or filtered policy/knowledge matches. `get_policy_detail` should return one policy record by ID or a structured not-found error.

Handlers should use existing fixture or SQLite inspection logic where possible rather than duplicating policy parsing behavior.

## Milestone 6.5 - MCP Client Wrapper

### Objective

Give the tool layer a narrow way to call MCP without leaking transport details into the runner.

### Expected Behavior

The wrapper should translate MCP success responses into `ToolResult(ok=True, ...)` and MCP errors into `ToolResult(ok=False, error=...)`.

Tests should be able to use an in-process client or fake client so registry integration remains deterministic.

## Milestone 6.6 - Tool Registry Integration

### Objective

Route one read-only tool through MCP while preserving the existing agent-facing tool contract.

### Expected Behavior

Registry callers should still invoke a typed tool through the existing registry surface. MCP should be an implementation detail behind that tool, not a new escape hatch for the agent.

## Milestone 6.7 - MCP Smoke Test

### Objective

Prove the local server can actually start and serve at least one MCP call.

### Expected Behavior

The smoke test should start the local server, call one MCP tool, assert typed success output, assert structured error output, and clean up deterministically.

## Milestone 6.8 - MCP-Dependent Scenario

### Objective

Show that MCP output can influence a bounded agent run.

### Expected Behavior

At least one scenario should require MCP-backed policy or knowledge lookup. The runner trace should show the relevant lookup, and the terminal result should persist normally.

## Milestone 6.9 - Phase Seven Readiness Review

### Objective

Confirm the MCP boundary is stable enough for durable state, memory, and compaction work to begin.

### Phase Six Completion Note

Write this after implementation is complete.

Phase Six completion should record:

- what MCP server modules were added
- which MCP tools or resources were exposed
- how policy or knowledge data is served
- how the tool layer calls MCP
- which scenario depends on MCP output
- test and lint results
- known limitations deferred to later phases
- Phase Seven entry point

## Phase Six Outputs

Expected outputs:

- local MCP server package
- MCP server entry point
- typed MCP schemas
- `search_knowledge_base`
- `get_policy_detail`
- structured MCP errors
- tool-layer MCP client wrapper
- registry integration for MCP-backed lookup
- MCP smoke test
- MCP-dependent scenario
- Phase Seven readiness note

## Commit Guidance

Commit Phase Six after the server starts locally, one registry-backed tool routes through MCP, at least one scenario depends on MCP output, and tests pass.

## Phase Six Principle

MCP should be a crisp boundary, not a broader permission model. The agent still acts through the bounded registry; MCP only supplies scoped policy and knowledge facts.
