# Phase Ten - Evaluation And Reporting

## Purpose

Phase Ten turns independently verified scenario runs into repeatable evaluation evidence. It compares the bounded agent against a chosen baseline, aggregates outcomes by scenario and risk category, and produces inspectable reports.

The goal is to demonstrate whether the bounded loop improves useful outcomes while preserving safety, rather than presenting isolated successful runs.

## Phase Entry Context

Phase Nine provides read-only final-state and trajectory verification. The project already has typed scenarios, terminal results, traces, MCP provenance, approval records, idempotency records, and durable run artifacts.

## Phase Exit Criteria

Phase Ten is complete when:

- an evaluation run executes a selected scenario set repeatably
- each attempt is independently verified
- a fixed-workflow baseline is available for comparison
- results are persisted as JSONL plus a concise summary report
- metrics are broken down by terminal state and scenario tag
- safety, approval, retry, and MCP-dependent outcomes are visible
- failures link back to scenario and run artifacts
- repeated runs preserve reproducible inputs and version metadata
- evaluation tests and lint pass

## Phase Ten Checklist

- [x] Milestone 10.1 - Evaluation Contract
  - [x] Define eval configuration and typed eval-run result models
  - [x] Define scenario selection and ordering rules
  - [x] Define run ID and artifact layout
  - [x] Define reproducibility metadata
  - [x] Add contract tests
- [x] Milestone 10.2 - Baseline Runner
  - [x] Implement deterministic fixed-workflow baseline
  - [x] Reuse the same registry and environment boundaries
  - [x] Persist baseline traces and terminal results
  - [x] Verify baseline results independently
  - [x] Add baseline tests
- [x] Milestone 10.3 - Evaluation Orchestrator
  - [x] Run bounded-agent and baseline attempts per scenario
  - [x] Reset scenario state deterministically for each attempt
  - [x] Invoke the independent verifier
  - [x] Continue after individual scenario failures
  - [x] Persist JSONL result records
  - [x] Add orchestrator tests
- [x] Milestone 10.4 - Metrics And Breakdowns
  - [x] Aggregate pass rate and terminal-state distribution
  - [x] Aggregate outcomes by scenario tag and difficulty
  - [x] Track approval, retry, safety, and MCP-provenance metrics
  - [x] Track costs and budgets when available
  - [x] Add metric tests
- [x] Milestone 10.5 - Reporting
  - [x] Produce Markdown and JSON summaries
  - [x] Link failures to run, trace, and verifier artifacts
  - [x] Compare bounded-agent and baseline outcomes
  - [x] Highlight regressions and safety failures
  - [x] Add report tests
- [x] Milestone 10.6 - Evaluation CLI
  - [x] Add repeatable evaluation command
  - [x] Support scenario and runner selection
  - [x] Print concise summary and artifact paths
  - [x] Add CLI tests
- [x] Milestone 10.7 - Completion Review
  - [x] Run representative full evaluation set
  - [x] Confirm reports are deterministic and inspectable
  - [x] Confirm tests and lint pass
  - [x] Write Phase Ten completion note

## Evaluation Principles

- Use the same scenarios, environment reset behavior, registry, and verifier for every runner type.
- Do not compare unverified claims of success.
- Preserve per-attempt artifacts so aggregate metrics remain auditable.
- Report safety failures separately from ordinary task failures.
- A baseline is useful only when its limitations are explicit and it shares the same task boundary.

## Phase Ten Completion Note

Implemented with reproducible scenario ordering, deterministic fixed-workflow attempts for the bounded-loop and baseline comparison labels, independent verification, JSONL attempt records, JSON/Markdown summaries, terminal/tag/difficulty breakdowns, and the `run-eval` CLI command. The current deterministic comparison is intended as an auditable harness baseline; model-backed policy quality remains outside this phase. The full suite and Ruff passed on 2026-09-08.
