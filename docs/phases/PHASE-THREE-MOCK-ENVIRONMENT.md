# Phase Three - Mock Environment

## Purpose

Phase Three builds the realistic, resettable support environment that the bounded agent will inspect and mutate.

The goal is not to implement the agent loop or tool registry yet. The goal is to create the explicit mock backend, fixture data, deterministic reset behavior, injected failure configuration, final-state inspection helpers, and audit logging that later tools, verifiers, and evals will depend on.

By the end of this phase, scenario fixtures should be able to reset a local SQLite environment into a known state, mutations should leave an audit trail, and tests should prove the environment can be inspected and reset deterministically.

## Phase Entry Context

Phase Two completed:

- project metadata
- package scaffold
- configuration loading
- domain enums
- core Pydantic models
- action and tool contract models
- prompt skeletons
- ten scenario JSON skeletons
- basic CLI
- validation tests

Phase Three should use those foundations to create the mock support and billing backend.

## Phase Exit Criteria

Phase Three is complete when:

- SQLite schema exists
- environment module exists
- fixture files exist under `data/fixtures/`
- fixture loader can seed the database
- scenario reset can deterministically prepare state
- final environment state can be inspected for grading
- injected failures can be configured per scenario
- mutating environment operations write audit events
- idempotency records can be stored and checked
- tests cover schema creation, fixture loading, reset, inspection, audit logging, injected failures, and idempotency records
- Phase Four can begin without unresolved mock-backend questions

## Phase Three Checklist

- [x] Milestone 3.1 - Environment Boundary And Storage Decisions
  - [x] Confirm SQLite as the mock backend
  - [x] Define environment responsibilities
  - [x] Define what is not part of the environment
  - [x] Define database file locations
  - [x] Define reset strategy
- [x] Milestone 3.2 - SQLite Schema
  - [x] Create schema module
  - [x] Add `tickets` table
  - [x] Add `customers` table
  - [x] Add `orders` table
  - [x] Add `charges` table
  - [x] Add `policies` table
  - [x] Add `ticket_comments` table
  - [x] Add `approvals` table
  - [x] Add `audit_log` table
  - [x] Add `idempotency_keys` table
  - [x] Add `injected_failures` table
  - [x] Add schema tests
- [x] Milestone 3.3 - Fixture Data Design
  - [x] Create support seed fixture
  - [x] Create policy fixture
  - [x] Include duplicate-charge data
  - [x] Include refund-ineligible data
  - [x] Include missing-record scenario support
  - [x] Include ambiguous-policy data
  - [x] Include prompt-injection ticket text
  - [x] Include approval approved/denied fixture hooks
- [x] Milestone 3.4 - Fixture Loader
  - [x] Implement fixture file loading
  - [x] Implement database seeding
  - [x] Validate fixture shape
  - [x] Make fixture loading deterministic
  - [x] Add fixture loader tests
- [x] Milestone 3.5 - Scenario Reset System
  - [x] Implement reset by scenario ID
  - [x] Clear run-specific state
  - [x] Load base fixtures
  - [x] Apply scenario-specific initial state
  - [x] Configure scenario injected failures
  - [x] Add reset tests
- [x] Milestone 3.6 - Environment Inspection Helpers
  - [x] Implement ticket inspection helpers
  - [x] Implement customer inspection helpers
  - [x] Implement order and charge inspection helpers
  - [x] Implement policy inspection helpers
  - [x] Implement final-state snapshot helper
  - [x] Add inspection tests
- [ ] Milestone 3.7 - Audit Log And Mutating Operation Primitives
  - [ ] Implement audit event writer
  - [ ] Implement internal ticket comment primitive
  - [ ] Implement approval record primitive
  - [ ] Implement status update primitive
  - [ ] Implement mock refund record primitive
  - [ ] Ensure all mutations write audit events
  - [ ] Add audit tests
- [ ] Milestone 3.8 - Idempotency Records
  - [ ] Implement idempotency key table helpers
  - [ ] Store original argument hash
  - [ ] Store original result payload
  - [ ] Return existing result for matching retries
  - [ ] Return conflict for reused key with different args
  - [ ] Add idempotency tests
- [ ] Milestone 3.9 - Injected Failure Mechanism
  - [ ] Define injected failure schema
  - [ ] Load failures from scenario JSON
  - [ ] Track remaining failure count
  - [ ] Support timeout failure
  - [ ] Support transient error
  - [ ] Support transient error after side effect
  - [ ] Add injected failure tests
- [ ] Milestone 3.10 - Phase Four Readiness Review
  - [ ] Confirm mock database can be created
  - [ ] Confirm fixtures load
  - [ ] Confirm scenarios reset deterministically
  - [ ] Confirm final-state snapshots work
  - [ ] Confirm mutations audit correctly
  - [ ] Confirm idempotency helpers work
  - [ ] Confirm injected failures work
  - [ ] Write Phase Three completion note

## Milestone 3.1 - Environment Boundary And Storage Decisions

### Objective

Define what the mock environment owns before writing schema and loaders.

### Environment Responsibilities

The mock environment owns:

