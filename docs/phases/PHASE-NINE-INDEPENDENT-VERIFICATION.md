# Phase Nine - Independent Verification

## Purpose

Phase Nine independently grades bounded-agent runs. It evaluates both final environment state and execution trajectory without relying on the decision source to self-report success.

The goal is a deterministic verifier that reads scenario expectations, persisted terminal results, environment state, traces, and durable memory to produce inspectable pass/fail evidence.

## Phase Entry Context

Earlier phases provide typed terminal results, scoped tools, durable environment state, JSONL traces, MCP provenance, and resumable run snapshots. Phase Nine consumes those artifacts; it does not execute agent actions or alter scenario state.

## Phase Exit Criteria

Phase Nine is complete when:

- deterministic final-state verification exists
- trajectory verification exists
- required and forbidden actions are evaluated
- expected terminal state is evaluated
- environment changes and approval behavior are evaluated
- trace provenance and safety events are evaluated where required
- verifier output is typed and persisted
- failures identify the failed check and supporting evidence
- scenarios can be verified repeatedly without mutation
- tests and lint pass

## Phase Nine Checklist

- [x] Milestone 9.1 - Verifier Contract And Inputs
  - [x] Define typed verifier request and result models
  - [x] Define artifact discovery by run ID
  - [x] Define read-only verifier boundary
  - [x] Define structured check and failure payloads
  - [x] Add contract tests
- [x] Milestone 9.2 - Final-State Verification
  - [x] Verify expected terminal state
  - [x] Verify terminal state-specific required fields
  - [x] Verify expected environment changes
  - [x] Verify final ticket, refund, and approval state where applicable
  - [x] Add final-state tests
- [x] Milestone 9.3 - Trajectory Verification
  - [x] Verify required action coverage
  - [x] Verify forbidden actions are absent
  - [x] Verify idempotency and duplicate-mutation constraints
  - [x] Verify retry and budget behavior
  - [x] Verify trace continuity and ordering
  - [x] Add trajectory tests
- [x] Milestone 9.4 - Safety And MCP Evidence
  - [x] Verify approval gates for consequential actions
  - [x] Verify safety events when scenarios require them
  - [x] Verify MCP-backed lookup provenance where scenarios require it
  - [x] Verify untrusted content did not grant authority
  - [x] Add evidence tests
- [x] Milestone 9.5 - Verifier Persistence And CLI
  - [x] Persist typed verifier results under eval runs
  - [x] Add read-only verification CLI command
  - [x] Render concise human-readable failures
  - [x] Ensure repeated verification is deterministic
  - [x] Add CLI tests
- [x] Milestone 9.6 - Phase Ten Readiness Review
  - [x] Verify representative scenarios end to end
  - [x] Confirm verifier does not mutate state
  - [x] Confirm tests and lint pass
  - [x] Write Phase Nine completion note

## Verification Principles

- The verifier is independent from the decision source.
- Verification reads persisted evidence and does not repair or mutate runs.
- A passing terminal state alone is insufficient when trajectory or safety constraints fail.
- Failures must be attributable to a named check and concrete artifact evidence.
- MCP provenance, approvals, idempotency, and safety events are facts to verify, not authority grants.

## Phase Nine Completion Note

Implemented with a typed verification request/result contract, read-only run-artifact inspection, structured evidence per check, persisted verification reports, and the `verify-run` CLI command. The verifier checks terminal contracts, environment state, approvals, idempotency, trajectory, trace continuity, safety events, and local MCP provenance. The full suite and Ruff passed on 2026-09-08.
