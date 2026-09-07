# Phase Five - Bare Bounded Agent Loop

## Purpose

Phase Five implements the central bounded agent loop before adding advanced recovery, durable memory, MCP exposure, or independent verification.

The goal is to connect the existing domain models, scenario loader, resettable mock environment, and Phase Four tool registry into a minimal runner that can move through multiple iterations and stop only in a named terminal state.

By the end of this phase, a task should be able to load scenario state, build bounded context, select a structured action from a mocked or model-backed decision source, validate and execute registry tools, record observations, update run state, write trace events, enforce budgets, and persist a `TerminalResult`.

## Phase Entry Context

Phase Four completed:

- strict tool schemas
- execution context model
- central tool registry
- registered specs for every planned scoped tool
- read-only inspection tools
- deterministic policy reasoning tools
- draft-only response generation
- low-risk audited comments
- approval-gated consequential tools
- mutating-tool idempotency
- injected failure handling through registry execution
- tool validation, permission, idempotency, and failure tests
- Phase Five readiness review

Phase Five should build on those foundations by calling the tool registry for validated tool execution instead of reaching into SQLite or tool internals directly.

## Phase Exit Criteria

Phase Five is complete when:

- `AgentRunner` exists
- tasks and scenario state can be loaded into a run
- the runner builds bounded context for each step
- a mocked decision source can drive deterministic tests
- optional model-backed decision source boundaries are defined
- structured action decisions are parsed and validated
- unknown or unsupported action types are rejected
- tool calls are validated through the Phase Four registry
- tools execute only through registry execution
- approval requests can be emitted as terminal or intermediate outcomes
- observations are recorded after each action
- durable agent state is updated after each step
- trace events are written during the run
- max step budget is enforced
- max retry budget is enforced
- terminal results are persisted with state-specific fields
- at least five manual scenarios run end to end
- Phase Six can begin by exposing the runner through an MCP server

## Phase Five Checklist

- [x] Milestone 5.1 - Runner Boundary And Control Flow
  - [x] Define what `AgentRunner` owns
  - [x] Define what remains outside the runner
  - [x] Define runner inputs
  - [x] Define runner outputs
  - [x] Define stop conditions
  - [x] Add runner contract tests
- [x] Milestone 5.2 - Run State Loading
  - [x] Load task metadata
  - [x] Load scenario metadata
  - [x] Reset or attach to scenario environment
  - [x] Initialize `AgentState`
  - [x] Initialize `BudgetUsage`
  - [x] Add state-loading tests
- [x] Milestone 5.3 - Bounded Context Builder
  - [x] Build context from task, state, scenario, and observations
  - [x] Include available tool specs from registry
  - [x] Include relevant safety and budget constraints
  - [x] Exclude raw database access
  - [x] Add prompt/context tests
- [x] Milestone 5.4 - Decision Source And Parser
  - [x] Define decision source protocol
  - [x] Implement deterministic mocked decision source
  - [x] Define model-backed decision source boundary
  - [x] Parse structured action decisions
  - [x] Reject malformed decisions
  - [x] Add parser tests
- [x] Milestone 5.5 - Action Validation
  - [x] Validate action type
  - [x] Validate tool call name against registry
  - [x] Validate tool arguments through registry
  - [x] Validate approval request actions
  - [x] Validate terminal-state actions
  - [x] Add action validation tests
- [x] Milestone 5.6 - Tool Execution Integration
  - [x] Build tool execution context
  - [x] Execute tools through registry only
  - [x] Record successful tool observations
  - [x] Record structured tool errors
  - [x] Preserve idempotency behavior for mutating tools
  - [x] Add registry-integration tests
- [x] Milestone 5.7 - State Updates And Trace Writing
  - [x] Append completed actions
  - [x] Append tool call history
  - [x] Track pending approval IDs
  - [x] Update retry counters
  - [x] Write trace events for decisions, tool calls, observations, retries, and terminal states
  - [x] Add trace/state tests