- support ticket state
- scoped customer records
- order records
- charge and refund records
- policy records or policy references
- internal ticket comments
- approval records
- audit log entries
- idempotency records
- injected failure state
- final-state snapshots for grading

### Environment Non-Responsibilities

The mock environment should expose deterministic state and operations. It should not decide agent policy.

| Concern | Owner |
| --- | --- |
| Whether a tool is allowed | Safety/tool policy layer |
| Which action to take next | Agent loop |
| Whether a terminal state is correct | Verifier/eval layer |
| How prompts are built | Prompt/context layer |
| Whether to retry | Agent loop retry policy |
| Whether approval is needed | Safety/tool policy layer |
| Whether an approval record exists | Mock environment storage |
| Whether an idempotency key was reused | Mock environment storage |

### Out Of Scope

The mock environment does not own:

- model calls
- agent loop planning
- prompt building
- tool registry policy decisions
- external network calls
- real payment actions
- real customer email
- real support-system integration

### Database File Strategy

Recommended files:

```text
data/runs/{run_id}/state.db
```

For tests, use temporary SQLite files or in-memory SQLite when persistence is not being tested.

### Storage Decision

Use SQLite as the primary mock backend.

Reasons:

- local and dependency-free
- deterministic per-run database files
- realistic relational state for tickets, customers, orders, charges, approvals, audit logs, and idempotency records
- easy final-state inspection for graders
- simple CI and local development story
- sufficient transaction support for idempotent mutations

Do not use Postgres in the first implementation. It adds infrastructure without improving the portfolio evidence bar for this local bounded-agent harness.

Do not use JSON files as the primary backend. JSON remains useful for scenario and fixture definitions, but the mutable environment needs relational constraints, transaction boundaries, and easy joins.

### Database Location Rules

Runtime scenario runs should use:

```text
data/runs/{run_id}/state.db
```

Manual development may use:

```text
data/runs/dev/state.db
```

Tests should use:

```text
tmp_path/state.db
```

In-memory SQLite is allowed only for tests that do not need to verify persistence or resume behavior.

### Environment API Shape

Phase Three should introduce a small environment API, likely under:

```text
src/bounded_agent/state/
```

Recommended modules:

```text
src/bounded_agent/state/schema.py
src/bounded_agent/state/environment.py
src/bounded_agent/state/fixtures.py
src/bounded_agent/state/reset.py
src/bounded_agent/state/inspection.py
src/bounded_agent/state/audit.py
src/bounded_agent/state/idempotency.py
src/bounded_agent/state/failures.py
```

The exact module split can change during implementation, but these responsibilities should remain separate.

### Reset Strategy

For each scenario run:

1. Create or clear the run database.
2. Apply schema.
3. Load base fixtures.
4. Apply scenario-specific state.
5. Configure injected failures.
6. Start with empty audit, approval, idempotency, and run-specific mutation state unless scenario explicitly needs preloaded approvals.

### Reset Invariants

After reset:

- scenario-relevant tickets, customers, orders, charges, and policies exist or are intentionally absent
- run-specific mutation tables start empty unless scenario fixtures explicitly preload them
- injected failure counters match the scenario JSON
- audit log starts empty for the run
- idempotency records start empty for the run
- resetting the same scenario twice produces the same initial snapshot

### Decision Record

```text
Milestone 3.1 decision: the mock environment will use SQLite as the primary local backend.
Each scenario run will use a per-run database at data/runs/{run_id}/state.db. Scenario and
fixture definitions remain JSON files, while mutable environment state lives in SQLite. The
environment owns deterministic state, persistence, inspection, audit records, idempotency records,
and injected failure state. It does not own model behavior, tool permission decisions, prompt
construction, retry policy, or eval grading.
```

### Deliverable

Environment boundary decision.

### Acceptance Check

It should be clear whether a future feature belongs in the mock environment, tool layer, agent loop, or eval harness.

## Milestone 3.2 - SQLite Schema

### Objective

Create the database schema for the mocked support and billing backend.

### Recommended Tables

- `tickets`
- `customers`
- `orders`
- `charges`
- `policies`
- `ticket_comments`
- `approvals`
- `audit_log`
- `idempotency_keys`
- `injected_failures`

### Table Responsibilities

| Table | Responsibility |
| --- | --- |
| `tickets` | Ticket body, status, category, linked customer/order IDs, untrusted customer text |
| `customers` | Scoped customer support summary, account status, support tier, risk flags |
| `orders` | Order metadata, customer relation, fulfillment/refund status |
| `charges` | Charge records, amount, currency, status, refund linkage |
| `policies` | Policy text, policy category, version, eligibility hints |
| `ticket_comments` | Internal notes or drafted comments tied to tickets |
| `approvals` | Approval requests and outcomes |
| `audit_log` | Append-only mutation log |
| `idempotency_keys` | Idempotency key, argument hash, result payload, tool/action metadata |
| `injected_failures` | Scenario-specific deterministic failures |

### Deliverable

Schema creation module and schema tests.

### Acceptance Check

A fresh database can be initialized with all required tables and constraints.

