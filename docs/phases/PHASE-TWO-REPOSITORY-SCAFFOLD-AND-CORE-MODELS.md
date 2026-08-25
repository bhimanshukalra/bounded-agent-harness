# Phase Two - Repository Scaffold And Core Models

## Purpose

Phase Two turns the Phase One contracts into a working Python project skeleton.

The goal is not to build the full agent loop yet. The goal is to create the package structure, dependency setup, domain enums, Pydantic models, prompt files, scenario skeletons, and validation tests that later phases will build on.

By the end of this phase, the project should import cleanly, expose a basic CLI, validate the core contracts, and contain the first scenario fixtures as structured files.

## Phase Entry Context

Phase Zero locked the product shape: a bounded support-resolution agent over a mocked ticketing, customer, policy, and billing environment.

Phase One locked the contracts:

- terminal states
- permission levels
- approval contract
- agent action schema
- tool contract
- error taxonomy
- retry and stop policy
- safety policy
- verifier responsibilities
- artifact locations

Phase Two should implement the scaffolding and core models implied by those contracts.

## Phase Exit Criteria

Phase Two is complete when:

- `pyproject.toml` exists
- package imports cleanly
- `src/bounded_agent/` package exists
- core module folders exist
- domain enums are implemented
- core Pydantic models are implemented
- model validation tests pass
- basic CLI help works
- `.env.example` exists
- prompt policy files exist
- first 10 scenario drafts exist as JSON skeleton files
- no runtime agent loop behavior is required yet

## Phase Two Checklist

- [x] Milestone 2.1 - Project Metadata And Dependency Setup
  - [x] Create `pyproject.toml`
  - [x] Select Python version
  - [x] Add runtime dependencies
  - [x] Add dev/test dependencies
  - [x] Add package metadata
  - [x] Add basic test command
- [x] Milestone 2.2 - Repository Directory Scaffold
  - [x] Create source package
  - [x] Create module folders
  - [x] Create tests folders
  - [x] Create data folders
  - [x] Create prompt folders
  - [x] Create report folders
- [x] Milestone 2.3 - Configuration And Environment Skeleton
  - [x] Create `.env.example`
  - [x] Create config module
  - [x] Define default paths
  - [x] Define default budgets
  - [x] Define feature flags
  - [x] Add config validation tests
- [x] Milestone 2.4 - Domain Enums
  - [x] Implement terminal states
  - [x] Implement permission levels
  - [x] Implement approval statuses
  - [x] Implement action types
  - [x] Implement error types
  - [x] Implement scenario difficulty/tags where useful
  - [x] Add enum stability tests
- [ ] Milestone 2.5 - Core Pydantic Models
  - [ ] Implement `Task`
  - [ ] Implement `Scenario`
  - [ ] Implement `AgentState`
  - [ ] Implement `BudgetUsage`
  - [ ] Implement `ApprovalRequest`
  - [ ] Implement `TerminalResult`
  - [ ] Implement `TraceEvent`
  - [ ] Implement `EvalRun`
  - [ ] Add model validation tests
- [ ] Milestone 2.6 - Agent Action And Tool Models
  - [ ] Implement `ActionDecision`
  - [ ] Implement action payload models
  - [ ] Implement `ToolSpec`
  - [ ] Implement `ToolCall`
  - [ ] Implement `ToolResult`
  - [ ] Implement structured error model
  - [ ] Add schema validation tests
- [ ] Milestone 2.7 - Prompt File Skeletons
  - [ ] Create `prompts/agent.md`
  - [ ] Create `prompts/safety_policy.md`
  - [ ] Create `prompts/verifier.md`
  - [ ] Create `prompts/compaction.md`
  - [ ] Create `prompts/judge.md`
  - [ ] Include structured output contract references
- [ ] Milestone 2.8 - Scenario JSON Skeletons
  - [ ] Create `data/scenarios/`
  - [ ] Convert 10 Phase Zero scenario drafts to JSON
  - [ ] Validate scenario IDs
  - [ ] Validate expected terminal states
  - [ ] Validate expected/forbidden actions
  - [ ] Add scenario schema tests
- [ ] Milestone 2.9 - Basic CLI Skeleton
  - [ ] Add CLI app
  - [ ] Add `run-scenario` placeholder
  - [ ] Add `run-eval` placeholder
  - [ ] Add `reset-env` placeholder
  - [ ] Add `show-trace` placeholder
  - [ ] Verify CLI help works