- [x] Milestone 5.8 - Budget And Retry Enforcement
  - [x] Enforce max step budget before executing another action
  - [x] Enforce max retry budget by failure type
  - [x] Emit `failed_budget_exceeded` when needed
  - [x] Emit `blocked_tool_error` or `failed_unrecoverable` when retry recovery fails
  - [x] Add budget and retry tests
- [x] Milestone 5.9 - Terminal Result Persistence
  - [x] Convert terminal actions into `TerminalResult`
  - [x] Populate state-specific terminal fields
  - [x] Persist terminal result to run output path
  - [x] Persist trace path on terminal result
  - [x] Add terminal persistence tests
- [x] Milestone 5.10 - Manual Scenario Readiness Review
  - [x] Run at least five manual scenarios
  - [x] Confirm multi-step runs work
  - [x] Confirm named terminal states are produced
  - [x] Confirm state and traces are written
  - [x] Confirm tests and lint pass
  - [x] Write Phase Five completion note

## Milestone 5.1 - Runner Boundary And Control Flow

### Objective

Define the smallest useful runner boundary before implementing loop behavior.

### Runner Responsibilities

The runner owns:

- run initialization
- bounded context construction
- decision-source invocation
- structured decision parsing
- action validation
- registry-based tool execution
- observation recording
- agent state updates
- trace writing
- budget enforcement
- retry enforcement
- terminal result creation
- terminal result persistence

### Runner Non-Responsibilities

The runner does not own:

- direct SQLite reads or writes
- tool implementation internals
- policy reasoning outside registered tools
- final independent grading
- MCP transport
- long-term memory compaction
- production customer-facing side effects

### Loop Contract

```text
trigger
  -> load goal/state
  -> build bounded context
  -> plan/select action
  -> validate tool call
  -> execute tool or request approval
  -> observe environment result
  -> verify progress
  -> update state and trace
  -> continue, retry, re-plan, escalate, or stop
  -> named terminal state
  -> persist trace/memory
```

### Implementation Notes

Start with a deterministic runner that can be tested without calling a live model. The decision-source interface should make it possible to plug in a model later without changing runner control flow.

## Milestone 5.2 - Run State Loading

### Objective

Load enough task, scenario, environment, and budget state for the runner to start from a known point.

### Expected Behavior

The runner should accept a task or scenario identifier, initialize the mock environment through existing reset helpers, create an `AgentState`, and attach a `BudgetUsage` instance with configured limits.

State loading should not duplicate fixture parsing or scenario validation logic already provided by the eval and state modules.

## Milestone 5.3 - Bounded Context Builder

### Objective

Create the prompt/context boundary used by each loop step.

### Expected Behavior

The context builder should include the task goal, current agent state, relevant observations, budget status, safety constraints, and available registry tool specs.

The context should avoid exposing raw database internals. The loop should learn about the environment by calling tools.

## Milestone 5.4 - Decision Source And Parser

### Objective

Separate action selection from loop execution so tests can use deterministic decisions.

### Agent Action Contract

```json
{
  "thought_summary": "Need to inspect the ticket and order before deciding.",
  "action": {
    "type": "tool_call",
    "tool_name": "fetch_order",
    "arguments": {
      "order_id": "o_551"
    }
  },
  "safety_check": {
    "permission_level": "read_only",
    "approval_required": false
  },
  "stop_reason": null
}
```

### Expected Behavior

The parser should accept structured decisions matching the loop action models and reject malformed output before tool execution.

## Milestone 5.5 - Action Validation

### Objective

Ensure the runner never executes an unsupported or malformed action.

### Expected Behavior

Tool call actions should be validated against the registry. Approval request actions should produce approval-aware control flow. Terminal-state actions should be converted into validated terminal outcomes.

Invalid decisions should stop with a named failure state rather than raising uncaught exceptions.

## Milestone 5.6 - Tool Execution Integration

### Objective

Connect loop actions to Phase Four registry execution.

### Expected Behavior

The runner should build a `ToolExecutionContext`, call the registry, preserve typed `ToolResult` behavior, and record both successful observations and structured errors.

The runner should not call concrete tool functions directly.

## Milestone 5.7 - State Updates And Trace Writing

### Objective

Make each loop step inspectable after execution.

