# Phase Seven - Durable State, Memory, And Compaction

## Purpose

Phase Seven makes run progress durable so the bounded agent loop does not depend on chat history or one uninterrupted process.

The goal is to persist agent state after meaningful loop steps, maintain compact human-readable run memory alongside exact tool history, keep long observations out of bounded decision context, and resume an interrupted scenario without replaying completed work.

Phase Seven builds on the Phase Five runner and Phase Six MCP boundary. MCP remains a scoped source of policy and knowledge facts; durable run state, memory, compaction, and resume remain owned by the runner and state layers.

## Phase Entry Context

Phase Six completed:

- local typed MCP policy and knowledge tools
- fixture-backed local server lifecycle and structured errors
- tool-layer MCP client wrapper
- registry-backed `search_policy` lookup
- MCP provenance in tool trace metadata
- deterministic MCP-dependent scenario coverage

The runner already persists a terminal result and writes JSONL traces, but active `AgentState`, observations, and compacted context are not yet durable across a process restart.

## Phase Exit Criteria

Phase Seven is complete when:

- durable run state is persisted under `data/runs/{run_id}/`
- state is written after each meaningful loop step
- persisted state can reconstruct `AgentState` and bounded context
- each run has `facts.md`, `decisions.md`, `open_questions.md`, and `tool_history.jsonl`
- exact tool results remain available outside the compact prompt context
- long observations are summarized or referenced instead of copied blindly into context
- irreversible decisions and approval outcomes survive compaction
- an interrupted scenario resumes from persisted progress
- resumed work does not repeat completed mutating actions
- terminal result and trace continuity are preserved across resume
- deterministic compaction and resume tests pass
- Phase Eight can begin without durable-state or memory ownership questions

## Phase Seven Checklist

- [x] Milestone 7.1 - Durable State Boundary And Schema
  - [x] Define persisted run-state ownership
  - [x] Define run-state file or SQLite layout
  - [x] Define serialization contract for `AgentState`
  - [x] Define persisted observation and retry fields
  - [x] Define atomic write and load behavior
  - [x] Add state schema tests
- [x] Milestone 7.2 - Run State Store
  - [x] Add run-state path helpers
  - [x] Persist state after runner initialization
  - [x] Persist state after tool, approval, retry, and terminal transitions
  - [x] Load persisted state by `run_id`
  - [x] Reject malformed or mismatched persisted state
  - [x] Add state-store tests
- [x] Milestone 7.3 - Per-Run Memory Artifacts
  - [x] Create run memory directory
  - [x] Write `facts.md`
  - [x] Write `decisions.md`
  - [x] Write `open_questions.md`
  - [x] Append exact calls and results to `tool_history.jsonl`
  - [x] Add memory artifact tests
- [x] Milestone 7.4 - Memory Update Rules
  - [x] Extract durable facts from successful observations
  - [x] Record irreversible decisions and approval outcomes
  - [x] Record unresolved blockers as open questions
  - [x] Keep memory scoped to the active task and ticket
  - [x] Keep untrusted content identified as data
  - [x] Add deterministic update-rule tests
- [x] Milestone 7.5 - Context Compaction
  - [x] Define compaction threshold and deterministic trigger
  - [x] Summarize or reference long observations
  - [x] Preserve approvals, retries, budgets, and policy references
  - [x] Exclude raw long outputs from bounded context by default
  - [x] Rebuild bounded context from state and compact memory
  - [x] Add compaction tests under simulated context pressure
- [x] Milestone 7.6 - Interrupted Run Resume
  - [x] Add a resume entry point to `AgentRunner`
  - [x] Load state, memory, and trace continuity by `run_id`
  - [x] Continue step and retry budgets from persisted values
  - [x] Preserve pending approval IDs and idempotency behavior
  - [x] Refuse resume for terminal runs unless explicitly supported
  - [x] Add resume tests
- [x] Milestone 7.7 - Resume Scenario Coverage
  - [x] Add an interrupted deterministic scenario path
  - [x] Stop after a persisted read-only step
  - [x] Resume without repeating completed work
  - [x] Verify MCP-backed policy provenance survives the resume boundary where used
  - [x] Verify terminal result and trace remain continuous
  - [x] Add end-to-end scenario test coverage
- [x] Milestone 7.8 - Phase Eight Readiness Review
  - [x] Confirm state survives a fresh runner instance
  - [x] Confirm memory artifacts are readable and scoped
  - [x] Confirm compaction preserves required safety facts
  - [x] Confirm resume preserves approvals and idempotency
  - [x] Confirm tests and lint pass
  - [x] Write Phase Seven completion note

## Milestone 7.1 - Durable State Boundary And Schema

### Objective

Define what the runner persists and where it is owned before wiring persistence into loop control flow.

