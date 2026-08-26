# Phase Four - Tool Registry And Scoped Tools

## Purpose

Phase Four gives the bounded agent a narrow, typed tool surface over the mock support environment.

The goal is not to build the agent loop yet. The goal is to create a deterministic tool registry, typed tool input/output schemas, permission enforcement, scoped read tools, policy tools, draft-only tools, approval-gated mutation tools, idempotent write behavior, injected failure handling, and tests that prove invalid or unsafe tool calls are rejected before execution.

By the end of this phase, future agent-loop code should be able to validate a structured tool call, execute an allowed tool against a reset scenario database, receive a typed `ToolResult`, and rely on permission, idempotency, audit, and injected failure behavior outside the prompt.

## Phase Entry Context

Phase Three completed:

- SQLite mock support environment
- base support and policy fixtures
- deterministic scenario reset
- final-state inspection helpers
- audited mutation primitives
- idempotency record helpers
- injected failure consumption helpers
- environment test coverage
- Phase Four readiness review

Phase Four should build on those foundations without changing the storage decision or scenario fixture contract.

## Phase Exit Criteria

Phase Four is complete when:

- every planned tool has a `ToolSpec`
- tool input and output schemas are typed
- a central registry can list, fetch, validate, and execute tools
- forbidden or unknown tool names are rejected before execution
- invalid tool arguments return structured validation errors
- read-only tools do not mutate environment state
- draft-only tools create drafts without customer-facing sends
- approval-required tools enforce approval checks outside the prompt
- mutating tools require idempotency keys
- idempotent retries return the original result without duplicating side effects
- injected failures are consumed during tool execution
- structured tool errors cover expected failure modes
- unit tests cover registry behavior, validation, permissions, idempotency, failures, and tool behavior
- Phase Five can begin by calling the registry from the bare bounded agent loop

## Phase Four Checklist

- [x] Milestone 4.1 - Tool Boundary And Execution Contract
  - [x] Define what the tool layer owns
  - [x] Define what is outside the tool layer
  - [x] Define tool execution inputs
  - [x] Define tool execution outputs
  - [x] Define error handling contract
  - [x] Define environment connection strategy
- [x] Milestone 4.2 - Tool Schema Models
  - [x] Add typed input schemas
  - [x] Add typed output schemas
  - [x] Add shared context model for execution
  - [x] Add validation helpers
  - [x] Add schema tests
- [x] Milestone 4.3 - Tool Registry
  - [x] Define central registry module
  - [x] Register all planned tool specs
  - [x] Validate tool names against allowlist
  - [x] Fetch tool specs by name
  - [x] List tools by permission level
  - [x] Add registry tests
- [x] Milestone 4.4 - Read-Only Inspection Tools
  - [x] Implement `fetch_ticket`
  - [x] Implement `fetch_customer`
  - [x] Implement `fetch_order`
  - [x] Implement `search_policy`
  - [x] Ensure read tools do not write audit events or mutations
  - [x] Add read tool tests
- [x] Milestone 4.5 - Policy Reasoning Tools
  - [x] Implement `check_refund_policy`
  - [x] Detect duplicate charge eligibility
  - [x] Detect refund-window ineligibility
  - [x] Detect ambiguous bundled-promotion cases
  - [x] Return policy references and rationale
  - [x] Add policy tool tests
- [x] Milestone 4.6 - Draft And Low-Risk Write Tools
  - [x] Implement `draft_customer_response`
  - [x] Implement `add_ticket_comment`
  - [x] Ensure drafts are not sent externally
  - [x] Ensure comments write audit events
  - [x] Add draft and comment tests
- [ ] Milestone 4.7 - Approval-Gated Tools
  - [ ] Implement `request_approval`
  - [ ] Implement approval lookup for approved/denied decisions
  - [ ] Implement `apply_refund`
  - [ ] Implement `update_ticket_status`
  - [ ] Reject approval-required calls without durable approval
  - [ ] Add approval-gated tool tests
- [ ] Milestone 4.8 - Idempotent Mutating Tool Execution
  - [ ] Require idempotency keys for mutating tools
  - [ ] Store argument hash and result payload
  - [ ] Replay matching retries
  - [ ] Reject reused keys with different arguments
  - [ ] Prove `apply_refund` cannot duplicate side effects
  - [ ] Add idempotency integration tests