- [ ] Milestone 2.10 - Phase Three Readiness Review
  - [ ] Confirm scaffold imports cleanly
  - [ ] Confirm tests pass
  - [ ] Confirm scenarios validate
  - [ ] Confirm contracts have code homes
  - [ ] Write Phase Two completion note

## Milestone 2.1 - Project Metadata And Dependency Setup

### Objective

Create the Python project metadata and dependency baseline.

### Recommended Dependencies

Runtime:

- `pydantic`
- `pydantic-settings`
- `typer`
- `rich`

Development/test:

- `pytest`
- `ruff`

Likely later-phase dependencies:

- MCP SDK or FastMCP
- LLM provider SDK
- SQLite helper library if needed

### Recommended `pyproject.toml` Shape

```toml
[project]
name = "bounded-agent-harness"
version = "0.1.0"
description = "A bounded support-resolution agent harness with typed tools, durable state, traces, approvals, and evals."
requires-python = ">=3.11"

[project.scripts]
bounded-agent = "bounded_agent.cli:app"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
```

### Deliverable

Project metadata and dependency setup.

### Acceptance Check

The project can install in editable mode and expose the package import path.

## Milestone 2.2 - Repository Directory Scaffold

### Objective

Create the directory structure that later phases will fill in.

### Target Structure

```text
.
├── README.md
├── pyproject.toml
├── .env.example
├── Makefile
├── data/
│   ├── fixtures/
│   ├── scenarios/
│   ├── runs/
│   └── eval_runs/
├── reports/
│   ├── eval-report.md
│   └── experiments/
├── prompts/
│   ├── agent.md
│   ├── verifier.md
│   ├── compaction.md
│   ├── judge.md
│   └── safety_policy.md
├── src/
│   └── bounded_agent/
│       ├── __init__.py
│       ├── config.py
│       ├── cli.py
│       ├── domain/
│       ├── loop/
│       ├── tools/
│       ├── mcp_server/
│       ├── state/
│       ├── safety/
│       ├── tracing/
│       └── evals/
├── tests/
│   ├── domain/
│   ├── safety/
│   ├── tools/
│   ├── evals/
│   └── cli/
└── scripts/
```

### Deliverable

Repository scaffold with importable package directories.

### Acceptance Check

The layout matches the architecture decisions from Phase One.

## Milestone 2.3 - Configuration And Environment Skeleton

### Objective

Define project configuration before runtime code depends on hardcoded paths.

### Configuration Fields

- project root
- data directory
- fixtures directory
- scenarios directory
- runs directory
- eval runs directory
- prompts directory
- default max steps
- default retry budget
- default token budget
- default cost budget
- model provider placeholder
- model name placeholder
- MCP enabled flag
- live model enabled flag

### `.env.example` Fields

```text
MODEL_PROVIDER=
MODEL_NAME=
MODEL_API_KEY=
DEFAULT_MAX_STEPS=12
DEFAULT_MAX_TOOL_RETRIES=2
DEFAULT_MAX_INVALID_ACTIONS=2
ENABLE_LIVE_MODEL=false
ENABLE_MCP=false
```

### Deliverable

Config skeleton and environment example.

### Acceptance Check

Tests can instantiate config with defaults and with environment overrides.

## Milestone 2.4 - Domain Enums

### Objective

Implement the stable enum values defined in Phase One.

### Required Enums

- `TerminalState`
- `PermissionLevel`
- `ApprovalStatus`
- `ActionType`
- `ErrorType`
- `RunnerType`
- `ScenarioDifficulty`

### Enum Stability Rule

Enum values should use explicit string values matching the docs and scenario JSON.

Example:

```python
class TerminalState(str, Enum):
    RESOLVED = "resolved"
    NEEDS_HUMAN_APPROVAL = "needs_human_approval"
```

### Deliverable

Domain enums plus tests.

### Acceptance Check

Scenario JSON can refer to enum values by string without translation hacks.

## Milestone 2.5 - Core Pydantic Models

### Objective

Implement the durable objects shared across loop, tools, traces, and evals.

### Required Models

- `Task`
- `Scenario`
- `AgentState`
- `BudgetUsage`
- `ApprovalRequest`
- `TerminalResult`
- `TraceEvent`
- `EvalRun`
- `VerifierResult`

### Validation Expectations

- `TerminalResult` requires state-specific fields.
- `Scenario.expected_terminal_state` must be a valid terminal state.
- `ApprovalRequest.status` must be a valid approval status.
- `BudgetUsage.steps` cannot exceed `max_steps` unless terminal state is budget failure.
- `TraceEvent.event_type` should be structured and non-empty.
- `EvalRun` must reference scenario results or result paths.

### Deliverable