### Expected Behavior

Each decision, tool call, observation, retry, approval request, and terminal state should create trace data. `AgentState` should reflect completed actions, pending approvals, retry counters, budget usage, and terminal state.

Trace files should be suitable for later verifier and report phases.

## Milestone 5.8 - Budget And Retry Enforcement

### Objective

Keep the loop bounded even when decisions or tools fail repeatedly.

### Expected Behavior

The runner should check step budget before continuing and retry budget before reattempting failed actions. Budget exhaustion and unrecoverable retry exhaustion should produce explicit terminal states with the state-specific fields required by `TerminalResult`.

## Milestone 5.9 - Terminal Result Persistence

### Objective

Persist the final run outcome in the domain model shape used by later eval and reporting phases.

### Expected Behavior

The runner should create and persist a validated `TerminalResult`, including `trace_path`, budget usage, summary, actions taken, errors, and terminal-state-specific fields.

## Milestone 5.10 - Manual Scenario Readiness Review

### Objective

Confirm the bare loop works across representative scenario paths before exposing it through MCP.

### Manual Scenario Coverage

Run at least five scenarios covering:

- successful resolution path
- human approval required path
- missing information path
- tool error and retry path
- budget or invalid-decision failure path

### Phase Five Completion Note

Phase Five is complete. The bare bounded agent loop now has a deterministic runner boundary,
scenario-backed state loading, a structured bounded context, decision-source parsing, action
validation, registry-only tool execution, observation recording, state updates, JSONL trace writing,
step and retry budget enforcement, and terminal result persistence.

Implementation added `src/bounded_agent/loop/runner.py` with:

- `AgentRunner`
- `RunnerConfig`, `RunnerRequest`, `RunnerContext`, and `RunnerResult`
- `BoundedContext` and `build_bounded_context`
- `DecisionSource`, `DeterministicDecisionSource`, and `ModelBackedDecisionSource`
- `parse_action_decision`
- `validate_action_decision`
- registry-backed tool execution and observation helpers
- trace and terminal-result persistence helpers

The first implemented decision source is deterministic. This lets tests and manual scenario runs
exercise loop control flow without depending on a live model. `ModelBackedDecisionSource` defines the
future provider boundary by passing `BoundedContext.to_decision_payload()` to a model client and
parsing the returned structured action decision.

Manual scenario readiness was exercised with deterministic decisions:

- `support_001` -> `needs_human_approval`, 6 steps, 5 observations, 19 trace events, result persisted
- `support_002` -> `resolved`, 6 steps, 6 observations, 20 trace events, result persisted
- `support_003` -> `blocked_missing_information`, 3 steps, 3 observations, 11 trace events, result persisted
- `support_005` -> `escalated`, 5 steps, 5 observations, 17 trace events, result persisted
- `support_006` -> `needs_human_approval`, 8 steps, 6 observations, timeout retry path, 24 trace events, result persisted
- `support_010` -> `failed_budget_exceeded`, 3 steps, 3 observations, 10 trace events, result persisted

Known limitations deferred to later phases:

- the model-backed decision source boundary exists, but no live model provider is wired yet
- approval-request actions update runner state but do not yet call the `request_approval` tool path
- retry actions update state and trace events, but the next actual tool call is still selected by the decision source
- terminal result persistence is local JSON rather than an eval-run aggregation layer
- independent verifier and report generation remain later-phase work

Phase Six can begin by exposing `AgentRunner.run_scenario` through the MCP server and mapping MCP
requests to deterministic or model-backed decision sources.

## Phase Five Outputs

Expected outputs:

- runner implementation
- bounded context builder
- decision source protocol
- mocked decision source
- structured decision parser
- action validation path
- registry execution integration
- trace writing support
- budget and retry enforcement
- terminal result persistence
- runner tests
- Phase Six readiness note

## Commit Guidance

Commit Phase Five after the bare loop can run multiple iterations, stop in named terminal states, persist traces/results, and pass tests.

## Phase Five Principle

The loop should be narrow, inspectable, and deterministic first. Intelligence can improve later; bounded control flow must be reliable now.