- [ ] Milestone 4.9 - Injected Failure Integration
  - [ ] Check injected failures before read tool execution
  - [ ] Support timeout errors
  - [ ] Support transient errors
  - [ ] Support post-side-effect transient errors
  - [ ] Decrement failure counters exactly once
  - [ ] Add injected failure tool tests
- [ ] Milestone 4.10 - Tool Registry Readiness Review
  - [ ] Confirm all planned tools are registered
  - [ ] Confirm tool validation works
  - [ ] Confirm permission enforcement works
  - [ ] Confirm mutating tools are idempotent
  - [ ] Confirm injected failures work through tools
  - [ ] Confirm tests and lint pass
  - [ ] Write Phase Four completion note

## Milestone 4.1 - Tool Boundary And Execution Contract

### Objective

Define the exact responsibility of the tool layer before implementing registry and tool functions.

### Tool Layer Responsibilities

The tool layer owns:

- tool allowlist
- tool metadata
- input validation
- output validation
- permission checks
- approval checks for approval-required tools
- idempotency checks for mutating tools
- injected failure handling at execution time
- translating environment state into typed tool results
- translating expected failures into structured tool errors

### Tool Layer Non-Responsibilities

The tool layer should not decide which action the agent should take next.

| Concern | Owner |
| --- | --- |
| Which tool to call | Agent loop |
| Whether a terminal state is correct | Verifier/eval layer |
| How prompts are built | Prompt/context layer |
| Whether to retry after an error | Agent loop retry policy |
| Durable support state | Mock environment |
| Whether a tool exists and can run | Tool registry |
| Whether arguments match schema | Tool registry |
| Whether approval exists | Tool execution layer |

### Execution Contract

Implemented execution input:

```text
ToolExecutionContext
  - exactly one of db_path or SQLite connection
  - run_id
  - scenario_id
  - actor
  - approval_id when provided
  - idempotency_key when provided
```

Recommended execution output:

```text
ToolResult
  - ok
  - result
  - error
  - metadata
```

### Error Contract

All expected tool failures should return `ToolResult(ok=False, error=ToolError(...))`.

Use exceptions only for programming errors, broken test setup, or impossible internal states.

### Environment Connection Strategy

Tools should use `tool_connection(context)` instead of opening SQLite connections directly.

The execution context supports two modes:

- `db_path` mode opens and closes a SQLite connection for the tool call.
- `connection` mode reuses a caller-owned SQLite connection and leaves it open.

This lets unit tests share in-memory or temporary connections while CLI and eval runs can pass the
per-run database path.

### Implementation Note

Milestone 4.1 introduced:

- `ToolExecutionContext`
- `tool_connection`
- `success_result`
- `error_result`

These are intentionally small contract helpers. Actual tool schemas, registry dispatch, and
permission enforcement are implemented in later Phase Four milestones.

### Deliverable

Documented tool boundary and execution contract.

### Acceptance Check

A future agent runner can call the tool layer without knowing SQLite table details.

## Milestone 4.2 - Tool Schema Models

### Objective

Create typed Pydantic schemas for every planned tool input and output.

### Planned Tools

| Tool | Permission | Mutates State | Approval Required | Idempotency Required |
| --- | --- | --- | --- | --- |
| `fetch_ticket` | `read_only` | No | No | No |
| `fetch_customer` | `read_only` | No | No | No |
| `fetch_order` | `read_only` | No | No | No |
| `search_policy` | `read_only` | No | No | No |
| `check_refund_policy` | `read_only` | No | No | No |
| `draft_customer_response` | `draft_only` | No | No | No |
| `request_approval` | `approval_required` | Yes | Yes | Yes |
| `apply_refund` | `approval_required` | Yes | Yes | Yes |
| `add_ticket_comment` | `low_risk_write` | Yes | No | Yes |
| `update_ticket_status` | `approval_required` | Yes | Yes | Yes |

### Schema Guidance

Schemas should be narrow and explicit.

Examples:

- `FetchTicketInput(ticket_id)`
- `FetchTicketOutput(ticket)`
- `FetchCustomerInput(customer_id)`
- `FetchOrderInput(order_id)`
- `SearchPolicyInput(query)`
- `CheckRefundPolicyInput(ticket_id, order_id)`
- `DraftCustomerResponseInput(ticket_id, response_body, rationale)`
- `RequestApprovalInput(ticket_id, action_type, target, proposed_arguments, evidence_summary, risk_summary)`
- `ApplyRefundInput(charge_id, amount, currency, reason)`
- `AddTicketCommentInput(ticket_id, body)`
- `UpdateTicketStatusInput(ticket_id, status)`

