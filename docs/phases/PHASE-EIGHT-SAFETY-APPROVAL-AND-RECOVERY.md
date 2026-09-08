# Phase Eight - Safety, Approval, And Recovery

## Purpose

Phase Eight makes unsafe behavior structurally difficult and recovery behavior deliberate. It strengthens the existing bounded registry, approval records, durable run state, and trace rather than adding a second permission system.

The goal is to enforce permission and approval requirements at execution time, treat untrusted content as data, record safety-relevant decisions durably, and guide recovery from invalid actions, transient failures, missing information, and repeated errors into named terminal states.

## Phase Entry Context

Phase Seven completed durable run snapshots, compact memory artifacts, bounded-context compaction, and fresh-runner resume. Phase Six established MCP as a read-only policy/knowledge boundary. Consequential actions remain owned by the registry, environment, approval, audit, and idempotency layers.

## Phase Exit Criteria

Phase Eight is complete when:

- every registered tool call is checked against its permission contract before execution
- approval-required tools require a matching durable approved record
- approval decisions support approved, denied, pending, missing, and expired outcomes
- prompt-injection or instruction-like content is marked as untrusted data before context insertion
- safety-relevant events are recorded in trace and durable memory
- invalid arguments lead to bounded re-plan or named stop behavior
- transient failures retry only within configured limits
- missing required information leads to a safe escalation or blocked state
- repeated failures do not cause blind looping
- policy-violating or forbidden actions stop in `failed_policy_violation`
- safety and recovery scenario coverage passes
- Phase Nine can begin without unresolved enforcement ownership questions

## Phase Eight Checklist

- [x] Milestone 8.1 - Execution Safety Boundary
  - [x] Define runner, registry, and environment enforcement responsibilities
  - [x] Define safety event trace payloads
  - [x] Define durable safety-memory entries
  - [x] Confirm MCP remains fact-only and read-only
  - [x] Add boundary tests
- [x] Milestone 8.2 - Permission Enforcement
  - [x] Enforce registry permission level before tool execution
  - [x] Reject forbidden or unregistered actions structurally
  - [x] Validate action safety declarations against tool specs
  - [x] Return structured permission errors
  - [x] Trace permission denials
  - [x] Add permission tests
- [x] Milestone 8.3 - Durable Approval Gate
  - [x] Require matching approval ID for consequential execution
  - [x] Validate approval target and proposed arguments
  - [x] Accept only durable approved records
  - [x] Handle denied, pending, expired, and missing records
  - [x] Preserve approval state across resume
  - [x] Add approval-gate tests
- [x] Milestone 8.4 - Untrusted Content Handling
  - [x] Label ticket, customer, policy, and tool content as data
  - [x] Add safe context representation for untrusted content
  - [x] Detect instruction-like prompt-injection markers deterministically
  - [x] Record suspected injection events without executing content
  - [x] Preserve evidence for escalation
  - [x] Add injection tests
- [x] Milestone 8.5 - Invalid Action Recovery
  - [x] Classify invalid tool name, schema, and permission failures
  - [x] Permit bounded re-plan after recoverable invalid actions
  - [x] Stop with `failed_invalid_tool_call` after the invalid-action budget
  - [x] Persist recovery state and trace events
  - [x] Add recovery tests
- [x] Milestone 8.6 - Tool Failure Recovery
  - [x] Retry timeout and transient failures only within budget
  - [x] Preserve corrected arguments for explicit retry actions
  - [x] Escalate missing information safely
  - [x] Stop repeated failures with `blocked_tool_error`
  - [x] Preserve retry state across resume
  - [x] Add failure-recovery tests
- [x] Milestone 8.7 - Safety Scenario Coverage
  - [x] Add denied-approval scenario coverage
  - [x] Add missing-approval execution coverage
  - [x] Add prompt-injection scenario coverage
  - [x] Add transient retry and repeated-failure coverage
  - [x] Verify trace, memory, and terminal result behavior
  - [x] Add end-to-end tests
- [x] Milestone 8.8 - Phase Nine Readiness Review
  - [x] Confirm enforcement remains registry-owned
  - [x] Confirm approval and recovery state survives resume
  - [x] Confirm untrusted content cannot grant authority
  - [x] Confirm safety scenarios and quality checks pass
  - [x] Write Phase Eight completion note

## Milestone 8.1 - Execution Safety Boundary

### Objective

Make enforcement ownership explicit before adding more checks.

### Boundary Decision

The runner validates structured decisions and records safety outcomes. The registry enforces the allowed tool surface and schemas. Tool executors and environment state enforce approval, idempotency, and mutation rules. MCP only provides scoped facts and never grants permission or executable authority.

## Milestone 8.2 - Permission Enforcement

### Objective

Ensure an action cannot claim a weaker permission level than its registered tool requires.

### Expected Behavior

Permission mismatch, forbidden tools, and unregistered tools return structured errors before execution. Denials are traced and persisted so a resumed run cannot forget why an action was rejected.

## Milestone 8.3 - Durable Approval Gate

### Objective

Require durable approval before executing consequential tools.

### Expected Behavior

An approved record must match the run, action, target, and proposed arguments. Pending, denied, expired, missing, or mismatched approval records must not authorize execution. Resume must retain the same approval decision and idempotency behavior.

## Milestone 8.4 - Untrusted Content Handling

### Objective

Keep retrieved and customer-authored content from becoming instructions.

### Expected Behavior

Bounded context should label untrusted text as data. Deterministic markers for instruction-like content should produce a traceable safety event and safe escalation or continued evidence gathering, never tool authorization.

## Milestone 8.5 - Invalid Action Recovery

### Objective

Recover from correctable invalid actions without allowing unbounded retries.

### Expected Behavior

The runner should permit a bounded re-plan after an invalid action when a safe alternate path exists. Once the invalid-action budget is exhausted, it must stop with the existing named invalid-tool-call terminal state and preserve the validation evidence.

## Milestone 8.6 - Tool Failure Recovery

### Objective

Turn tool failures into bounded, typed recovery paths.

### Expected Behavior

Only timeout and transient errors are retryable. Missing information should lead to additional scoped reads, a blocked state, or escalation. Repeated errors stop safely and retain retry state across resume.

## Milestone 8.7 - Safety Scenario Coverage

### Objective

Prove safety behavior with deterministic scenarios and final-state assertions.

### Expected Behavior

Scenario coverage must show denied or missing approvals prevent mutations, prompt injection cannot change authority, and retry exhaustion reaches the correct terminal result while preserving trace and memory evidence.

## Milestone 8.8 - Phase Nine Readiness Review

### Objective

Confirm safety and recovery controls are ready for independent verification.

### Phase Eight Completion Note

Implemented with registry-aligned permission validation, durable approval creation and execution matching, safe untrusted-ticket context handling, durable safety memory, bounded invalid-action recovery, retry constraints, and explicit replan handling. The full test suite and Ruff checks passed on 2026-09-08.

Phase Eight completion should record:

- enforcement ownership and permission checks
- approval record matching behavior
- untrusted-content representation and detection behavior
- recovery policy and terminal-state mapping
- scenario coverage and quality results
- limitations deferred to later phases
- Phase Nine entry point

## Phase Eight Principle

Safety checks constrain authority and recovery behavior; they do not create new capabilities. The safest recovery is often escalation or a named stop, not another attempt.
