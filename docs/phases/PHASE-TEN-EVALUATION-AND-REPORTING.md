# Phase Ten - Evaluation And Reporting

## Purpose

Phase Ten turns independently verified scenario runs into repeatable evaluation evidence, aggregates outcomes by scenario and risk category, and produces inspectable reports. A runner comparison is admitted only when each label has a distinct implemented decision source.

The goal is to make supported behavior measurable while preserving safety, rather than presenting isolated successful runs or unsupported comparisons.

## Phase Entry Context

Phase Nine provides read-only final-state and trajectory verification. The project already has typed scenarios, terminal results, traces, MCP provenance, approval records, idempotency records, and durable run artifacts.

## Phase Exit Criteria

Phase Ten is complete when:

- an evaluation run executes a selected scenario set repeatably
- each attempt is independently verified
- any comparison uses distinct implemented decision sources
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
  - [x] Run supported decision-source attempts per scenario
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
  - [x] Reject unsupported comparison labels
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

Implemented with reproducible scenario ordering, deterministic fixed-workflow attempts, independent verification, JSONL attempt records, JSON/Markdown summaries, terminal/tag/difficulty breakdowns, and the `run-eval` CLI command. Unsupported comparison labels now fail closed until they have distinct decision-source implementations; model-backed policy quality remains outside this phase. The full suite and Ruff passed on 2026-09-08.