## Milestone 3.3 - Fixture Data Design

### Objective

Create realistic base data that supports the first 10 scenarios.

### Fixture Files

Recommended files:

```text
data/fixtures/support_seed.json
data/fixtures/policies.json
```

### Required Fixture Coverage

- verified duplicate charge case
- refund outside policy window
- missing order reference
- missing customer reference
- ambiguous bundled promotional order policy
- transient order lookup failure scenario hook
- approval denied scenario hook
- prompt-injection ticket body
- approved refund/idempotency retry scenario
- strict budget scenario

### Deliverable

Fixture files with support, billing, and policy records.

### Acceptance Check

Every existing scenario ID has enough fixture data to reset into its intended starting condition.

## Milestone 3.4 - Fixture Loader

### Objective

Load fixture JSON into SQLite deterministically.

### Loader Responsibilities

- validate fixture file exists
- parse fixture JSON
- insert customers
- insert orders
- insert charges
- insert tickets
- insert policies
- fail clearly on duplicate primary keys
- fail clearly on malformed fixture records

### Deliverable

Fixture loader and tests.

### Acceptance Check

Loading the same fixture twice after reset produces the same database state.

## Milestone 3.5 - Scenario Reset System

### Objective

Prepare a fresh environment for a specific scenario.

### Reset Responsibilities

- read `data/scenarios/{scenario_id}.json`
- initialize schema
- load base fixtures
- apply scenario `initial_state`
- configure `injected_failures`
- preload approval fixture state when specified
- clear stale mutation artifacts

### Deliverable

Scenario reset helper and tests.

### Acceptance Check

Resetting the same scenario twice produces identical inspectable state.

## Milestone 3.6 - Environment Inspection Helpers

### Objective

Provide deterministic read helpers that later tools and verifiers can use.

### Inspection Helpers

- `get_ticket(ticket_id)`
- `get_customer(customer_id)`
- `get_order(order_id)`
- `get_charges_for_order(order_id)`
- `search_policies(query)`
- `get_approvals_for_ticket(ticket_id)`
- `get_audit_events(target_id)`
- `snapshot_environment(ticket_id)`

### Deliverable

Read helper module and tests.

### Acceptance Check

Final-state grading can inspect the environment without using agent prompts or tool outputs.

## Milestone 3.7 - Audit Log And Mutating Operation Primitives

### Objective

Create low-level mutation helpers that always write audit entries.

### Mutation Primitives

- create ticket comment
- create approval request
- resolve approval
- record mock refund
- update ticket status
- write audit event

### Audit Event Fields

- audit ID
- timestamp
- run ID
- scenario ID
- actor
- action
- target type
- target ID
- payload
- idempotency key when present

### Deliverable

Mutation primitives and audit tests.

### Acceptance Check

No supported mutation can happen without an audit event.

## Milestone 3.8 - Idempotency Records

### Objective

Create durable idempotency primitives for future mutating tools.

### Required Behavior

- first call with a key stores argument hash and result payload
- repeated call with same key and same arguments returns original result
- repeated call with same key and different arguments returns conflict
- records include run ID, tool/action, target, created timestamp, and payload hashes

### Deliverable

Idempotency helper module and tests.

### Acceptance Check

The future `apply_refund` tool can retry without duplicating side effects.

## Milestone 3.9 - Injected Failure Mechanism

### Objective

Make scenario-specific failures deterministic and testable.

### Supported Failure Types

- `timeout`
- `transient_error`
- `transient_error_after_side_effect`
- `not_found`
- `permission_denied`
- `conflict`

### Failure Behavior

Each injected failure should include:

- scenario ID
- tool name
- failure type
- remaining count
- optional target resource
- optional payload

When consumed, remaining count should decrement. Once exhausted, the operation should proceed normally.

### Deliverable

Injected failure helper and tests.

### Acceptance Check

Scenario `support_006` can force one `fetch_order` timeout, and `support_009` can force one post-side-effect transient refund error.

## Milestone 3.10 - Phase Four Readiness Review

### Objective

Confirm the project is ready for tool registry and scoped tool implementation.

### Review Checklist

- SQLite schema exists.
- Fixture data exists.
- Fixture loader works.
- Scenario reset works.
- Inspection helpers work.
- Mutation primitives write audit events.
- Idempotency helpers work.
- Injected failures work.
- Tests pass.
- CLI scenario validation still works.

### Deliverable

Phase Three completion note.

### Acceptance Check

Phase Four can begin by implementing scoped tools over this environment.

## Phase Three Outputs

By the end of this phase, the repo should have:

- SQLite schema module
- mock environment module
- fixture files
- fixture loader
- scenario reset helper
- environment inspection helpers
- audit log primitives
- idempotency helpers
- injected failure mechanism
- environment tests
- Phase Four readiness note

## Suggested Commit Boundary

Commit Phase Three as mock environment implementation.

Suggested commit message:

```text
feat: add mock support environment
```

## Phase Three Principle

Make the environment boringly explicit. The agent can only be graded honestly if the world it acts on is deterministic, inspectable, resettable, and audited.