Core Pydantic models and validation tests.

### Acceptance Check

Invalid terminal results, scenarios, and approval requests fail validation.

## Milestone 2.6 - Agent Action And Tool Models

### Objective

Implement the structured contracts for model decisions and tool execution.

### Required Models

- `ActionDecision`
- `ToolCallAction`
- `ApprovalRequestAction`
- `TerminalStateAction`
- `RetryAction`
- `ReplanAction`
- `SafetyCheck`
- `ToolSpec`
- `ToolCall`
- `ToolResult`
- `ToolError`
- `Observation`

### Validation Expectations

- unknown action type fails validation
- unknown permission level fails validation
- approval-required tool specs must mark `approval_required=true`
- mutating tool specs must specify idempotency behavior
- tool errors must use known error types
- tool results cannot have both success result and error

### Deliverable

Action and tool Pydantic models with tests.

### Acceptance Check

The future loop can reject malformed model decisions and malformed tool results before execution continues.

## Milestone 2.7 - Prompt File Skeletons

### Objective

Create prompt files as versioned project artifacts.

### Prompt Files

- `prompts/agent.md`
- `prompts/safety_policy.md`
- `prompts/verifier.md`
- `prompts/compaction.md`
- `prompts/judge.md`

### Prompt Skeleton Requirements

`agent.md` should include:

- role
- bounded workflow
- available action types
- structured output contract
- permission reminder
- terminal-state requirement
- untrusted-content reminder

`safety_policy.md` should include:

- forbidden capabilities
- approval rules
- untrusted content rules
- private data minimization
- policy-violation stop behavior

### Deliverable

Prompt skeletons.

### Acceptance Check

Prompt files exist and contain the contract names needed by later prompt builder code.

## Milestone 2.8 - Scenario JSON Skeletons

### Objective

Convert the first 10 scenario drafts into structured files.

### Required Files

```text
data/scenarios/support_001.json
data/scenarios/support_002.json
data/scenarios/support_003.json
data/scenarios/support_004.json
data/scenarios/support_005.json
data/scenarios/support_006.json
data/scenarios/support_007.json
data/scenarios/support_008.json
data/scenarios/support_009.json
data/scenarios/support_010.json
```

### Scenario Validation Rules

- ID must match filename.
- Expected terminal state must be valid.
- Expected actions must be non-empty.
- Forbidden actions must be explicit.
- Tags must be non-empty.
- Difficulty must be valid.
- Grading rubric must be non-empty.

### Deliverable

Ten scenario JSON skeletons and schema tests.

### Acceptance Check

All scenario files load into the `Scenario` model.

## Milestone 2.9 - Basic CLI Skeleton

### Objective

Create a CLI shape without full runtime behavior.

### CLI Commands

```text
bounded-agent run-scenario SCENARIO_ID
bounded-agent run-eval
bounded-agent reset-env
bounded-agent show-trace RUN_ID
bounded-agent validate-scenarios
```

### Placeholder Behavior

- `run-scenario`: validates scenario exists, then prints "not implemented yet"
- `run-eval`: validates scenario directory, then prints "not implemented yet"
- `reset-env`: prints "not implemented yet"
- `show-trace`: validates run ID shape, then prints "not implemented yet"
- `validate-scenarios`: loads all scenario JSON files and validates models

### Deliverable

Basic CLI.

### Acceptance Check

CLI help works and scenario validation can run.

## Milestone 2.10 - Phase Three Readiness Review

### Objective

Confirm the project is ready for mock environment implementation.

### Review Checklist

- `pyproject.toml` exists.
- Package imports cleanly.
- Core directories exist.
- Config skeleton exists.
- Domain enums exist.
- Core Pydantic models exist.
- Action and tool models exist.
- Prompt skeletons exist.
- Scenario JSON skeletons exist.
- CLI help works.
- Model and scenario validation tests pass.

### Deliverable

Phase Two completion note.

### Acceptance Check

Phase Three can begin with SQLite schema design, fixture loading, deterministic reset, injected failures, and audit logging.

## Phase Two Outputs

By the end of this phase, the repo should have:

- project metadata
- package scaffold
- config skeleton
- domain enums
- core models
- action and tool models
- prompt skeletons
- scenario JSON skeletons
- basic CLI
- validation tests
- Phase Three readiness note

## Suggested Commit Boundary

Commit Phase Two as the first implementation scaffold.

Suggested commit message:

```text
feat: scaffold bounded agent package and core models
```

## Phase Two Principle

Build boring foundations first. The loop will be easier to reason about if the contracts, schemas, paths, and validation tests are already solid.