### Boundary Decision

The runner owns active run progress. The mock environment database remains the source of truth for tickets, orders, charges, approvals, audit records, and idempotency keys. The durable run record owns the agent's task state, observations needed for resume, and references to trace and memory artifacts.

Persisted state should be stored under:

```text
data/runs/{run_id}/
  state.json
  trace.jsonl
  result.json
  memory/
```

The initial implementation should use a strict JSON schema for the run record so it is easy to inspect and evolves independently from the mock environment schema. Atomic replace should prevent a partially written state file from appearing valid.

## Milestone 7.2 - Run State Store

### Objective

Persist and reload the state needed to continue a run.

### Expected Behavior

The store should persist the active `AgentState`, request identity, observations or their durable references, and the latest trace position after runner initialization and after every meaningful transition. It should reject a `run_id`, scenario ID, or ticket ID mismatch rather than silently joining unrelated state.

## Milestone 7.3 - Per-Run Memory Artifacts

### Objective

Create readable compact memory without losing exact execution history.

### Expected Behavior

Each run should have a memory directory with:

- `facts.md` for verified task-relevant facts
- `decisions.md` for durable decisions and rationale
- `open_questions.md` for unresolved blockers
- `tool_history.jsonl` for exact calls and results

Memory must never replace trace or environment truth. It is a compact runner-owned record used to rebuild bounded context and help a human inspect progress.

## Milestone 7.4 - Memory Update Rules

### Objective

Make memory updates deterministic, scoped, and safe.

### Expected Behavior

Only verified facts and durable workflow decisions should enter compact memory. Tool output, policy text, and customer-authored content remain data, not instructions. Approval outcomes, pending approvals, retries, policy references, and unresolved evidence gaps must remain recoverable after compaction.

## Milestone 7.5 - Context Compaction

### Objective

Keep bounded decision context useful under simulated pressure.

### Expected Behavior

Compaction should be deterministic for a given run state. It should retain the task goal, current status, required safety constraints, remaining budgets, relevant facts, approvals, retries, and concise observation references. Exact long payloads belong in trace or tool history, not the main decision context.

## Milestone 7.6 - Interrupted Run Resume

### Objective

Continue an unfinished run with a fresh runner instance.

### Expected Behavior

Resume should load the persisted run record, reconstruct bounded context from durable state and memory, and continue with the remaining budget. It must preserve pending approvals and rely on existing idempotency records to prevent repeated mutations. A terminal run should not be resumed accidentally.

## Milestone 7.7 - Resume Scenario Coverage

### Objective

Prove durability with a scenario rather than isolated storage tests alone.

### Expected Behavior

An end-to-end deterministic scenario should execute an initial step, persist state, simulate interruption, resume with a fresh runner, and reach a valid terminal state without duplicating prior work. When the scenario uses a policy lookup, its MCP provenance must still appear in the continuous trace.

## Milestone 7.8 - Phase Eight Readiness Review

### Objective

Confirm durable state and memory are stable enough for the next safety and recovery phase.

### Phase Seven Completion Note

Phase Seven is complete.

Active scenario runs now persist strict `state.json` snapshots beside the existing `state.db`, trace, and terminal result. `PersistedRunState` captures request identity, `AgentState`, typed observation payloads, database and trace paths, and terminal status. `RunStateStore` uses an atomic temporary-file replacement and rejects missing, malformed, mismatched, and terminal resume records.

Each run has a `memory/` directory containing `facts.md`, `decisions.md`, `open_questions.md`, and exact `tool_history.jsonl`. Facts are extracted only from successful observations; failures remain explicit open questions. Pending approvals are retained in both durable state and the compact decisions record. Memory is scoped to the run directory and remains a record of data rather than an authority source.

Bounded context now receives only the configured most-recent observations, while durable facts and exact results remain available through state and memory. `AgentRunner.resume_scenario` rebuilds a fresh runner from a nonterminal snapshot without resetting the scenario database, preserves steps, retries, approvals, and trace continuity, and refuses accidental terminal-run resume.

Verification completed with an interrupted MCP-backed `support_005` run resumed by a fresh runner, snapshot and memory tests, compaction pressure coverage, `254 passed` tests, and clean Ruff lint. Phase Eight can add safety and recovery controls on top of this durable execution record.

Phase Seven completion should record:

- persisted run-state schema and location
- memory artifact formats and update rules
- compaction trigger and retained facts
- resume behavior and terminal-run policy
- end-to-end interrupted scenario coverage
- test and lint results
- limitations deferred to later phases
- Phase Eight entry point

## Phase Seven Principle

Durable memory is a bounded record of verified progress, not a second authority system. The environment, approvals, idempotency records, registry, and MCP boundary retain their existing ownership.