### Deliverable

Tool schema module and validation tests.

### Acceptance Check

Invalid arguments fail before any environment state changes.

### Implementation Note

Milestone 4.2 introduced `src/bounded_agent/tools/schemas.py` with strict Pydantic input and
output schemas for every planned Phase Four tool. The module also includes:

- `ToolInputSchema`
- `ToolOutputSchema`
- `validate_tool_schema`
- `validation_error_details`

The shared execution context remains in `src/bounded_agent/tools/execution.py` from Milestone 4.1.
Future registry code should use these schema helpers before invoking any environment operation.

## Milestone 4.3 - Tool Registry

### Objective

Create a central registry that owns the allowed tool list and dispatch path.

### Registry Responsibilities

- register `ToolSpec` metadata
- map tool names to schema classes
- map tool names to executor functions
- reject unknown tool names
- parse raw `ToolCall` arguments into typed inputs
- validate execution context
- call the executor
- validate returned `ToolResult`

### Recommended Files

```text
src/bounded_agent/tools/schemas.py
src/bounded_agent/tools/registry.py
src/bounded_agent/tools/execution.py
```

### Deliverable

Tool registry and registry tests.

### Acceptance Check

The registry can execute a valid read-only tool and reject an unknown tool name.

### Implementation Note

Milestone 4.3 introduced `src/bounded_agent/tools/registry.py` with:

- `ToolRegistry`
- `RegisteredTool`
- `ToolExecutor`
- `DEFAULT_TOOL_SPECS`
- `DEFAULT_REGISTERED_TOOLS`
- `build_default_registry`
- `registered_tool`

The default registry now knows every planned Phase Four tool and its input/output schema pair. Tool
executors are attached in later milestones as each scoped tool is implemented.

## Milestone 4.4 - Read-Only Inspection Tools

### Objective

Expose safe read access to the mock support environment.

### Tools

- `fetch_ticket`
- `fetch_customer`
- `fetch_order`
- `search_policy`

### Behavior

Read-only tools should:

- validate required IDs
- use environment inspection helpers
- return structured `not_found` errors for missing records
- consume configured injected failures when applicable
- avoid audit writes
- avoid idempotency records
- avoid mutations

### Deliverable

Read-only tool implementations and tests.

### Acceptance Check

The agent can inspect ticket, customer, order, charge, and policy facts without mutating state.

### Implementation Note

Milestone 4.4 introduced `src/bounded_agent/tools/read_tools.py` and attached executors for:

- `fetch_ticket`
- `fetch_customer`
- `fetch_order`
- `search_policy`

These tools read through the Phase Three inspection helpers, return structured `not_found` errors
for missing records, consume matching injected failures when `scenario_id` is present, and avoid
audit, idempotency, and mutation writes.

## Milestone 4.5 - Policy Reasoning Tools

### Objective

Provide deterministic policy checks without delegating core eligibility logic to the model.

### `check_refund_policy` Behavior

The tool should return:

- eligibility status
- policy references
- rationale
- required evidence
- whether approval is required
- recommended next action

### Required Cases

- duplicate successful charges on the same order are eligible for approval
- old refund-window requests are ineligible
- bundled promotional partial refunds require escalation/manual review
- missing orders or customers return structured `not_found` or `validation_error`

### Deliverable

Policy tool and tests.

### Acceptance Check

Scenario policy decisions are deterministic and do not rely on prompt-only reasoning.

### Implementation Note

Milestone 4.5 introduced `src/bounded_agent/tools/policy_tools.py` and attached the
`check_refund_policy` executor to the default registry.

The tool deterministically handles:

- duplicate successful charges as eligible with approval required
- old refund-window requests as ineligible
- bundled promotional partial refunds as manual review
- missing ticket, order, or customer records as structured `not_found` errors

The tool returns policy references, rationale, required evidence, approval requirement, and a
recommended next action without mutating environment state.

## Milestone 4.6 - Draft And Low-Risk Write Tools

### Objective

Implement non-external communication and low-risk internal mutation tools.

### Tools

- `draft_customer_response`
- `add_ticket_comment`

### Behavior

`draft_customer_response` should:

- return a draft payload only
- not write customer-facing messages
- not close tickets
- include rationale and referenced facts

`add_ticket_comment` should:

- require an idempotency key
- write an internal ticket comment
- write an audit event
- replay safely on matching retries

### Deliverable

Draft and low-risk write tools with tests.

### Acceptance Check

The agent can create safe internal notes and response drafts without pretending to send messages.

### Implementation Note

Milestone 4.6 introduced `src/bounded_agent/tools/write_tools.py` and attached executors for:

- `draft_customer_response`
- `add_ticket_comment`

`draft_customer_response` returns a draft-only payload with `sent=false` and does not mutate the
environment. `add_ticket_comment` requires an idempotency key, writes an internal ticket comment,
writes an audit event, stores the original result payload, replays matching retries, and returns a
structured `conflict` error when the same key is reused with different arguments.

## Milestone 4.7 - Approval-Gated Tools

### Objective

Implement tools for consequential actions with durable approval enforcement outside the prompt.

### Tools

- `request_approval`
- `apply_refund`
- `update_ticket_status`

### Approval Rules

Approval-required tools should:

- require an approval ID or create one when the tool is `request_approval`
- look up approval state from the environment
- reject missing approvals
- reject pending approvals for execution-only tools
- reject denied approvals
- verify the approval target matches requested arguments
- write audit events for successful mutations

### Deliverable

Approval-gated tool implementations and tests.

### Acceptance Check

`apply_refund` and `update_ticket_status` cannot succeed based only on model text.

## Milestone 4.8 - Idempotent Mutating Tool Execution

### Objective

Wire Phase Three idempotency helpers into mutating tools.

### Mutating Tools

- `request_approval`
- `apply_refund`
- `add_ticket_comment`
- `update_ticket_status`

### Required Behavior

- missing idempotency key returns `validation_error`
- first successful call stores argument hash and result payload
- matching retry returns original result
- same key with different arguments returns `conflict`
- post-side-effect transient errors do not duplicate side effects when retried

### Deliverable

Idempotency integration and tests.

### Acceptance Check

Scenario `support_009` can retry `apply_refund` without creating a duplicate refund.

## Milestone 4.9 - Injected Failure Integration

### Objective

Make tool behavior fail deterministically according to scenario configuration.

### Required Failure Types

- `timeout`
- `transient_error`
- `transient_error_after_side_effect`
- `not_found`
- `permission_denied`
- `conflict`

### Execution Rules

- consume matching failures before normal execution for read-only and pre-side-effect failures
- decrement remaining count exactly once
- return structured retryable errors for timeout and transient errors
- allow post-side-effect transient errors after the mutation and idempotency record are written
- proceed normally once the failure count is exhausted

### Deliverable

Injected failure integration tests through the public tool registry.

### Acceptance Check

`support_006` can force one `fetch_order` timeout, and `support_009` can force one post-side-effect transient refund error through actual tool execution.

## Milestone 4.10 - Tool Registry Readiness Review

### Objective

Confirm the project is ready for the bare bounded agent loop.

### Review Checklist

- all planned tools have specs
- registry rejects unknown tools
- registry validates input arguments
- registry validates tool results
- read-only tools do not mutate state
- policy checks are deterministic
- draft-only tools do not send messages
- low-risk writes audit correctly
- approval-required tools enforce durable approval
- mutating tools are idempotent
- injected failures work through tool execution
- tests pass
- lint passes

### Deliverable

Phase Four completion note.

### Acceptance Check

Phase Five can begin by making the agent loop call the tool registry for validated tool execution.

## Phase Four Outputs

By the end of this phase, the repo should have:

- tool schema module
- tool execution context model
- central tool registry
- registered `ToolSpec` entries
- read-only support tools
- policy reasoning tool
- draft-only response tool
- low-risk internal comment tool
- approval request tool
- approval-gated refund and ticket-status tools
- idempotent mutating tool behavior
- injected failure integration through tool execution
- tool tests
- Phase Five readiness note

## Suggested Commit Boundary

Commit Phase Four as scoped tool registry implementation.

Suggested commit message:

```text
feat: add scoped tool registry
```

## Phase Four Principle

Keep tools narrow, typed, and boringly enforceable. The prompt may choose a tool, but the registry decides whether that tool exists, whether its arguments are valid, whether it is allowed, and whether consequential actions have durable approval.
