# Local Operations

## Supported Workflow

```bash
uv sync --locked
uv run bounded-agent run-scenario support_001 --run-id support-001-demo
uv run bounded-agent show-trace support-001-demo --event-type safety_event
uv run bounded-agent show-run support-001-demo
uv run bounded-agent show-memory support-001-demo --artifact facts
uv run bounded-agent show-result support-001-demo
uv run bounded-agent verify-run support-001-demo
uv run bounded-agent run-eval --scenarios support_001 --eval-run-id support-001-eval
```

`resume-scenario` accepts only a nonterminal persisted run. Terminal runs are intentionally refused. `reset-env` mutates only the scenario-specific local SQLite database. Inspection and verification commands are read-only.

## Artifact Layout

- `data/runs/<run_id>/state.db`: scenario-specific mock environment.
- `data/runs/<run_id>/state.json`: durable agent state and resume identity.
- `data/runs/<run_id>/result.json`: typed terminal result.
- `data/runs/<run_id>/memory/`: facts, decisions, questions, safety events, and tool history.
- `data/eval_runs/<run_id>/verification.json`: independent verifier output.
- `data/eval_runs/<eval_run_id>/`: JSONL attempts, JSON summary, Markdown report, and traces.

Run and evaluation artifacts are generated locally and ignored by Git. Fixtures and scenario contracts remain tracked under `data/fixtures` and `data/scenarios`.

## Configuration

Copy `.env.example` to `.env` only when overriding defaults. Relevant settings include step, retry, invalid-action, token, and cost budgets; storage directories; and optional model/MCP flags. Deterministic local execution is the default. Live-model configuration is a boundary only; it is not a release-ready remote automation mode.

## Boundaries

The registry owns the allowed tool surface and schema validation. The environment owns approval records, idempotency, and mock mutations. The runner records decisions, safety events, state, memory, and traces. The verifier reads persisted evidence and does not repair runs. MCP supplies read-only policy facts and never grants authority.

Approval-required actions still require matching durable approved records. This harness does not deploy remote MCP services, connect to production systems, or replace a human approval authority.

## Release Check

```bash
uv run pytest
uv run ruff check src tests
uv run bounded-agent validate-scenarios
uv run bounded-agent run-eval --scenarios support_001 --eval-run-id release-smoke
```
