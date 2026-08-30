# bounded-agent-harness

Bounded support-resolution agent harness with typed tools, durable state, approvals, traces, and evals.

## Problem statement

Most agent demos look powerful because the agent can do anything. Production support systems need the opposite: an agent that can resolve routine work while staying inside explicit tool scopes, preserving durable state, asking for approval before consequential writes, and leaving enough trace data for audit and evaluation.

`bounded-agent-harness` is a portfolio-grade mock support environment for that shape of agent. It models support tickets, customers, orders, charges, policies, approvals, idempotency records, injected failures, and typed tool calls so agent behavior can be tested as a bounded workflow instead of an open-ended chatbot.

## What the agent can and cannot do

The harness is designed for support-resolution scenarios such as duplicate-charge triage. The agent can inspect scoped account state, read tickets, fetch customer and order facts, search deterministic policy content, check refund eligibility, draft safe responses, add internal ticket comments, and create durable approval requests.

The agent cannot perform unsafe writes without the required approval context. Refunds and ticket status changes are modeled as approval-gated tools, mutating tools require idempotency keys, and every tool call is validated against strict Pydantic schemas. The current runner is intentionally incremental: the repo already contains the tool registry, state model, scenarios, policy checks, failure handling, and CLI entry points, while full planner orchestration is on the roadmap.

## Architecture

- `src/bounded_agent/domain`: shared enums and typed domain models.
- `src/bounded_agent/state`: SQLite schema, fixture loading, inspection helpers, audit records, idempotency, reset helpers, and injected failure support.
- `src/bounded_agent/tools`: typed tool schemas, registry metadata, read tools, write tools, approval-gated tools, policy tools, and execution wrappers.
- `src/bounded_agent/loop`: typed agent action models for tool calls, approval requests, retries, replans, and terminal states.
- `src/bounded_agent/evals`: scenario loading and validation for deterministic evaluation fixtures.
- `data/fixtures`: mock support and policy data.
- `data/scenarios`: support-resolution scenario contracts with expected and forbidden actions.
- `reports`: human-readable traces and experiment outputs.
- `tests`: focused unit tests for CLI behavior, schemas, state, tools, idempotency, and scenario validation.

## Quickstart

Run the 60-second local check:

```bash
uv sync --locked
uv run pytest
uv run bounded-agent --help
uv run bounded-agent demo
```

## Demo scenario

The included demo follows this bounded workflow:

```text
Support ticket -> inspect account state -> propose safe action -> request approval when needed -> apply bounded tool call -> write trace/report.
```

The default scenario is `support_001`, a duplicate-charge complaint. The expected behavior is to verify the ticket, customer, order, charges, and refund policy; create exactly one approval request for the refund; and stop before applying the refund until approval exists.

See `reports/demo-trace.md` for the readable trace.

## Safety model

### Safety constraints

- Scoped tools
- Idempotency keys
- Approval gates
- Durable state
- Bounded retries
- No unsafe writes without approval

### How safety is represented

Tools declare permission levels, mutation behavior, approval requirements, idempotency requirements, and expected error types. Inputs and outputs are validated with strict schemas. Mutating tools record idempotency keys and audit entries so retries can replay safely or fail on conflicting arguments. Approval-required tools reject writes unless they receive a durable `approval_id` tied to an approved action.

The mock environment also supports injected failures, allowing retry and failure-handling behavior to be tested without relying on flaky external systems.

## Evaluation approach

Scenarios in `data/scenarios` define the task, initial state, expected terminal state, expected actions, forbidden actions, injected failures, tags, difficulty, and grading rubric. This gives the harness a contract for evaluating whether an agent stayed inside bounds.

Current evaluation coverage validates scenario fixtures, typed tool schemas, state transitions, idempotency behavior, approval gates, and failure handling. The next step is to connect these contracts to a full agent loop runner that emits machine-readable traces and aggregate eval reports.

## What this demonstrates

Agent workflow design, bounded tool use, approval systems, auditability, typed state, failure handling, and eval-driven agent reliability.

## Roadmap

- Implement the full bounded agent loop runner.
- Emit structured trace artifacts for every run.
- Add a richer `bounded-agent run-scenario` execution path.
- Add eval scoring across expected actions, forbidden actions, terminal state, and trace quality.
- Add examples for approval granted, approval denied, transient tool failure, and idempotency replay.
- Publish a compact portfolio walkthrough with architecture diagram and demo recording.
